# Passkey Attendance Security: What Changed and How to Set It Up

## The original problem

An employee could give a coworker her username and password. The coworker could then sign in as her and record attendance from their own phone. The branch location check only checks the submitted location; it does not establish who is using the account.

## The short explanation

An employee now needs two things to sign in for attendance:

1. Her username and password.
2. A passkey registered to her account, approved on her phone using the phone's screen lock, fingerprint, or face unlock.

The one-time setup code is only permission to create that passkey. It is not the passkey itself and is not stored as the passkey on the phone. The employee enters it once during setup, then the phone creates and keeps the passkey. The site stores information needed to recognize it; the site does not receive the employee's fingerprint, face, phone PIN, or factory phone serial number.

If the employee gives her password to a coworker, the coworker can pass the password step, but cannot normally complete the next step using their own phone. The phone holding the registered passkey must approve the sign-in.

This reduces password-only impersonation. It does not stop an employee from lending her unlocked phone, sharing the phone's screen-lock code, approving a prompt for someone else, or synchronizing the passkey to another device.

## Why only “Passkey Credentials” appeared before

The database migration already creates three models:

- **Passkey Credentials** stores registered employee passkeys.
- **Passkey Enrollment Grants** stores setup-code records and their status.
- **Passkey Ceremonies** stores short-lived login/setup challenges.

Only Passkey Credentials had been registered in Django Admin, so the other two did not appear in its model list even though they existed in the code and database schema. They are now registered as read-only admin pages for super administrators. The raw setup-code digest and challenge value are intentionally not displayed.

The credential screen is intentionally not a place to add a passkey manually. A passkey must be created by the employee's phone and checked by the website during registration; manually adding a row would bypass that proof. When a passkey has been enrolled, a super administrator can select its row and use the normal **Delete selected** admin action to revoke that credential.

## What was corrected in this follow-up

- Added **Issue one-time passkey setup code** to the saved employee's User detail page, with an in-person verification warning and confirmation. It remains available as an action on the Users list as well.
- Registered Passkey Enrollment Grants and Passkey Ceremonies in Django Admin so their records and status can be inspected.
- Kept the grant and ceremony pages read-only, and hid the setup-code digest and challenge values.
- Kept credentials non-addable and non-editable, while retaining controlled deletion for recovery.
- Added tests for the detail-page setup button, permission checks, admin record visibility, secret hiding, and credential add/change restrictions.

The setup button is for an already-saved user account. Create and save a new employee account first; then open that employee's detail page and issue the code.

## How a super administrator issues a code

The action is available in either of these places:

### From the employee detail page

1. Sign in to Django Admin as an account with **Staff status**, **Superuser status**, and application **Role = Super Admin**.
2. Go to **Authentication → Users** and open the saved employee's username.
3. Verify the employee's identity in person.
4. Press **Issue one-time passkey setup code** near the bottom of the user form and confirm.
5. Read the one-time code from the Django Admin success message and give it directly to that employee.

### From the Users list

1. Go to **Authentication → Users**.
2. Select the checkbox beside the saved employee.
3. Choose **Issue passkey setup code (verify employee identity in person)** in the **Action** menu, then press **Go**.
4. Give the code shown in the success message directly to that employee.

The code expires after 30 minutes, can be used once, and is stored in the database only as a one-way digest. Issuing another code revokes any older unused code for that employee. Do not send setup codes in a public chat or leave them visible after handoff.

If the action is not shown, check that the logged-in account has all three required statuses above, that the user account has been saved, and that the deployment includes the current authentication Admin code and template.

## How the employee registers a phone

1. The employee opens the real attendance website on the phone/browser she plans to use.
2. She visits `/auth/passkeys/enroll/`.
3. She enters her username, the one-time code, and a recognizable label such as “Personal phone”.
4. She presses **Continue**, then **Create passkey on this device**.
5. She approves the phone's prompt using its screen lock, fingerprint, or face unlock.
6. After successful registration, she returns to login and tests signing in with her username, password, and the phone prompt.

Repeat this process for each employee and branch manager. There is no one-phone-only rule: if another passkey/device is needed, a super administrator must verify the employee and issue another setup code.

