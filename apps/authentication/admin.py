from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import User


@admin.register(User)
class CustomUserAdmin(UserAdmin):

    add_fieldsets = UserAdmin.add_fieldsets + (
        (
            "AREA Academy",
            {
                "fields": ("role",),
            },
        ),
    )

    fieldsets = UserAdmin.fieldsets + (
        (
            "AREA Academy",
            {
                "fields": ("role",),
            },
        ),
    )

    list_display = (
        "username",
        "email",
        "role",
        "is_staff",
    )