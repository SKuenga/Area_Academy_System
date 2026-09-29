import json

from .forms import LoginForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ImproperlyConfigured
from django.db import IntegrityError, transaction
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.shortcuts import redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST
from webauthn import (
    base64url_to_bytes,
    verify_authentication_response,
    verify_registration_response,
)
from webauthn.helpers.exceptions import WebAuthnException

from .models import (
    PasskeyCeremony,
    PasskeyCredential,
    PasskeyEnrollmentGrant,
    User,
)
from apps.branch.models import Branch
from apps.authentication.utils import haversion_algo
from apps.attendance.models import Attendance
from apps.authentication.services.passkeys import (
    create_enrollment_options,
    create_login_options,
    find_valid_enrollment_grant,
    get_webauthn_configuration,
)
from .services.attendance_status_service import status_check


PASSKEY_LOGIN_CEREMONY_SESSION_KEY = "passkey_login_ceremony_id"
PASSKEY_LOGIN_USER_SESSION_KEY = "passkey_login_user_id"
PASSKEY_ENROLLMENT_CEREMONY_SESSION_KEY = "passkey_enrollment_ceremony_id"
PASSKEY_ENROLLMENT_GRANT_SESSION_KEY = "passkey_enrollment_grant_id"
PASSKEY_ENROLLMENT_USER_SESSION_KEY = "passkey_enrollment_user_id"
PASSKEY_AUTHENTICATED_USER_SESSION_KEY = "passkey_authenticated_user_id"
PASSKEY_AUTHENTICATED_CREDENTIAL_SESSION_KEY = "passkey_authenticated_credential_id"


def _json_payload(request):
    try:
        payload = json.loads(request.body)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _consume_ceremony(request, session_key, purpose, user_id):
    ceremony_id = request.session.pop(session_key, None)
    if not isinstance(ceremony_id, str):
        return None

    now = timezone.now()
    ceremony = PasskeyCeremony.objects.filter(
        pk=ceremony_id,
        user_id=user_id,
        purpose=purpose,
    ).first()
    if ceremony is None:
        return None

    updated = PasskeyCeremony.objects.filter(
        pk=ceremony.pk,
        consumed_at__isnull=True,
        expires_at__gt=now,
    ).update(consumed_at=now)
    return ceremony if updated == 1 else None


def _credential_id(payload):
    try:
        raw_id = payload["rawId"]
        if not isinstance(raw_id, str):
            return None
        return base64url_to_bytes(raw_id)
    except (KeyError, TypeError, ValueError):
        return None


def _passkey_login_required(request):
    credential_id = request.session.get(
        PASSKEY_AUTHENTICATED_CREDENTIAL_SESSION_KEY
    )
    return (
        request.session.get(PASSKEY_AUTHENTICATED_USER_SESSION_KEY) == request.user.pk
        and isinstance(credential_id, int)
        and PasskeyCredential.objects.filter(
            pk=credential_id,
            user=request.user,
        ).exists()
    )


def login_view(request):
    if request.method == "POST":
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            if PasskeyCredential.objects.filter(user=user).exists():
                try:
                    ceremony, options = create_login_options(user)
                except ImproperlyConfigured as exc:
                    form.add_error(None, str(exc))
                else:
                    request.session[PASSKEY_LOGIN_CEREMONY_SESSION_KEY] = str(
                        ceremony.pk
                    )
                    request.session[PASSKEY_LOGIN_USER_SESSION_KEY] = user.pk
                    return render(
                        request,
                        "authentication/passkey_login.html",
                        {"options": options},
                    )
            elif user.role != User.Role.SUPER_ADMIN:
                form.add_error(
                    None,
                    (
                        "A passkey is required before you can sign in. "
                        "Contact a super administrator to verify your identity "
                        "and issue a one-time setup code."
                    ),
                )
            else:
                login(request, user)
                return redirect("super_admin_dashboard")
    else:
        form = LoginForm()
    return render(request, 'authentication/login.html', {'form': form})


