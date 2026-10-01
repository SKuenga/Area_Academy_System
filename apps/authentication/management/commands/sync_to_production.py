import os
import sys
import dj_database_url
from django.conf import settings
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction, connections


class Command(BaseCommand):
    help = "Safely syncs specific local database records out to the production database environment."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass safety confirmation check prompts',
        )

    def handle(self, *args, **options):
        # 1. Retrieve the production database URL from environment variables
        prod_db_url = os.environ.get('PRODUCTION_DATABASE_URL')
        if not prod_db_url:
            self.stderr.write(
                self.style.ERROR(
                    "Error: PRODUCTION_DATABASE_URL is not set in environment variables. Cannot target production."
                )
            )
            sys.exit(1)

        # 2. Dynamically add the production database configuration to settings
        settings.DATABASES['production'] = dj_database_url.parse(prod_db_url)

        if not options['force']:
            confirm = input("WARNING: You are about to modify your live production database. Proceed? (y/N): ")
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING("Sync operation cancelled."))
                return

        # Explicitly define models you want to push (avoid internal auth permissions/contenttypes)
        MODELS_TO_SYNC = [
            'branch.Branch',
            'authentication.User',
            'attendance.Attendance',
            'class_session.ClassSession',
        ]

        try:
            # Wrap in a transaction block targeting production database routing
            with transaction.atomic(using='production'):
                for model_path in MODELS_TO_SYNC:
                    model = apps.get_model(model_path)
                    self.stdout.write(f"Syncing records for model: {model.__name__}...")

                    # Fetch records sitting inside your local database ('default')
                    local_records = model.objects.using('default').all()

                    for record in local_records:
                        # Use save(using='production') to write directly across the connection wire
                        record.save(using='production')

            self.stdout.write(self.style.SUCCESS("Successfully synced local changes to production!"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Sync aborted due to critical error: {e}"))
            sys.exit(1)
        finally:
            # Clean up active connection to production after sync completes
            if 'production' in connections:
                connections['production'].close()