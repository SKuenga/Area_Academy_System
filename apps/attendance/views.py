# apps/attendance/views.py
from typing import Any
from django.views.generic.base import TemplateView
from apps.attendance.services.dashboard import get_branch_summary, get_branch_detail


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


class BranchDetailView(TemplateView):
    template_name = 'attendance/branch_detail.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branch_id = self.kwargs['branch_id']
        context["branch_data"] = get_branch_detail(branch_id)
        return context