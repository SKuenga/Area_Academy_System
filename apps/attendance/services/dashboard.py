from datetime import datetime, time, timedelta

from django.utils import timezone

from apps.attendance.models import Attendance
from apps.authentication.models import User
from apps.branch.models import Branch


STAFF_ROLES = (User.Role.EMPLOYEE, User.Role.BRANCH_MANAGER)


def _staff_for_branch(branch):
    return User.objects.filter(branch=branch, role__in=STAFF_ROLES)


def _date_range(target_date):
    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(
        datetime.combine(target_date, time.min),
        current_timezone,
    )
    return start, start + timedelta(days=1)


def _latest_statuses_by_user(attendance):
    latest_statuses = {}

    for record in attendance.order_by("-check_in_time", "-id"):
        latest_statuses.setdefault(record.user_id, record.status)

    return latest_statuses


def _count_statuses(statuses):
    return {
        "present": statuses.count(Attendance.Status.PRESENT),
        "absent": statuses.count(Attendance.Status.ABSENT),
        "late": statuses.count(Attendance.Status.LATE),
        "leave": statuses.count(Attendance.Status.ON_LEAVE),
        "remote": statuses.count(Attendance.Status.REMOTE),
    }


def _attendance_rate(counts, total_staff):
    if total_staff == 0:
        return 0

    attended = sum(counts[status] for status in ("present", "late", "remote"))
    return min(round((attended / total_staff) * 100), 100)


def get_branch_summary(target_date=None):
    """Return today's per-branch attendance counts using each staff member's latest status."""
    target_date = target_date or timezone.localdate()
    start, end = _date_range(target_date)
    branches = Branch.objects.all()
    summary = []

    for branch in branches:
        staff = _staff_for_branch(branch)
        attendance = Attendance.objects.filter(
            branch=branch,
            user__in=staff,
            check_in_time__gte=start,
            check_in_time__lt=end,
        )
        latest_statuses = _latest_statuses_by_user(attendance)
        counts = _count_statuses(list(latest_statuses.values()))
        total_staff = staff.count()

        summary.append({
            "branch": branch,
            "employees": total_staff,
            "present": counts["present"],
            "absent": counts["absent"],
            "late": counts["late"],
            "leave": counts["leave"],
            "remote": counts["remote"],
            "attendance_rate": _attendance_rate(counts, total_staff),
        })

    return summary


def get_branch_detail(branch_id):
    """Return macro summary + micro per-employee breakdown for one branch."""
    branch = Branch.objects.get(id=branch_id)
    employees = _staff_for_branch(branch)
    attendance = Attendance.objects.filter(branch=branch)

    # --- Macro ---
    summary = {
        "branch": branch,
        "total_employees": employees.count(),
        "present": attendance.filter(status=Attendance.Status.PRESENT).count(),
        "absent": attendance.filter(status=Attendance.Status.ABSENT).count(),
        "late": attendance.filter(status=Attendance.Status.LATE).count(),
        "leave": attendance.filter(status=Attendance.Status.ON_LEAVE).count(),
        "remote": attendance.filter(status=Attendance.Status.REMOTE).count(),
    }

    # --- Micro ---
    employee_details = []
    for emp in employees:
        emp_attendance = attendance.filter(user=emp)
        employee_details.append({
            "employee": emp,
            "present": emp_attendance.filter(status=Attendance.Status.PRESENT).count(),
            "absent": emp_attendance.filter(status=Attendance.Status.ABSENT).count(),
            "late": emp_attendance.filter(status=Attendance.Status.LATE).count(),
            "leave": emp_attendance.filter(status=Attendance.Status.ON_LEAVE).count(),
            "remote": emp_attendance.filter(status=Attendance.Status.REMOTE).count(),
            "last_attendance": emp_attendance.order_by('-check_in_time').first(),
        })

    return {
        "summary": summary,
        "employees": employee_details,
    }


def get_employee_attendance_summary(user_id):
    """Return a summary of attendance for a specific employee."""
    user = User.objects.get(id=user_id)
    attendance = Attendance.objects.filter(user=user)

    return {
        "employee": user,
        "total_days": attendance.count(),
        "present": attendance.filter(status=Attendance.Status.PRESENT).count(),
        "absent": attendance.filter(status=Attendance.Status.ABSENT).count(),
        "late": attendance.filter(status=Attendance.Status.LATE).count(),
        "leave": attendance.filter(status=Attendance.Status.ON_LEAVE).count(),
        "remote": attendance.filter(status=Attendance.Status.REMOTE).count(),
        "last_attendance": attendance.order_by('-check_in_time').values_list('check_in_time', flat=True).first(),
    }
