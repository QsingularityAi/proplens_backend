from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = 'Create a superuser for testing'

    def handle(self, *args, **options):
        username = 'admin'
        email = 'admin@proplens.ai'
        password = 'admin123'
        
        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f'User {username} already exists'))
        else:
            User.objects.create_superuser(username=username, email=email, password=password)
            self.stdout.write(self.style.SUCCESS(f'Created superuser: {username} / {password}'))



