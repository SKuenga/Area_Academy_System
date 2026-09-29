from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin
from django.contrib.admin.utils import unquote
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect

from .models import (
    PasskeyCeremony,
    PasskeyCredential,
    PasskeyEnrollmentGrant,
    User,
)
from .services.passkeys import issue_passkey_enrollment_grant


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    actions = ("delete_selected", "issue_passkey_setup_code")
    change_form_template = "admin/authentication/user/change_form.html"

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
            self._issue_setup_code_for_user(request, user)

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        if request.method == "POST" and "_issue_passkey_setup_code" in request.POST:
            if not self._can_manage_passkeys(request):
                return HttpResponseForbidden(
                    "Only super administrators can issue passkey setup codes."
                )
            if object_id is None:
                return HttpResponseForbidden("A saved employee account is required.")
            user = get_object_or_404(self.model, pk=unquote(object_id))
            self._issue_setup_code_for_user(request, user)
            return redirect(request.path)

        extra_context = extra_context or {}
        extra_context["show_passkey_setup_button"] = (
            self._can_manage_passkeys(request)
            and object_id is not None
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def _issue_setup_code_for_user(self, request, user):
        if not user.is_active:
            self.message_user(
                request,
                f"Skipped inactive account {user.username}.",
                level=messages.WARNING,
            )
            return

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
    fields = (
        "user",
        "device_name",
        "created_at",
        "last_used_at",
        "sign_count",
    )
    readonly_fields = fields

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


@admin.register(PasskeyEnrollmentGrant)
class PasskeyEnrollmentGrantAdmin(admin.ModelAdmin):
    list_display = ("user", "created_by", "created_at", "expires_at", "used_at", "revoked_at")
    list_select_related = ("user", "created_by")
    fields = ("user", "created_by", "created_at", "expires_at", "used_at", "revoked_at")
    readonly_fields = fields

    @staticmethod
    def _can_view(request):
        return (
            request.user.is_superuser
            and getattr(request.user, "role", None) == User.Role.SUPER_ADMIN
        )

    def has_module_permission(self, request):
        return self._can_view(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(PasskeyCeremony)
class PasskeyCeremonyAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "created_at", "expires_at", "consumed_at")
    list_select_related = ("user",)
    fields = ("user", "purpose", "created_at", "expires_at", "consumed_at")
    readonly_fields = fields

    @staticmethod
    def _can_view(request):
        return (
            request.user.is_superuser
            and getattr(request.user, "role", None) == User.Role.SUPER_ADMIN
        )

    def has_module_permission(self, request):
        return self._can_view(request)

    def has_view_permission(self, request, obj=None):
        return self._can_view(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
