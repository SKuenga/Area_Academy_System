from django.db import migrations


def remove_legacy_phone_number(apps, schema_editor):
    user_model = apps.get_model("authentication", "User")
    table_name = user_model._meta.db_table

    with schema_editor.connection.cursor() as cursor:
        columns = schema_editor.connection.introspection.get_table_description(
            cursor, table_name
        )

    if any(column.name == "phone_number" for column in columns):
        schema_editor.execute(
            f"ALTER TABLE {schema_editor.quote_name(table_name)} "
            f"DROP COLUMN {schema_editor.quote_name('phone_number')}"
        )


class Migration(migrations.Migration):
    dependencies = [
        ("authentication", "0004_alter_user_branch"),
    ]

    operations = [
        migrations.RunPython(
            remove_legacy_phone_number,
            migrations.RunPython.noop,
            hints={"model_name": "user"},
        ),
    ]
