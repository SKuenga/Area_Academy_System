from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    class Role(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        BRANCH_MANAGER = "BRANCH_MANAGER", "Branch Manager"
        EMPLOYEE = "EMPLOYEE", "Employee"

    role = models.CharField(
        max_length=30,
        choices=Role.choices,
        default=Role.EMPLOYEE
    )

    branch = models.ForeignKey(
        "branch.Branch",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="employees",
    )


    def __str__(self):
        return self.username


class PasskeyCredential(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="passkey_credentials",
    )
    credential_id = models.BinaryField(unique=True)
    public_key = models.BinaryField()
    sign_count = models.PositiveBigIntegerField(default=0)
    device_name = models.CharField(max_length=80)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("created_at",)

    def __str__(self):
        return f"{self.user.username} - {self.device_name}"


class PasskeyEnrollmentGrant(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="passkey_enrollment_grants",
    )
    token_digest = models.CharField(max_length=64, unique=True)
    created_by = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="issued_passkey_enrollment_grants",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    revoked_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Passkey setup for {self.user.username}"


class PasskeyCeremony(models.Model):
    class Purpose(models.TextChoices):
        LOGIN = "LOGIN", "Login"
        ENROLLMENT = "ENROLLMENT", "Enrollment"

    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="passkey_ceremonies",
    )
    purpose = models.CharField(max_length=16, choices=Purpose.choices)
    challenge = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    consumed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.purpose} ceremony for {self.user.username}"
