from django.conf import settings
from django.db import models

from apps.branch.models import Branch


class Attendance(models.Model):

    class Status(models.TextChoices):
        PRESENT = "PRESENT", "Present"
        ABSENT = "ABSENT", "Absent"
        LATE = "LATE", "Late"
        ON_LEAVE = "ON_LEAVE", "On Leave"
        REMOTE = "REMOTE", "Remote"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    branch = models.ForeignKey(
        Branch,
        on_delete=models.CASCADE,
        related_name="attendance_records"
    )

    check_in_time = models.DateTimeField(auto_now_add=True)

    check_out_time = models.DateTimeField(
        null=True,
        blank=True
    )

    is_verified = models.BooleanField(default=False)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PRESENT
    )

    def __str__(self):
        return f"{self.user.username} - {self.check_in_time.date()}"