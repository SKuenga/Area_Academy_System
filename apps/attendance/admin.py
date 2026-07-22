from django.contrib import admin

from .models import Attendance


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):

    list_display = (
        "user",
        "branch",
        "status",
        "check_in_time",
        "is_verified",
    )

    list_filter = (
        "status",
        "branch",
        "is_verified",
    )

    search_fields = (
        "user__username",
    )