## What happens on a normal attendance day

1. The employee scans the existing QR code and reaches the login page.
2. She enters her username and password.
3. The site asks the browser to verify a registered passkey.
4. She approves the prompt on her phone.
5. The site checks that the response came from the expected website, matches the fresh challenge, and includes the required phone verification.
6. After verification, the employee reaches the attendance page. The existing GPS/geofence check still runs when she checks in.

The QR code has not been changed to a rotating code. It remains an entry link. GPS is still a location signal and should not be treated as proof of the employee's identity or proof that location data cannot be faked.

## Deployment and initialization checklist

1. Deploy the code and install the dependencies from `requirements.txt`, including `webauthn==3.0.1`.
2. Configure these deployment environment variables:
   - `WEBAUTHN_RP_NAME`: human-readable name shown by the phone, for example `AREA Academy Attendance`.
   - `WEBAUTHN_RP_ID`: site host name, for example `attendance.example.com`.
   - `WEBAUTHN_ORIGIN`: exact site origin, for example `https://attendance.example.com` (include a non-default port if the site uses one; do not include a path or trailing slash).
3. Use HTTPS in production. Plain HTTP is accepted only for local development on `localhost`. In production the passkey code fails closed if the relying-party settings are missing or inconsistent.
4. Apply database migrations with `python manage.py migrate`; this applies migration `0006_passkeyceremony_passkeycredential_and_more` when it has not yet been applied.
5. Run the project's normal static-file deployment/collection process so the new passkey JavaScript is served.
6. Confirm that at least one administrator has Django Staff status, Django Superuser status, and application Role set to Super Admin.
7. Have that administrator enroll their own passkey if they need to record attendance. An administrator with no registered passkey can still use password login to access Django Admin for initial setup, but that password-only administrator session cannot record attendance.
8. Enroll employees one at a time using the steps above, then test on the actual production domain and supported employee phones before relying on records for payroll.

The code and tests were checked with Django's system checks and an isolated SQLite test database. The checks do not apply migrations to the live database or verify passkey prompts on every real phone/browser; do those checks in the target deployment before enabling the process for everyone.

## File guide

### New files for the passkey feature

- `apps/authentication/migrations/0006_passkeyceremony_passkeycredential_and_more.py` — creates the database tables for passkeys, setup grants, and short-lived challenges.
- `apps/authentication/services/passkeys.py` — prepares passkey setup/login instructions, validates website configuration, issues expiring setup codes, and creates challenges.
- `apps/authentication/static/authentication/passkey.js` — calls the browser's built-in passkey feature and sends its response to the server.
- `apps/authentication/templates/authentication/passkey_enrollment.html` — employee page for using a setup code to register a phone passkey.
- `apps/authentication/templates/authentication/passkey_login.html` — page shown after the password step to ask for the registered passkey.
- `apps/authentication/test_passkeys.py` — tests the setup, login, replay-prevention, and attendance-protection paths.
- `apps/authentication/templates/admin/authentication/user/change_form.html` — adds the setup-code button to a saved user's Django Admin detail page.
- `security_issue.md` — this setup and operations guide.

### Updated existing files

- `apps/authentication/models.py` — defines the credential, setup grant, and challenge records.
- `apps/authentication/admin.py` — provides the setup-code actions and safe admin visibility/recovery controls.
- `apps/authentication/views.py` and `apps/authentication/urls.py` — connect the password, passkey enrollment/login, and attendance checks.
- `apps/authentication/templates/authentication/login.html` — directs users who have not enrolled to the setup page/admin.
- `area_academy/settings.py` — reads relying-party settings from deployment environment variables.
- `requirements.txt` — adds the WebAuthn server library.
- `README.md` — includes the operational passkey overview and initial setup notes.

## Attendance behavior not included

This change does not add a checkout button, dynamic branch QR codes, an approved leave process, or payroll integration. Check-in remains a once-per-local-date event and the existing branch geofence remains a separate check. Define leave, corrections, missed check-ins, manager overrides, and checkout rules before using attendance data for automatic payroll.
