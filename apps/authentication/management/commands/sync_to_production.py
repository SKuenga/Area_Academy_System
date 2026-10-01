import os
import sys
from urllib.parse import quote
import dj_database_url

from django.conf import settings
from django.core.management.base import BaseCommand
from django.apps import apps
from django.db import transaction, connections, connection


class Command(BaseCommand):
    help = "Safely syncs local records into production using update_or_create and resets PK sequences."

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Bypass safety confirmation check prompts',
        )

    def handle(self, *args, **options):
        # 1. Build local connection URI from environment variables
        local_db_name = os.environ.get('DB_NAME', 'area_academy_db')
        password = quote(os.environ.get('DB_PASSWORD', 'anonymousmrbeast@404'))
        host = os.environ.get('DB_HOST', 'localhost')
        port = os.environ.get('DB_PORT', '5432')
        user = os.environ.get('DB_USER', 'postgres')

        local_url = f"postgres://{user}:{password}@{host}:{port}/{local_db_name}"

        # Dynamically inject 'local' database target into memory settings
        settings.DATABASES['local'] = dj_database_url.parse(local_url)

        if not options['force']:
            confirm = input(
                "WARNING: You are about to sync local data into your live PRODUCTION database ('default'). Proceed? (y/N): "
            )
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING("Sync operation cancelled."))
                return

        # Define models in order of foreign key dependencies (Parents -> Children)
        MODELS_TO_SYNC = [
            'branch.Branch',
            'authentication.User',
            'attendance.Attendance',
            'class_session.ClassSession',
        ]

        try:
            with transaction.atomic(using='default'):
                for model_path in MODELS_TO_SYNC:
                    model = apps.get_model(model_path)
                    pk_name = model._meta.pk.name
                    self.stdout.write(f"Syncing records for model: {model.__name__}...")

                    # Fetch all local records from temporary 'local' connection
                    local_records = model.objects.using('local').all()

                    for record in local_records:
                        # Extract non-relational and foreign key field values
                        record_data = {}
                        for field in model._meta.concrete_fields:
                            # Use attname to preserve raw foreign key IDs (e.g., user_id instead of user object)
                            record_data[field.attname] = getattr(record, field.attname)

                        # Separate primary key for lookup and remaining fields for defaults
                        lookup_kwargs = {pk_name: record_data.pop(pk_name)}

                        # Perform idempotent update or create on production ('default')
                        model.objects.using('default').update_or_create(
                            **lookup_kwargs,
                            defaults=record_data
                        )

                    # 2. Reset PostgreSQL sequence for auto-increment PKs on production
                    if model._meta.pk.get_internal_type() in ['AutoField', 'BigAutoField', 'SmallAutoField']:
                        self.reset_postgres_sequence(model)

            self.stdout.write(self.style.SUCCESS("Successfully synced local changes to production and updated PK sequences!"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"Sync aborted due to critical error: {e}"))
            sys.exit(1)
        finally:
            if 'local' in connections:
                connections['local'].close()

    def reset_postgres_sequence(self, model):
        """Fixes PostgreSQL PK sequence (nextval) drift on production database."""
        table_name = model._meta.db_table
        pk_column = model._meta.pk.column

        # SQL to reset sequence value to MAX(pk) + 1
        sql = f"""
            SELECT setval(
                pg_get_serial_sequence('{table_name}', '{pk_column}'),
                COALESCE((SELECT MAX({pk_column}) FROM {table_name}), 1),
                EXISTS (SELECT 1 FROM {table_name})
            );
        """
        with connections['default'].cursor() as cursor:
            cursor.execute(sql)
            self.stdout.write(self.style.SUCCESS(f"  └─ Reset sequence for {table_name}.{pk_column}"))