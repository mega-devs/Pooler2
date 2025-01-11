
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()

class Command(BaseCommand):
    help = 'Creates default superuser'

    def handle(self, *args, **options):
        if not User.objects.filter(username='Robert').exists():
            User.objects.create_superuser(
                username='Robert',
                password='Superuser',
            )
            self.stdout.write('Default superuser created')
        else:
            self.stdout.write('Default superuser already exists')
