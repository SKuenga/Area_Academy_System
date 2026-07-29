from typing import Any
from django.shortcuts import render
from django.views.generic.base import TemplateView
from apps.attendance.services.dashboard import get_branch_summary
from .models import Branch

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

from django.shortcuts import get_object_or_404, render

def branch_detail(request, pk):
    branch = get_object_or_404(Branch, pk=pk)
    return render(request, 'attendance/branch_detail.html', {'branch': branch})
