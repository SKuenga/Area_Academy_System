from typing import Any
from django.shortcuts import render
from django.views.generic.base import TemplateView
from apps.attendance.services.dashboard import get_branch_summary
class SuperAdminDashboard(TemplateView):
    template_name = 'attendance/admin_dashboard.html'
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        branches = get_branch_summary()
        context["branches"] = branches
        context["total_branches"] = len(branches)
        context["total_employees"] = sum(b["employees"] for b in branches)
        context["total_present"]  = sum(b["present"] for b in branches)
        context["total_absent"]   = sum(b["absent"] for b in branches)
        return context
        