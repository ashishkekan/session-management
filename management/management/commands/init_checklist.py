# management/management/commands/init_checklist.py
from django.core.management.base import BaseCommand
from management.models import SetupChecklist

class Command(BaseCommand):
    help = 'Initialize setup checklist'

    def handle(self, *args, **kwargs):
        tasks = [
            'Set company logo and name',
            'Add first admin user',
            'Create first session',
            'Add first department',
        ]
        for task in tasks:
            SetupChecklist.objects.get_or_create(task=task)
        self.stdout.write(self.style.SUCCESS('Checklist initialized'))
