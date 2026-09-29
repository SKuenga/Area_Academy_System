import calendar
from dataclasses import dataclass, field
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


def _month_range(month):
    start_month = month.replace(day=1)
    next_month_year = month.year + (month.month == 12)
    next_month_number = month.month % 12 + 1
    end_month = month.replace(year=next_month_year, month=next_month_number, day=1)
    current_timezone = timezone.get_current_timezone()
    return (
        timezone.make_aware(datetime.combine(start_month, time.min), current_timezone),
        timezone.make_aware(datetime.combine(end_month, time.min), current_timezone),
    )


@dataclass
class _MonthlyBranchSummary:
    branch: Branch
    employees: int
    present: int = 0
    absent: int = 0
    late: int = 0
    leave: int = 0
    remote: int = 0
    weekdays: dict[str, int] = field(default_factory=lambda: {day: 0 for day in calendar.day_name})
    periods: dict[str, int] = field(default_factory=lambda: {"Morning": 0, "Afternoon": 0, "Evening": 0})

    def as_dict(self):
        total_records = self.present + self.absent + self.late + self.leave + self.remote
        attended = self.present + self.late + self.remote
        return {
            "branch": self.branch,
            "employees": self.employees,
            "present": self.present,
            "absent": self.absent,
            "late": self.late,
            "leave": self.leave,
            "remote": self.remote,
            "weekdays": self.weekdays,
            "periods": self.periods,
            "total_records": total_records,
            "attended": attended,
            "attendance_rate": round(attended / total_records * 100, 1) if total_records else 0,
            "present_percentage": round(self.present / total_records * 100, 1) if total_records else 0,
            "absent_percentage": round(self.absent / total_records * 100, 1) if total_records else 0,
            "peak_day": max(self.weekdays, key=lambda day: self.weekdays[day]) if attended else None,
            "peak_period": max(self.periods, key=lambda period: self.periods[period]) if attended else None,
        }


def get_monthly_analytics(month, branch_id=None):
    """Summarize each staff member's latest attendance status per day for a month."""
    start, end = _month_range(month)
    branches = Branch.objects.order_by("name")
    if branch_id is not None:
        branches = branches.filter(id=branch_id)

    branch_data = {
        branch.pk: _MonthlyBranchSummary(
            branch=branch,
            employees=_staff_for_branch(branch).count(),
        )
        for branch in branches
    }

    records = Attendance.objects.filter(
        branch_id__in=branch_data,
        user__role__in=STAFF_ROLES,
        check_in_time__gte=start,
        check_in_time__lt=end,
    ).select_related("branch", "user").order_by("check_in_time", "id")
    latest_by_staff_day = {}
    for record in records:
        local_time = timezone.localtime(record.check_in_time)
        key = (record.branch.pk, record.user.pk, local_time.date())
        latest_by_staff_day[key] = (record.status, local_time)

    for (branch_id, _, day), (status, local_time) in latest_by_staff_day.items():
        summary = branch_data[branch_id]
        if status == Attendance.Status.PRESENT:
            summary.present += 1
        elif status == Attendance.Status.ABSENT:
            summary.absent += 1
        elif status == Attendance.Status.LATE:
            summary.late += 1
        elif status == Attendance.Status.ON_LEAVE:
            summary.leave += 1
        elif status == Attendance.Status.REMOTE:
            summary.remote += 1
        else:
            continue

        if status in (Attendance.Status.PRESENT, Attendance.Status.LATE, Attendance.Status.REMOTE):
            summary.weekdays[day.strftime("%A")] += 1
            if local_time.hour < 12:
                summary.periods["Morning"] += 1
            elif local_time.hour < 17:
                summary.periods["Afternoon"] += 1
            else:
                summary.periods["Evening"] += 1

    monthly_summaries = list(branch_data.values())
    summaries = [summary.as_dict() for summary in monthly_summaries]

    all_weekdays: dict[str, int] = {day: 0 for day in calendar.day_name}
    all_periods: dict[str, int] = {"Morning": 0, "Afternoon": 0, "Evening": 0}
    for summary in monthly_summaries:
        for day, count in summary.weekdays.items():
            all_weekdays[day] += count
        for period, count in summary.periods.items():
            all_periods[period] += count

    total_employees = sum(item.employees for item in monthly_summaries)
    total_present = sum(item.present for item in monthly_summaries)
    total_absent = sum(item.absent for item in monthly_summaries)
    total_late = sum(item.late for item in monthly_summaries)
    total_leave = sum(item.leave for item in monthly_summaries)
    total_remote = sum(item.remote for item in monthly_summaries)
    total_records = total_present + total_absent + total_late + total_leave + total_remote
    total_attended = total_present + total_late + total_remote
    weekday_rows = [
        {
            "name": day,
            "count": count,
            "percentage": round(count / total_attended * 100, 1) if total_attended else 0,
        }
        for day, count in all_weekdays.items()
    ]
    period_rows = [
        {
            "name": period,
            "count": count,
            "percentage": round(count / total_attended * 100, 1) if total_attended else 0,
        }
        for period, count in all_periods.items()
    ]
    totals = {
        "employees": total_employees,
        "present": total_present,
        "absent": total_absent,
        "late": total_late,
        "leave": total_leave,
        "remote": total_remote,
        "total_records": total_records,
        "attended": total_attended,
        "attendance_rate": round(total_attended / total_records * 100, 1) if total_records else 0,
        "present_percentage": round(total_present / total_records * 100, 1) if total_records else 0,
        "absent_percentage": round(total_absent / total_records * 100, 1) if total_records else 0,
        "weekdays": all_weekdays,
        "periods": all_periods,
        "peak_day": max(all_weekdays, key=lambda day: all_weekdays[day]) if total_attended else None,
        "peak_period": max(all_periods, key=lambda period: all_periods[period]) if total_attended else None,
        "weekday_rows": weekday_rows,
        "period_rows": period_rows,
    }

    ranked = [item for item in summaries if item["total_records"]]
    return {
        "branches": summaries,
        "totals": totals,
        "highest_branch": max(ranked, key=lambda item: item["attended"]) if ranked else None,
        "lowest_branch": min(ranked, key=lambda item: item["attended"]) if ranked else None,
        "highest_rate_branch": max(ranked, key=lambda item: item["attendance_rate"]) if ranked else None,
        "lowest_rate_branch": min(ranked, key=lambda item: item["attendance_rate"]) if ranked else None,
    }


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
    start, end = _month_range(timezone.localdate())
    attendance = Attendance.objects.filter(
        branch=branch,
        check_in_time__gte=start,
        check_in_time__lt=end,
    )

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
