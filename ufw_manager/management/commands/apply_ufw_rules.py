from django.core.management.base import BaseCommand
from ufw_manager.models import UFWRule
import subprocess

class Command(BaseCommand):
    help = 'Applies UFW rules from the database'

    def handle(self, *args, **options):
        subprocess.run(['ufw', 'disable'], check=True)
        subprocess.run(['ufw', 'reset'], check=True)
        for rule in UFWRule.objects.all():
            command = ['ufw', 'allow']
            if rule.direction == 'in':
                command.append('in')
            elif rule.direction == 'out':
                command.append('out')
            if rule.protocol != 'any':
                command.append(rule.protocol)
            if rule.port:
                command.append(str(rule.port))
            if rule.from_ip:
                command.append('from')
                command.append(rule.from_ip)
            if rule.to_ip:
                command.append('to')
                command.append(rule.to_ip)
            if rule.action == 'deny':
                command[1] = 'deny'
            try:
                subprocess.run(command, check=True)
                self.stdout.write(self.style.SUCCESS(f'Successfully applied rule: {rule}'))
            except subprocess.CalledProcessError as e:
                self.stderr.write(self.style.ERROR(f'Error applying rule: {rule} - {e}'))
        subprocess.run(['ufw', 'enable'], check=True)
        self.stdout.write(self.style.SUCCESS('UFW rules applied successfully.'))
