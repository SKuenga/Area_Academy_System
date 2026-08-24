import json
import os
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.dateparse import parse_datetime, parse_time

from apps.attendance.models import Attendance
from apps.authentication.models import User
from apps.branch.models import Branch
from apps.class_session.models import Class_Session


TRUE_VALUES = {"1", "true", "yes", "on"}


class Command(BaseCommand):
    help = "Load initial production data into an empty database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Load bootstrap data even when BOOTSTRAP_PRODUCTION_DATA is not enabled.",
        )

    def handle(self, *args, **options):
        enabled = os.environ.get("BOOTSTRAP_PRODUCTION_DATA", "").lower() in TRUE_VALUES

        if not enabled and not options["force"]:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped production bootstrap because BOOTSTRAP_PRODUCTION_DATA is not True."
                )
            )
            return

        admin_username = (
            os.environ.get("AREA_ADMIN_USERNAME")
            or os.environ.get("DJANGO_SUPERUSER_USERNAME")
            or "Admin"
        )

        if self._has_existing_business_data(admin_username):
            self.stdout.write(
                self.style.WARNING(
                    "Skipped production bootstrap because business data already exists."
                )
            )
            return

        data_path = Path(__file__).resolve().parents[2] / "bootstrap_data" / "production_seed.json"
        with data_path.open(encoding="utf-8") as seed_file:
            seed_data = json.load(seed_file)

        with transaction.atomic():
            branches = self._load_branches(seed_data["branches"])
            users = self._load_users(seed_data["users"])
            class_sessions = self._load_class_sessions(seed_data["class_sessions"])
            attendance = self._load_attendance(seed_data["attendance"])

        self.stdout.write(
            self.style.SUCCESS(
                "Bootstrapped production data: "
                f"{branches} branches, {users} users, "
                f"{class_sessions} class sessions, {attendance} attendance records."
            )
        )

    def _has_existing_business_data(self, admin_username):
        return (
            Branch.objects.exists()
            or Class_Session.objects.exists()
            or Attendance.objects.exists()
            or User.objects.exclude(username=admin_username).exists()
        )

    def _load_branches(self, branches):
        for branch in branches:
            Branch.objects.update_or_create(
                name=branch["name"],
                defaults={
                    "latitude": branch["latitude"],
                    "longitude": branch["longitude"],
                    "geofencing_radius": branch["geofencing_radius"],
                },
            )
        return len(branches)

    def _load_users(self, users):
        for user_data in users:
            branch = Branch.objects.get(name=user_data["branch"])
            user, _ = User.objects.get_or_create(username=user_data["username"])

            user.password = user_data["password"]
            user.last_login = self._parse_datetime_or_none(user_data["last_login"])
            user.is_superuser = user_data["is_superuser"]
            user.first_name = user_data["first_name"]
            user.last_name = user_data["last_name"]
            user.email = user_data["email"]
            user.is_staff = user_data["is_staff"]
            user.is_active = user_data["is_active"]
            user.date_joined = parse_datetime(user_data["date_joined"])
            user.role = user_data["role"]
            user.branch = branch
            user.save()

        return len(users)

    def _load_class_sessions(self, class_sessions):
        for session in class_sessions:
            instructor = User.objects.get(username=session["instructor"])
            branch = Branch.objects.get(name=session["branch"])

            Class_Session.objects.update_or_create(
                session_name=session["session_name"],
                instructor=instructor,
                branch=branch,
                defaults={
                    "day": session["day"],
                    "start_time": parse_time(session["start_time"]),
                    "end_time": parse_time(session["end_time"]),
                },
            )

        return len(class_sessions)

    def _load_attendance(self, attendance_records):
        for record in attendance_records:
            user = User.objects.get(username=record["user"])
            branch = Branch.objects.get(name=record["branch"])
            check_in_time = parse_datetime(record["check_in_time"])

            attendance_record = Attendance.objects.filter(
                user=user,
                branch=branch,
                check_in_time=check_in_time,
            ).first()

            if attendance_record is None:
                attendance_record = Attendance.objects.create(user=user, branch=branch)
                attendance_record.check_in_time = check_in_time

            attendance_record.check_out_time = self._parse_datetime_or_none(
                record["check_out_time"]
            )
            attendance_record.is_verified = record["is_verified"]
            attendance_record.status = record["status"]
            attendance_record.save(
                update_fields=[
                    "check_in_time",
                    "check_out_time",
                    "is_verified",
                    "status",
                ]
            )

        return len(attendance_records)

    def _parse_datetime_or_none(self, value):
        if value is None:
            return None
        return parse_datetime(value)
