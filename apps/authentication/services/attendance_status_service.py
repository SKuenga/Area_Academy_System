from datetime import datetime, timedelta

from django.utils import timezone

from apps.attendance.models import Attendance
from apps.class_session.models import Class_Session


GRACE_PERIOD_MINUTES = 10


def _day_matches(session_day, check_in_day):
    days = [day.strip().lower() for day in session_day.split(",")]
    return check_in_day.lower() in days


def _scheduled_start_datetime(check_in_time, session):
    local_check_in = timezone.localtime(check_in_time)
    scheduled_start = datetime.combine(local_check_in.date(), session.start_time)

    if timezone.is_naive(scheduled_start):
        return timezone.make_aware(scheduled_start, timezone.get_current_timezone())

    return scheduled_start


def status_check(user_check_in_time, user_branch, username):
    """
    Return the attendance status for a user based on today's class schedule.

    A matching class is looked up by instructor username, branch, and weekday.
    The user is present when they check in on or before the class start time
    plus the configured grace period; otherwise they are late.
    """
    check_in_day = timezone.localtime(user_check_in_time).strftime("%A")

    possible_sessions = Class_Session.objects.filter(
        instructor__username=username,
        branch=user_branch,
    ).order_by("start_time")

    todays_session = next(
        (
            session
            for session in possible_sessions
            if _day_matches(session.day, check_in_day)
        ),
        None,
    )

    if todays_session is None:
        return Attendance.Status.PRESENT

    scheduled_start = _scheduled_start_datetime(user_check_in_time, todays_session)
    late_cutoff = scheduled_start + timedelta(minutes=GRACE_PERIOD_MINUTES)

    if user_check_in_time <= late_cutoff:
        return Attendance.Status.PRESENT

    return Attendance.Status.LATE
