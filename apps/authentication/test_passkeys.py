import base64
import hashlib
import json
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from apps.authentication.models import (
    PasskeyCredential,
    PasskeyEnrollmentGrant,
    User,
)
from apps.authentication.services.passkeys import issue_passkey_enrollment_grant


def _base64url(value):
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


@override_settings(
    WEBAUTHN_RP_ID="testserver",
    WEBAUTHN_RP_NAME="AREA Academy",
    WEBAUTHN_ORIGIN="https://testserver",
)
class PasskeyFlowTests(TestCase):
    def setUp(self):
        self.employee = User.objects.create_user(
            username="employee",
            password="A-secure-test-password-42",
            role=User.Role.EMPLOYEE,
        )
        self.super_admin = User.objects.create_superuser(
            username="superadmin",
            email="superadmin@example.test",
            password="Another-secure-test-password-42",
            role=User.Role.SUPER_ADMIN,
        )

    def _credential(self, credential_id=b"employee-phone-key"):
        return PasskeyCredential.objects.create(
            user=self.employee,
            credential_id=credential_id,
            public_key=b"credential-public-key",
            sign_count=0,
            device_name="Personal phone",
        )

    def _post_json(self, url, payload):
        return self.client.post(
            url,
            data=json.dumps(payload),
            content_type="application/json",
        )

    def test_employee_without_passkey_cannot_complete_password_login(self):
        response = self.client.post(
            reverse("login"),
            {"username": self.employee.username, "password": "A-secure-test-password-42"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/login.html")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(response, "A passkey is required")

    def test_password_login_does_not_authenticate_before_passkey(self):
        self._credential()

        response = self.client.post(
            reverse("login"),
            {"username": self.employee.username, "password": "A-secure-test-password-42"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "authentication/passkey_login.html")
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertIn("passkey_login_ceremony_id", self.client.session)

    @override_settings(
        WEBAUTHN_RP_ID="other.example",
        WEBAUTHN_ORIGIN="https://testserver",
    )
    def test_mismatched_relying_party_configuration_fails_closed(self):
        self._credential()

        response = self.client.post(
            reverse("login"),
            {"username": self.employee.username, "password": "A-secure-test-password-42"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("_auth_user_id", self.client.session)
        self.assertContains(
            response,
            "WEBAUTHN_ORIGIN must be a canonical HTTPS origin",
        )

    def test_login_passkey_verification_establishes_attendance_session(self):
        credential = self._credential()
        self.client.post(
            reverse("login"),
            {"username": self.employee.username, "password": "A-secure-test-password-42"},
        )
        payload = {
            "id": _base64url(bytes(credential.credential_id)),
            "rawId": _base64url(bytes(credential.credential_id)),
            "type": "public-key",
            "response": {
                "clientDataJSON": "dGVzdA",
                "authenticatorData": "dGVzdA",
                "signature": "dGVzdA",
                "userHandle": None,
            },
        }

        with patch(
            "apps.authentication.views.verify_authentication_response",
            return_value=SimpleNamespace(new_sign_count=1),
        ) as verify:
            response = self._post_json(reverse("passkey_login_complete"), payload)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect"], reverse("attendance_check_in"))
        self.assertEqual(verify.call_args.kwargs["require_user_verification"], True)
        self.assertEqual(
            self.client.session["passkey_authenticated_user_id"],
            self.employee.pk,
        )
        credential.refresh_from_db()
        self.assertEqual(credential.sign_count, 1)
        self.assertIsNotNone(credential.last_used_at)
        self.assertEqual(self.client.get(reverse("attendance_check_in")).status_code, 200)

        credential.delete()
        self.assertEqual(self.client.get(reverse("attendance_check_in")).status_code, 403)

    def test_invalid_login_response_consumes_challenge_and_cannot_be_replayed(self):
        credential = self._credential()
        self.client.post(
            reverse("login"),
            {"username": self.employee.username, "password": "A-secure-test-password-42"},
        )
        valid_shape = {
            "id": _base64url(bytes(credential.credential_id)),
            "rawId": _base64url(bytes(credential.credential_id)),
            "type": "public-key",
            "response": {
                "clientDataJSON": "dGVzdA",
                "authenticatorData": "dGVzdA",
                "signature": "dGVzdA",
                "userHandle": None,
            },
        }

        invalid_response = self._post_json(
            reverse("passkey_login_complete"),
            {"not": "a credential"},
        )
        with patch("apps.authentication.views.verify_authentication_response") as verify:
            replay_response = self._post_json(
                reverse("passkey_login_complete"),
                valid_shape,
            )

        self.assertEqual(invalid_response.status_code, 400)
        self.assertEqual(replay_response.status_code, 400)
        verify.assert_not_called()

    def test_password_only_session_cannot_open_attendance_check_in(self):
        self.client.force_login(self.employee)

        response = self.client.get(reverse("attendance_check_in"))

        self.assertEqual(response.status_code, 403)

    def test_setup_code_is_stored_as_a_digest_and_expires(self):
        raw_token = issue_passkey_enrollment_grant(self.employee, self.super_admin)
        grant = PasskeyEnrollmentGrant.objects.get(user=self.employee)

        self.assertEqual(
            grant.token_digest,
            hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        )
        self.assertNotEqual(grant.token_digest, raw_token)
        self.assertGreater(grant.expires_at, timezone.now())

    def test_enrollment_requires_valid_code_and_matching_username(self):
        raw_token = issue_passkey_enrollment_grant(self.employee, self.super_admin)

        response = self._post_json(
            reverse("passkey_enrollment_options"),
            {"username": self.super_admin.username, "setup_code": raw_token},
        )

        self.assertEqual(response.status_code, 400)
        self.assertNotIn("passkey_enrollment_ceremony_id", self.client.session)

    def test_enrollment_registers_credential_and_consumes_setup_code_once(self):
        raw_token = issue_passkey_enrollment_grant(self.employee, self.super_admin)
        options_response = self._post_json(
            reverse("passkey_enrollment_options"),
            {"username": self.employee.username, "setup_code": raw_token},
        )
        self.assertEqual(options_response.status_code, 200)
        self.assertEqual(
            options_response.json()["options"]["authenticatorSelection"]["userVerification"],
            "required",
        )

        credential_id = b"new-employee-phone-key"
        credential_response = {
            "id": _base64url(credential_id),
            "rawId": _base64url(credential_id),
            "type": "public-key",
            "response": {
                "clientDataJSON": "dGVzdA",
                "attestationObject": "dGVzdA",
                "transports": ["internal"],
            },
        }
        with patch(
            "apps.authentication.views.verify_registration_response",
            return_value=SimpleNamespace(
                credential_id=credential_id,
                credential_public_key=b"new-public-key",
                sign_count=0,
            ),
        ) as verify:
            response = self._post_json(
                reverse("passkey_enrollment_complete"),
                {
                    "credential": credential_response,
                    "device_name": "Employee phone",
                },
            )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["redirect"], reverse("login"))
        self.assertEqual(verify.call_args.kwargs["require_user_verification"], True)
        self.assertTrue(
            PasskeyCredential.objects.filter(
                user=self.employee,
                credential_id=credential_id,
                device_name="Employee phone",
            ).exists()
        )
        grant = PasskeyEnrollmentGrant.objects.get(user=self.employee)
        self.assertIsNotNone(grant.used_at)

        reused_code_response = self._post_json(
            reverse("passkey_enrollment_options"),
            {"username": self.employee.username, "setup_code": raw_token},
        )
        self.assertEqual(reused_code_response.status_code, 400)

    def test_expired_setup_code_is_rejected(self):
        raw_token = issue_passkey_enrollment_grant(self.employee, self.super_admin)
        PasskeyEnrollmentGrant.objects.filter(user=self.employee).update(
            expires_at=timezone.now() - timedelta(seconds=1)
        )

        response = self._post_json(
            reverse("passkey_enrollment_options"),
            {"username": self.employee.username, "setup_code": raw_token},
        )

        self.assertEqual(response.status_code, 400)
