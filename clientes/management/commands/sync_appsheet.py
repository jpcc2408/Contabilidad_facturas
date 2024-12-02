from django.core.management.base import BaseCommand
from clientes.utils import sync_appsheet_data

class Command(BaseCommand):
    help = 'Sincroniza datos desde AppSheet'

    def handle(self, *args, **options):
        if sync_appsheet_data():
            self.stdout.write(self.style.SUCCESS('Sincronización exitosa'))
        else:
            self.stdout.write(self.style.ERROR('Error en la sincronización'))