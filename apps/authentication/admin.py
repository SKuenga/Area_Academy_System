from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "AREA Academy",
            {
                "fields": ("role", "branch"),
            },
        ),
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "AREA Academy",
            {
                "fields": ("role", "branch"),
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "role",
        "branch",
        "is_staff",
    )

    list_filter = UserAdmin.list_filter + ("role", "branch")
