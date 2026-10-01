import os
from urllib.parse import quote
import psycopg2
from django.core.management.base import BaseCommand
from django.apps import apps

class Command(BaseCommand):
    help = "Safely copies production data from Neon to your local PostgreSQL instance using direct psycopg2 streams."

    def handle(self, *args, **options):
        # 1. Define target application models to clone
        MODELS_TO_SYNC = [
            'branch.Branch',
            'authentication.User',
            'attendance.Attendance',
            'class_session.Class_Session',
        ]
        db_tables = [apps.get_model(m)._meta.db_table for m in MODELS_TO_SYNC]

        # 2. Extract production source connection configuration
        prod_url = os.environ.get('PRODUCTION_DATABASE_URL')
        if not prod_url:
            self.stderr.write(self.style.ERROR(
                "CRITICAL ERROR: PRODUCTION_DATABASE_URL not found in your environment variables.\n"
                "Please verify your .env settings configuration."
            ))
            return

        # 3. Parse local database fallback credentials explicitly from settings configurations
        local_db_name = os.environ.get('DB_NAME', 'area_academy_db')
        password = quote(os.environ.get('DB_PASSWORD', 'anonymousmrbeast@404'))
        
        # Build an explicit local connection URI bypassing the active env variables
        local_url = f"postgres://postgres:{password}@localhost:5432/{local_db_name}"

        self.stdout.write("Initializing target connections using raw psycopg2 protocols...")

        try:
            # 4. Connect to both databases concurrently
            # Open production as read-only source and local as target destination
            with psycopg2.connect(prod_url) as prod_conn, psycopg2.connect(local_url) as local_conn:
                
                with prod_conn.cursor() as prod_cursor, local_conn.cursor() as local_cursor:
                    
                    # 5. Flush local records safely and reset incremental tracking IDs
                    self.stdout.write(self.style.WARNING("Clearing target tables on local instance..."))
                    tables_str = ", ".join([f'"{t}"' for t in db_tables])
                    local_cursor.execute(f"TRUNCATE TABLE {tables_str} RESTART IDENTITY CASCADE;")

                    # 6. Stream rows across the database connection pipeline
                    for table in db_tables:
                        self.stdout.write(f"Streaming data records for: {table}...")

                        # Fetch from Neon
                        prod_cursor.execute(f'SELECT * FROM "{table}";')
                        rows = prod_cursor.fetchall()

                        if not rows:
                            self.stdout.write(f"↳ Table {table} is currently empty in production. Skipping.")
                            continue

                        # Read field arrays metadata to build valid insert formatting layouts
                        colnames = [desc[0] for desc in prod_cursor.description]
                        cols_str = ", ".join([f'"{c}"' for c in colnames])
                        placeholders = ", ".join(["%s"] * len(colnames))

                        insert_query = f'INSERT INTO "{table}" ({cols_str}) VALUES ({placeholders});'

                        # Execute raw bulk insert statements on local engine sandbox
                        local_cursor.executemany(insert_query, rows)
                        self.stdout.write(self.style.SUCCESS(f"↳ Copied {len(rows)} operational rows successfully."))

                # Commit entries to write to your local disk storage setup
                local_conn.commit()
                self.stdout.write(self.style.SUCCESS("\n[SUCCESS] Production clone completely processed!"))

        except Exception as e:
            self.stderr.write(self.style.ERROR(f"\n[CRITICAL FAILURE] Pipeline execution failed: {e}"))
