from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.attendance.services.dashboard import get_branch_detail, get_branch_summary
from apps.authentication.models import User
from apps.branch.models import Branch


class BranchDetailAccessTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name="Main Branch",
            latitude=40.409264,
            longitude=49.867092,
            geofencing_radius=100,
        )
        self.other_branch = Branch.objects.create(
            name="Second Branch",
            latitude=40.410000,
            longitude=49.868000,
            geofencing_radius=100,
        )
        self.super_admin = User.objects.create_user(
            username="super-admin",
            password="test-password",
            role=User.Role.SUPER_ADMIN,
        )
        self.branch_manager = User.objects.create_user(
            username="branch-manager",
            password="test-password",
            role=User.Role.BRANCH_MANAGER,
            branch=self.branch,
        )
        self.unassigned_branch_manager = User.objects.create_user(
            username="unassigned-manager",
            password="test-password",
            role=User.Role.BRANCH_MANAGER,
        )
        self.employee = User.objects.create_user(
            username="employee",
            password="test-password",
            role=User.Role.EMPLOYEE,
            branch=self.branch,
        )

    def test_super_admin_can_view_any_branch_detail(self):
        self.client.force_login(self.super_admin)

        response = self.client.get(reverse("branch_detail", args=[self.other_branch.id]))

        self.assertEqual(response.status_code, 200)

    def test_branch_manager_can_view_assigned_branch_detail(self):
        self.client.force_login(self.branch_manager)

        response = self.client.get(reverse("branch_detail", args=[self.branch.id]))

        self.assertEqual(response.status_code, 200)

    def test_branch_manager_cannot_view_another_branch_detail(self):
        self.client.force_login(self.branch_manager)

        response = self.client.get(reverse("branch_detail", args=[self.other_branch.id]))

        self.assertEqual(response.status_code, 403)

    def test_employee_cannot_view_branch_detail(self):
        self.client.force_login(self.employee)

        response = self.client.get(reverse("branch_detail", args=[self.branch.id]))

        self.assertEqual(response.status_code, 403)

    def test_branch_manager_dashboard_redirects_to_assigned_branch_detail(self):
        self.client.force_login(self.branch_manager)

        response = self.client.get(reverse("branch_manager_dashboard"))

        self.assertRedirects(
            response,
            reverse("branch_detail", args=[self.branch.id]),
            fetch_redirect_response=False,
        )

    def test_branch_manager_dashboard_requires_assigned_branch(self):
        self.client.force_login(self.unassigned_branch_manager)

        response = self.client.get(reverse("branch_manager_dashboard"))

        self.assertEqual(response.status_code, 400)


class DashboardSummaryTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name="Dummy Branch",
            latitude=40.409264,
            longitude=49.867092,
            geofencing_radius=100,
        )
        self.employee = User.objects.create_user(
            username="dummy-staff",
            password="test-password",
            role=User.Role.EMPLOYEE,
            branch=self.branch,
        )
        self.branch_manager = User.objects.create_user(
            username="dummy-manager",
            password="test-password",
            role=User.Role.BRANCH_MANAGER,
            branch=self.branch,
        )

    def _attendance_at(self, user, status, days_ago=0, hour=9):
        record = Attendance.objects.create(
            user=user,
            branch=self.branch,
            status=status,
            is_verified=True,
        )
        record.check_in_time = timezone.now() - timedelta(days=days_ago)
        record.check_in_time = record.check_in_time.replace(hour=hour)
        record.save(update_fields=["check_in_time"])
        return record

    def test_branch_summary_counts_only_todays_latest_status_per_staff_member(self):
        self._attendance_at(self.employee, Attendance.Status.PRESENT, days_ago=3)
        self._attendance_at(self.employee, Attendance.Status.PRESENT, hour=9)
        self._attendance_at(self.employee, Attendance.Status.LATE, hour=10)
        self._attendance_at(self.branch_manager, Attendance.Status.PRESENT, days_ago=2)

        summary = get_branch_summary()[0]

        self.assertEqual(summary["employees"], 2)
        self.assertEqual(summary["present"], 0)
        self.assertEqual(summary["late"], 1)
        self.assertEqual(summary["attendance_rate"], 50)

    def test_branch_detail_breakdown_includes_late_records_for_branch_staff(self):
        self._attendance_at(self.employee, Attendance.Status.PRESENT)
        self._attendance_at(self.employee, Attendance.Status.PRESENT, days_ago=1)
        self._attendance_at(self.employee, Attendance.Status.PRESENT, days_ago=2)
        self._attendance_at(self.employee, Attendance.Status.LATE, days_ago=3)
        self._attendance_at(self.branch_manager, Attendance.Status.LATE)

        detail = get_branch_detail(self.branch.id)
        rows = {row["employee"].username: row for row in detail["employees"]}

        self.assertEqual(detail["summary"]["total_employees"], 2)
        self.assertEqual(rows["dummy-staff"]["present"], 3)
        self.assertEqual(rows["dummy-staff"]["late"], 1)
        self.assertEqual(rows["dummy-manager"]["late"], 1)
