from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin

from .models import PasskeyCredential, User
from .services.passkeys import issue_passkey_enrollment_grant


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    actions = ("delete_selected", "issue_passkey_setup_code")

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

    @admin.action(
        description="Issue passkey setup code (verify employee identity in person)"
    )
    def issue_passkey_setup_code(self, request, queryset):
        if not self._can_manage_passkeys(request):
            self.message_user(
                request,
                "Only super administrators can issue passkey setup codes.",
                level=messages.ERROR,
            )
            return

        for user in queryset:
            if not user.is_active:
                self.message_user(
                    request,
                    f"Skipped inactive account {user.username}.",
                    level=messages.WARNING,
                )
                continue
            raw_token = issue_passkey_enrollment_grant(user, request.user)
            self.message_user(
                request,
                (
                    f"One-time passkey setup code for {user.username}: {raw_token}. "
                    "Give it directly to the employee; it expires in 30 minutes."
                ),
                level=messages.SUCCESS,
            )

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not self._can_manage_passkeys(request):
            actions.pop("issue_passkey_setup_code", None)
        return actions

    @staticmethod
    def _can_manage_passkeys(request):
        return (
            request.user.is_superuser
            and getattr(request.user, "role", None) == User.Role.SUPER_ADMIN
        )


@admin.register(PasskeyCredential)
class PasskeyCredentialAdmin(admin.ModelAdmin):
    list_display = ("user", "device_name", "created_at", "last_used_at")
    list_display_links = None
    list_select_related = ("user",)
    readonly_fields = (
        "user",
        "device_name",
        "created_at",
        "last_used_at",
        "sign_count",
    )

    @staticmethod
    def _can_manage_passkeys(request):
        return (
            request.user.is_superuser
            and getattr(request.user, "role", None) == User.Role.SUPER_ADMIN
        )

    def has_module_permission(self, request):
        return self._can_manage_passkeys(request)

    def has_view_permission(self, request, obj=None):
        return self._can_manage_passkeys(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return self._can_manage_passkeys(request)
