# apps/attendance/views.py
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseForbidden
from django.views.generic.base import TemplateView
from apps.attendance.services.dashboard import get_branch_summary, get_branch_detail
from apps.authentication.models import User


class SuperAdminDashboard(TemplateView):
    template_name = 'attendance/admin_dashboard.html'

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
