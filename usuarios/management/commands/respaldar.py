"""Respaldo de todos los datos en un archivo JSON (sirve con SQLite y con PostgreSQL).

    python manage.py respaldar                       # crea respaldos/respaldo_AAAAMMDD_HHMMSS.json
    python manage.py loaddata respaldos/<archivo>    # restaura sobre una base ya migrada

El archivo incluye los hashes de las contraseñas: guárdalo en un lugar seguro (la carpeta respaldos/ no se sube a git).
"""
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

EXCLUIR = ['contenttypes', 'auth.permission', 'sessions', 'admin.logentry']


class Command(BaseCommand):
    help = 'Guarda un respaldo de los datos en respaldos/ (restaurar con loaddata).'

    def add_arguments(self, parser):
        parser.add_argument('--carpeta', default=str(Path(settings.BASE_DIR) / 'respaldos'),
                            help='Carpeta donde se guarda el respaldo.')

    def handle(self, *args, **opciones):
        carpeta = Path(opciones['carpeta'])
        carpeta.mkdir(parents=True, exist_ok=True)
        archivo = carpeta / f"respaldo_{timezone.localtime():%Y%m%d_%H%M%S}.json"
        call_command('dumpdata', natural_foreign=True, exclude=EXCLUIR, indent=2, output=str(archivo), verbosity=0)
        self.stdout.write(self.style.SUCCESS(f'Respaldo guardado en {archivo} ({archivo.stat().st_size // 1024} KB).'))
        self.stdout.write(f'Para restaurar: python manage.py loaddata "{archivo}"')
