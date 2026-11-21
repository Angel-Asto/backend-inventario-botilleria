"""Las ventas creadas antes de existir creada_en recibieron la hora de la migración.

Se les asigna su fecha real a las 00:00 (hora local), para no mostrar una hora inventada.
"""
from datetime import datetime, time

from django.db import migrations
from django.utils import timezone


def corregir(apps, schema_editor):
    Venta = apps.get_model('ventas', 'Venta')
    for v in Venta.objects.all().only('pk', 'fecha', 'creada_en'):
        if timezone.localtime(v.creada_en).date() != v.fecha:
            v.creada_en = timezone.make_aware(datetime.combine(v.fecha, time.min))
            v.save(update_fields=['creada_en'])


class Migration(migrations.Migration):

    dependencies = [
        ('ventas', '0005_indices'),
    ]

    operations = [
        migrations.RunPython(corregir, migrations.RunPython.noop),
    ]
