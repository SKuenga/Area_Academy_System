# apps/attendance/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from datetime import datetime, timedelta
from typing import cast

from django.http import HttpResponseBadRequest, HttpResponseForbidden
from django.views.generic.base import TemplateView
from django.utils import timezone
from django.utils.http import urlencode

from apps.attendance.services.dashboard import (
    get_branch_detail,
    get_branch_summary,
    get_employee_attendance_summary,
    get_monthly_analytics,
)
from apps.authentication.models import User
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render


class SuperAdminDashboard(LoginRequiredMixin, TemplateView):
    login_url = "/auth/"
    template_name = 'attendance/admin_dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        user = cast(User, request.user)
        if user.role != User.Role.SUPER_ADMIN:
            return HttpResponseForbidden("Only super admins can view this dashboard.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = get_branch_summary()
        context["branches"] = branches

        # Totals for stat cards
        context["total_branches"] = len(branches)
        context["total_employees"] = sum(b["employees"] for b in branches)
        context["total_present"]  = sum(b["present"] for b in branches)
        context["total_absent"]   = sum(b["absent"] for b in branches)
        context["total_late"]     = sum(b["late"] for b in branches)
        context["total_remote"]   = sum(b["remote"] for b in branches)
        context["total_leave"]    = sum(b["leave"] for b in branches)
        context["total_attended"] = (
            context["total_present"] + context["total_late"] + context["total_remote"]
        )
        context["total_attendance_rate"] = (
            round((context["total_attended"] / context["total_employees"]) * 100)
            if context["total_employees"] else 0
        )

        return context


class MonthlyAnalyticsView(LoginRequiredMixin, TemplateView):
    login_url = "/auth/"
    template_name = "attendance/monthly_analytics.html"

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return super().dispatch(request, *args, **kwargs)
        user = cast(User, request.user)
        if user.role not in (User.Role.SUPER_ADMIN, User.Role.BRANCH_MANAGER):
            return HttpResponseForbidden("You do not have permission to view monthly analytics.")
        branch_id = cast(int | None, getattr(user, "branch_id"))
        if user.role == User.Role.BRANCH_MANAGER and branch_id is None:
            return HttpResponse(
                "Your account is not assigned to a branch yet. Please contact the administrator.",
                status=400,
            )
        return super().dispatch(request, *args, **kwargs)

    def get(self, request, *args, **kwargs):
        current_month = timezone.localdate().replace(day=1)
        month_value = request.GET.get("month")
        if month_value:
            try:
                month = datetime.strptime(month_value, "%Y-%m").date().replace(day=1)
            except ValueError:
                return HttpResponseBadRequest("Month must use YYYY-MM format.")
            if month.strftime("%Y-%m") != month_value:
                return HttpResponseBadRequest("Month must use YYYY-MM format.")
            if month > current_month:
                return HttpResponseBadRequest("Future months are not available.")
            self.selected_month = month
        else:
            self.selected_month = current_month
        return super().get(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        current_month = timezone.localdate().replace(day=1)
        month = self.selected_month

        user = cast(User, self.request.user)
        assigned_branch_id = cast(int | None, getattr(user, "branch_id"))
        branch_id = assigned_branch_id if user.role == User.Role.BRANCH_MANAGER else None
        analytics = get_monthly_analytics(month, branch_id=branch_id)
        sort_by = self.request.GET.get("sort", "attendance_rate")
        sort_functions = {
            "attendance_rate": lambda row: row["attendance_rate"],
            "late": lambda row: row["late"],
            "attended": lambda row: row["attended"],
            "absent": lambda row: row["absent"],
        }
        if sort_by not in sort_functions:
            sort_by = "attendance_rate"
        analytics["branches"].sort(key=sort_functions[sort_by], reverse=True)

        selected_branch = self.request.GET.get("branch", "")
        if selected_branch and user.role == User.Role.SUPER_ADMIN:
            analytics["displayed_branches"] = [
                item for item in analytics["branches"]
                if str(item["branch"].id) == selected_branch
            ]
            if not analytics["displayed_branches"]:
                selected_branch = ""
                analytics["displayed_branches"] = analytics["branches"]
        else:
            analytics["displayed_branches"] = analytics["branches"]

        previous_month = month.replace(day=1) - timedelta(days=1)
        previous_month = previous_month.replace(day=1)
        month_after = month.replace(
            year=month.year + (month.month == 12),
            month=month.month % 12 + 1,
            day=1,
        )
        next_month = month_after if month_after <= current_month else None
        next_query = {"month": next_month.strftime("%Y-%m"), "sort": sort_by} if next_month else {}
        previous_query = {"month": previous_month.strftime("%Y-%m"), "sort": sort_by}
        if selected_branch:
            next_query["branch"] = selected_branch
            previous_query["branch"] = selected_branch

        context.update({
            "month": month,
            "current_month": current_month,
            "previous_month_url": f"?{urlencode(previous_query)}",
            "next_month_url": f"?{urlencode(next_query)}" if next_query else None,
            "analytics": analytics,
            "sort_by": sort_by,
            "selected_branch": selected_branch,
            "is_super_admin": user.role == User.Role.SUPER_ADMIN,
        })
        return context


class BranchDetailView(LoginRequiredMixin, TemplateView):
    template_name = 'attendance/branch_detail.html'

    def dispatch(self, request, *args, **kwargs):
        branch_id = kwargs.get("branch_id")

        if request.user.role == User.Role.SUPER_ADMIN:
            return super().dispatch(request, *args, **kwargs)

        if (
            request.user.role == User.Role.BRANCH_MANAGER
            and request.user.branch_id == branch_id
        ):
            return super().dispatch(request, *args, **kwargs)

        return HttpResponseForbidden("You do not have permission to view this branch.")

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branch_id = self.kwargs['branch_id']
        context["branch_data"] = get_branch_detail(branch_id)
        return context

@login_required
def employee_dashboard(request):
    if request.user.role != User.Role.EMPLOYEE:
        return HttpResponseForbidden("You do not have permission to view this page.")
    context = {
        "detail": get_employee_attendance_summary(request.user.id)
    }
    return render(request, "attendance/employee_dashboard.html", context=context)