@require_POST
def passkey_login_complete(request):
    user_id = request.session.pop(PASSKEY_LOGIN_USER_SESSION_KEY, None)
    ceremony = _consume_ceremony(
        request,
        PASSKEY_LOGIN_CEREMONY_SESSION_KEY,
        PasskeyCeremony.Purpose.LOGIN,
        user_id,
    )
    if ceremony is None:
        return JsonResponse(
            {"error": "The passkey challenge expired or was already used. Sign in again."},
            status=400,
        )

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse(
            {"error": "The passkey response was invalid. Sign in again to retry."},
            status=400,
        )
    credential_id = _credential_id(payload)
    if credential_id is None:
        return JsonResponse(
            {"error": "The passkey response was invalid. Sign in again to retry."},
            status=400,
        )

    try:
        configuration = get_webauthn_configuration()
        with transaction.atomic():
            credential = PasskeyCredential.objects.select_for_update().select_related(
                "user"
            ).filter(
                user_id=user_id,
                credential_id=credential_id,
            ).first()
            if credential is None or not credential.user.is_active:
                return JsonResponse(
                    {"error": "Passkey verification failed. Sign in again to retry."},
                    status=401,
                )

            verification = verify_authentication_response(
                credential=payload,
                expected_challenge=base64url_to_bytes(ceremony.challenge),
                expected_rp_id=configuration.rp_id,
                expected_origin=configuration.origin,
                credential_public_key=bytes(credential.public_key),
                credential_current_sign_count=credential.sign_count,
                require_user_verification=True,
            )
            credential.sign_count = verification.new_sign_count
            credential.last_used_at = timezone.now()
            credential.save(update_fields=("sign_count", "last_used_at"))
    except ImproperlyConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except (WebAuthnException, TypeError, ValueError, KeyError):
        return JsonResponse(
            {"error": "Passkey verification failed. Sign in again to retry."},
            status=401,
        )

    user = credential.user

    login(request, user)
    request.session[PASSKEY_AUTHENTICATED_USER_SESSION_KEY] = user.pk
    request.session[PASSKEY_AUTHENTICATED_CREDENTIAL_SESSION_KEY] = credential.pk
    request.session.set_expiry(12 * 60 * 60)

    if user.role == User.Role.SUPER_ADMIN:
        next_url = redirect("super_admin_dashboard").url
    elif user.role == User.Role.BRANCH_MANAGER:
        next_url = redirect("branch_manager_dashboard").url
    else:
        next_url = redirect("attendance_check_in").url
    return JsonResponse({"redirect": next_url})


def passkey_enrollment(request):
    return render(request, "authentication/passkey_enrollment.html")


@require_POST
def passkey_enrollment_options(request):
    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "Invalid setup request."}, status=400)

    username = payload.get("username")
    raw_token = payload.get("setup_code")
    if (
        not isinstance(username, str)
        or not isinstance(raw_token, str)
        or len(username) > 150
        or len(raw_token) > 128
    ):
        return JsonResponse({"error": "The setup code is invalid or expired."}, status=400)
    username = username.strip()
    raw_token = raw_token.strip()
    if not username or not raw_token:
        return JsonResponse({"error": "The setup code is invalid or expired."}, status=400)

    grant = find_valid_enrollment_grant(raw_token)
    if grant is None or grant.user.get_username() != username:
        return JsonResponse({"error": "The setup code is invalid or expired."}, status=400)

    try:
        ceremony, options = create_enrollment_options(grant.user)
    except ImproperlyConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)

    request.session[PASSKEY_ENROLLMENT_CEREMONY_SESSION_KEY] = str(ceremony.pk)
    request.session[PASSKEY_ENROLLMENT_GRANT_SESSION_KEY] = grant.pk
    request.session[PASSKEY_ENROLLMENT_USER_SESSION_KEY] = grant.user.pk
    return JsonResponse({"options": options})


