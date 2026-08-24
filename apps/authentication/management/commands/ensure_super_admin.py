import os

from django.core.management.base import BaseCommand

from apps.authentication.models import User


class Command(BaseCommand):
    help = "Create or update the initial AREA Academy super admin from environment variables."

    def add_arguments(self, parser):
        parser.add_argument(
            "--username",
            default=os.environ.get("AREA_ADMIN_USERNAME")
            or os.environ.get("DJANGO_SUPERUSER_USERNAME")
            or "Admin",
            help="Super admin username. Defaults to AREA_ADMIN_USERNAME, DJANGO_SUPERUSER_USERNAME, then Admin.",
        )
        parser.add_argument(
            "--email",
            default=os.environ.get("AREA_ADMIN_EMAIL")
            or os.environ.get("DJANGO_SUPERUSER_EMAIL")
            or "",
            help="Super admin email. Defaults to AREA_ADMIN_EMAIL or DJANGO_SUPERUSER_EMAIL.",
        )
        parser.add_argument(
            "--password",
            default=os.environ.get("AREA_ADMIN_PASSWORD")
            or os.environ.get("DJANGO_SUPERUSER_PASSWORD"),
            help="Super admin password. Defaults to AREA_ADMIN_PASSWORD or DJANGO_SUPERUSER_PASSWORD.",
        )

    def handle(self, *args, **options):
        username = options["username"]
        email = options["email"]
        password = options["password"]

        if not password:
            self.stdout.write(
                self.style.WARNING(
                    "Skipped super admin setup because AREA_ADMIN_PASSWORD or "
                    "DJANGO_SUPERUSER_PASSWORD is not set."
                )
            )
            return

        user, created = User.objects.get_or_create(username=username)
        user.email = email
        user.role = User.Role.SUPER_ADMIN
        user.is_staff = True
        user.is_superuser = True
        user.is_active = True
        user.set_password(password)
        user.save(
            update_fields=[
                "email",
                "role",
                "is_staff",
                "is_superuser",
                "is_active",
                "password",
            ]
        )

        action = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(f"{action} super admin user '{username}'."))
