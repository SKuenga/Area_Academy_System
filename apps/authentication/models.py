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
    related_name="employees"
)


    def __str__(self):
        return self.username