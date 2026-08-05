from django.test import TestCase
from django.urls import reverse

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
