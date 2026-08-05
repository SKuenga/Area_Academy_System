from datetime import time

from django.core.management.base import BaseCommand

from apps.authentication.models import User
from apps.branch.models import Branch
from apps.class_session.models import Class_Session


class Command(BaseCommand):
    help = "Create dummy class sessions for existing AREA Academy users and branches."

    def handle(self, *args, **options):
        branches = list(Branch.objects.order_by("id"))
        instructors = list(
            User.objects.exclude(role=User.Role.SUPER_ADMIN).order_by("id")
        )

        if not branches:
            self.stdout.write(self.style.WARNING("No branches found. Create branches first."))
            return

        if not instructors:
            self.stdout.write(self.style.WARNING("No instructors found. Create users first."))
            return

        dummy_sessions = [
            ("Foundation English", "Monday, Wednesday", time(9, 0), time(10, 30)),
            ("IELTS Speaking", "Tuesday, Thursday", time(11, 0), time(12, 30)),
            ("Academic Writing", "Friday", time(15, 0), time(16, 30)),
        ]

        created = 0
        for index, instructor in enumerate(instructors):
            branch = instructor.branch or branches[index % len(branches)]
            session_name, day, start_time, end_time = dummy_sessions[index % len(dummy_sessions)]

            _, was_created = Class_Session.objects.update_or_create(
                instructor=instructor,
                branch=branch,
                session_name=session_name,
                defaults={
                    "day": day,
                    "start_time": start_time,
                    "end_time": end_time,
                },
            )
            created += int(was_created)

        self.stdout.write(
            self.style.SUCCESS(
                f"Seeded class sessions for {len(instructors)} users ({created} created)."
            )
        )
