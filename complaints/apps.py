from django.apps import AppConfig
import sys

class ComplaintsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'complaints'

    def ready(self):
        # This forces migrations to run on startup when deployed
        if 'runserver' in sys.argv or 'gunicorn' in sys.argv or 'wsgi' in sys.argv:
            from django.core.management import call_command
            try:
                call_command('migrate', interactive=False)
            except Exception as e:
                print(f"Migration failed on startup: {e}")