import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import timedelta
from urllib.parse import urlsplit

from django.conf import settings
from django.core.exceptions import ImproperlyConfigured
from django.db import transaction
from django.utils import timezone
from webauthn import (
    generate_authentication_options,
    generate_registration_options,
    options_to_json,
)
from webauthn.helpers.structs import (
    AuthenticatorAttachment,
    AuthenticatorSelectionCriteria,
    PublicKeyCredentialDescriptor,
    ResidentKeyRequirement,
    UserVerificationRequirement,
)

from apps.authentication.models import (
    PasskeyCeremony,
    PasskeyCredential,
    PasskeyEnrollmentGrant,
    User,
)

PASSKEY_GRANT_LIFETIME = timedelta(minutes=30)
PASSKEY_CEREMONY_LIFETIME = timedelta(minutes=2)


@dataclass(frozen=True)
class WebAuthnConfiguration:
    rp_id: str
    rp_name: str
    origin: str


def get_webauthn_configuration() -> WebAuthnConfiguration:
    rp_id = getattr(settings, "WEBAUTHN_RP_ID", "")
    rp_name = getattr(settings, "WEBAUTHN_RP_NAME", "")
    origin = getattr(settings, "WEBAUTHN_ORIGIN", "")
    if not rp_id or not rp_name.strip() or not origin:
        raise ImproperlyConfigured(
            "Set WEBAUTHN_RP_ID, WEBAUTHN_RP_NAME, and WEBAUTHN_ORIGIN "
            "before using passkey authentication."
        )

    try:
        parsed_origin = urlsplit(origin)
    except ValueError as exc:
        raise ImproperlyConfigured("WEBAUTHN_ORIGIN is not a valid origin.") from exc
    origin_host = (parsed_origin.hostname or "").lower().rstrip(".")
    rp_id = rp_id.strip().lower().rstrip(".")
    local_origin = origin_host == "localhost" or origin_host.endswith(".localhost")
    try:
        port = parsed_origin.port
    except ValueError as exc:
        raise ImproperlyConfigured("WEBAUTHN_ORIGIN is not a valid origin.") from exc
    origin_netloc = origin_host
    if port is not None and not (
        (parsed_origin.scheme == "https" and port == 443)
        or (parsed_origin.scheme == "http" and port == 80)
    ):
        origin_netloc = f"{origin_netloc}:{port}"
    canonical_origin = f"{parsed_origin.scheme}://{origin_netloc}"
    if (
        not origin_host
        or not parsed_origin.netloc
        or parsed_origin.username
        or parsed_origin.password
        or parsed_origin.scheme not in ("https", "http")
        or parsed_origin.path
        or parsed_origin.query
        or parsed_origin.fragment
        or origin != canonical_origin
        or (parsed_origin.scheme == "http" and not local_origin)
        or (origin_host != rp_id and not origin_host.endswith(f".{rp_id}"))
    ):
        raise ImproperlyConfigured(
            "WEBAUTHN_ORIGIN must be a canonical HTTPS origin whose hostname "
            "matches WEBAUTHN_RP_ID. HTTP is allowed only on localhost."
        )

    return WebAuthnConfiguration(
        rp_id=rp_id,
        rp_name=rp_name.strip(),
        origin=origin,
    )


def issue_passkey_enrollment_grant(user: User, issued_by: User) -> str:
    raw_token = secrets.token_urlsafe(32)
    now = timezone.now()
    with transaction.atomic():
        PasskeyEnrollmentGrant.objects.filter(
            user=user,
            used_at__isnull=True,
            revoked_at__isnull=True,
        ).update(revoked_at=now)
        PasskeyEnrollmentGrant.objects.create(
            user=user,
            token_digest=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
            created_by=issued_by,
            expires_at=now + PASSKEY_GRANT_LIFETIME,
        )
    return raw_token


def find_valid_enrollment_grant(raw_token: str) -> PasskeyEnrollmentGrant | None:
    digest = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    now = timezone.now()
    return (
        PasskeyEnrollmentGrant.objects.select_related("user")
        .filter(
            token_digest=digest,
            expires_at__gt=now,
            used_at__isnull=True,
            revoked_at__isnull=True,
            user__is_active=True,
        )
        .first()
    )


def _remove_old_ceremonies(now):
    PasskeyCeremony.objects.filter(
        expires_at__lt=now - timedelta(days=1)
    ).delete()


def create_enrollment_options(
    user: User,
) -> tuple[PasskeyCeremony, dict[str, object]]:
    configuration = get_webauthn_configuration()
    credentials = PasskeyCredential.objects.filter(user=user).only("credential_id")
    options = generate_registration_options(
        rp_id=configuration.rp_id,
        rp_name=configuration.rp_name,
        user_id=str(user.pk).encode("utf-8"),
        user_name=user.get_username(),
        user_display_name=user.get_full_name() or user.get_username(),
        timeout=120_000,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=AuthenticatorAttachment.PLATFORM,
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.REQUIRED,
        ),
        exclude_credentials=[
            PublicKeyCredentialDescriptor(id=bytes(credential.credential_id))
            for credential in credentials
        ],
    )
    options_data = json.loads(options_to_json(options))
    now = timezone.now()
    _remove_old_ceremonies(now)
    ceremony = PasskeyCeremony.objects.create(
        user=user,
        purpose=PasskeyCeremony.Purpose.ENROLLMENT,
        challenge=options_data["challenge"],
        expires_at=now + PASSKEY_CEREMONY_LIFETIME,
    )
    return ceremony, options_data


def create_login_options(
    user: User,
) -> tuple[PasskeyCeremony, dict[str, object]]:
    configuration = get_webauthn_configuration()
    credentials = PasskeyCredential.objects.filter(user=user).only("credential_id")
    options = generate_authentication_options(
        rp_id=configuration.rp_id,
        timeout=120_000,
        allow_credentials=[
            PublicKeyCredentialDescriptor(id=bytes(credential.credential_id))
            for credential in credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )
    options_data = json.loads(options_to_json(options))
    now = timezone.now()
    _remove_old_ceremonies(now)
    ceremony = PasskeyCeremony.objects.create(
        user=user,
        purpose=PasskeyCeremony.Purpose.LOGIN,
        challenge=options_data["challenge"],
        expires_at=now + PASSKEY_CEREMONY_LIFETIME,
    )
    return ceremony, options_data
