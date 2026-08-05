# apps/attendance/services/dashboard.py
from apps.attendance.models import Attendance
from apps.authentication.models import User
from apps.branch.models import Branch


def get_branch_summary():
    """Return a list of dicts, one per branch, with attendance counts."""
    branches = Branch.objects.all()
    summary = []

    for branch in branches:
        employees = User.objects.filter(branch=branch, role=User.Role.EMPLOYEE)
        attendance = Attendance.objects.filter(branch=branch)

        summary.append({
            "branch": branch,          # <-- the actual Branch object!
            "employees": employees.count(),
            "present": attendance.filter(status=Attendance.Status.PRESENT).count(),
            "absent": attendance.filter(status=Attendance.Status.ABSENT).count(),
            "late": attendance.filter(status=Attendance.Status.LATE).count(),
            "leave": attendance.filter(status=Attendance.Status.ON_LEAVE).count(),
            "remote": attendance.filter(status=Attendance.Status.REMOTE).count(),
        })

    return summary


def get_branch_detail(branch_id):
    """Return macro summary + micro per-employee breakdown for one branch."""
    branch = Branch.objects.get(id=branch_id)
    employees = User.objects.filter(branch=branch, role=User.Role.EMPLOYEE)
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
