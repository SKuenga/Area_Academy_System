from datetime import datetime, time
from io import StringIO
import os
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from apps.attendance.models import Attendance
from apps.authentication.models import User
from apps.authentication.services.attendance_status_service import status_check
from apps.branch.models import Branch
from apps.class_session.models import Class_Session


class AttendanceStatusServiceTests(TestCase):
    def setUp(self):
        self.branch = Branch.objects.create(
            name="Bakixanov",
            latitude=40.409264,
            longitude=49.867092,
            geofencing_radius=100,
        )
        self.user = User.objects.create_user(
            username="instructor",
            password="test-password",
            role=User.Role.EMPLOYEE,
            branch=self.branch,
        )
        Class_Session.objects.create(
            session_name="Foundation English",
            day="Monday, Wednesday",
            start_time=time(9, 0),
            end_time=time(10, 30),
            instructor=self.user,
            branch=self.branch,
        )

    def _check_in_at(self, hour, minute):
        return timezone.make_aware(datetime(2026, 8, 5, hour, minute))

    def test_status_is_present_inside_grace_period(self):
        status = status_check(self._check_in_at(9, 10), self.branch, self.user.username)

        self.assertEqual(status, Attendance.Status.PRESENT)

    def test_status_is_late_after_grace_period(self):
        status = status_check(self._check_in_at(9, 11), self.branch, self.user.username)

        self.assertEqual(status, Attendance.Status.LATE)

    def test_status_is_present_when_no_class_is_scheduled(self):
        status = status_check(self._check_in_at(9, 11), self.branch, "unknown-user")

        self.assertEqual(status, Attendance.Status.PRESENT)


class ProductionBootstrapCommandTests(TestCase):
    def _run_bootstrap(self):
        output = StringIO()
        with patch.dict(os.environ, {"BOOTSTRAP_PRODUCTION_DATA": "True"}):
            call_command("bootstrap_production_data", stdout=output)
        return output.getvalue()

    def test_bootstrap_loads_seed_data_once(self):
        output = self._run_bootstrap()

        self.assertIn("Bootstrapped production data", output)
        self.assertEqual(Branch.objects.count(), 4)
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(Class_Session.objects.count(), 4)
        self.assertEqual(Attendance.objects.count(), 4)
        self.assertEqual(Attendance.objects.filter(check_in_time__year=2026).count(), 4)
        self.assertTrue(
            User.objects.filter(
                username="Admin",
                role=User.Role.SUPER_ADMIN,
                is_staff=True,
                is_superuser=True,
            ).exists()
        )

        second_output = self._run_bootstrap()

        self.assertIn("Skipped production bootstrap", second_output)
        self.assertEqual(Branch.objects.count(), 4)
        self.assertEqual(User.objects.count(), 5)
        self.assertEqual(Class_Session.objects.count(), 4)
        self.assertEqual(Attendance.objects.count(), 4)

    def test_bootstrap_loads_when_only_admin_exists(self):
        User.objects.create_superuser(username="Admin", password="temporary-password")

        output = self._run_bootstrap()

        self.assertIn("Bootstrapped production data", output)
        self.assertEqual(Branch.objects.count(), 4)
        self.assertEqual(User.objects.count(), 5)