@require_POST
def passkey_enrollment_complete(request):
    grant_id = request.session.pop(PASSKEY_ENROLLMENT_GRANT_SESSION_KEY, None)
    user_id = request.session.pop(PASSKEY_ENROLLMENT_USER_SESSION_KEY, None)
    ceremony = _consume_ceremony(
        request,
        PASSKEY_ENROLLMENT_CEREMONY_SESSION_KEY,
        PasskeyCeremony.Purpose.ENROLLMENT,
        user_id,
    )
    if ceremony is None or grant_id is None:
        return JsonResponse(
            {"error": "The setup challenge expired or was already used. Start setup again."},
            status=400,
        )

    payload = _json_payload(request)
    if payload is None:
        return JsonResponse({"error": "The passkey response was invalid."}, status=400)
    credential_payload = payload.get("credential")
    credential_id = (
        _credential_id(credential_payload)
        if isinstance(credential_payload, dict)
        else None
    )
    if credential_id is None or not isinstance(credential_payload, dict):
        return JsonResponse(
            {"error": "The passkey response was invalid. Reload setup and try again."},
            status=400,
        )

    device_name = payload.get("device_name")
    if not isinstance(device_name, str):
        return JsonResponse(
            {"error": "Enter a name for this device, then reload setup and try again."},
            status=400,
        )
    device_name = device_name.strip()
    if not device_name or len(device_name) > 80:
        return JsonResponse(
            {
                "error": (
                    "Device names must contain 1 to 80 characters. "
                    "Reload setup and try again."
                )
            },
            status=400,
        )

    try:
        configuration = get_webauthn_configuration()
        verification = verify_registration_response(
            credential=credential_payload,
            expected_challenge=base64url_to_bytes(ceremony.challenge),
            expected_rp_id=configuration.rp_id,
            expected_origin=configuration.origin,
            require_user_verification=True,
        )
    except ImproperlyConfigured as exc:
        return JsonResponse({"error": str(exc)}, status=503)
    except (WebAuthnException, TypeError, ValueError, KeyError):
        return JsonResponse(
            {"error": "Passkey registration failed. Reload setup and try again."},
            status=400,
        )

    if verification.credential_id != credential_id:
        return JsonResponse(
            {"error": "Passkey registration failed. Reload setup and try again."},
            status=400,
        )

    now = timezone.now()
    try:
        with transaction.atomic():
            grant = PasskeyEnrollmentGrant.objects.select_for_update().filter(
                pk=grant_id,
                user_id=user_id,
                expires_at__gt=now,
                used_at__isnull=True,
                revoked_at__isnull=True,
            ).first()
            if grant is None or not grant.user.is_active:
                return JsonResponse(
                    {"error": "The setup code is invalid, expired, or already used."},
                    status=400,
                )

            PasskeyCredential.objects.create(
                user=grant.user,
                credential_id=verification.credential_id,
                public_key=verification.credential_public_key,
                sign_count=verification.sign_count,
                device_name=device_name,
            )
            grant.used_at = now
            grant.save(update_fields=("used_at",))
    except IntegrityError:
        return JsonResponse(
            {"error": "This passkey is already registered. Contact an administrator."},
            status=409,
        )

    return JsonResponse({"redirect": redirect("login").url})


@login_required
def attendance_check_in(request):
    if not _passkey_login_required(request):
        return HttpResponseForbidden(
            "Sign in with your passkey before recording attendance."
        )

    if request.method == "POST":
        user_latitude = request.POST.get('latitude')
        user_longitude = request.POST.get('longitude')
        branches = list(Branch.objects.all())

        if not user_latitude or not user_longitude:
            return render(request, "authentication/attendance_check_in.html", {"error": "Location coordinates were not received."})

        if not branches:
            return render(request, "authentication/attendance_check_in.html", {"error": "No branches are configured yet."})

        try:
            nearest_branch, distance = haversion_algo.check_distance(user_latitude, user_longitude, branches)
        except (TypeError, ValueError):
            return render(request, "authentication/attendance_check_in.html", {"error": "Invalid location coordinates received."})
        
        if distance > nearest_branch.geofencing_radius:
            return render(request, "authentication/attendance_check_in.html", {"error": "You are outside the allowed radius."})

        user_check_in_time = timezone.now()
        status_returned = status_check(
            user_check_in_time=user_check_in_time,
            user_branch=nearest_branch,
            username=request.user.username,
        )

        with transaction.atomic():
            User.objects.select_for_update().get(pk=request.user.pk)
            attendance_record = Attendance.objects.filter(
                user=request.user,
                check_in_time__date=timezone.localdate(user_check_in_time),
            ).order_by("check_in_time").first()
            if attendance_record:
                return render(
                    request,
                    "authentication/attendance_check_in.html",
                    {"error": "Attendance is already recorded for today."},
                )
            Attendance.objects.create(
                user=request.user,
                branch=nearest_branch,
                status=status_returned,
                is_verified=True,
            )

        if request.user.role == User.Role.BRANCH_MANAGER:
            return redirect("branch_manager_dashboard")
        else:
            return redirect("employee_dashboard")

    return render(request, 'authentication/attendance_check_in.html')


@login_required
def branch_manager_dashboard(request):
    if request.user.role != User.Role.BRANCH_MANAGER:
        return HttpResponseForbidden("Only branch managers can access this dashboard.")

    if not request.user.branch_id:
        return HttpResponse(
            "Your account is not assigned to a branch yet. Please contact the administrator.",
            status=400,
        )

    return redirect("branch_detail", branch_id=request.user.branch_id)
