from apps.attendance.models import Attendance
from apps.authentication.models import User
from apps.branch.models import Branch


def get_branch_summary():

    branches = Branch.objects.all()

    summary = []

    for branch in branches:

        employees = User.objects.filter(
            branch=branch,
            role=User.Role.EMPLOYEE
        )

        attendance = Attendance.objects.filter(
            branch=branch
        )

        summary.append({

            "branch": branch,

            "employees": employees.count(),

            "present": attendance.filter(
                status=Attendance.Status.PRESENT
            ).count(),

            "absent": attendance.filter(
                status=Attendance.Status.ABSENT
            ).count(),

            "late": attendance.filter(
                status=Attendance.Status.LATE
            ).count(),

            "leave": attendance.filter(
                status=Attendance.Status.ON_LEAVE
            ).count(),

            "remote": attendance.filter(
                status=Attendance.Status.REMOTE
            ).count()

        })

    return summary
