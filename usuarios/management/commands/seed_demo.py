"""Datos de demostración compartidos por el equipo.

    python manage.py seed_demo                  # usuarios, catálogo, stock, proveedores, una compra y una venta
    python manage.py seed_demo --solo-catalogo  # sin la compra ni la venta de ejemplo

Es idempotente: se puede correr varias veces sin duplicar nada. Solo funciona con DEBUG=True.
Las contraseñas se leen de DEMO_ADMIN_PASSWORD y DEMO_WORKER_PASSWORD (archivo .env).
"""
import json
import os
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from compras.models import Compra, DetalleCompra, Proveedor
from inventario.models import MovimientoStock
from inventario.servicios import registrar_movimiento
from productos.models import Categoria, Producto
from usuarios.models import Usuario
from ventas.models import Venta
from ventas.servicios import registrar_venta

CATALOGO = Path(settings.BASE_DIR) / 'productos' / 'fixtures' / 'catalogo.json'
MOTIVO_STOCK_INICIAL = 'Stock inicial (demo)'

# Solo para desarrollo (DEBUG=True) si el .env no define las contraseñas. Nunca se imprimen.
_CLAVES_POR_DEFECTO = {'DEMO_ADMIN_PASSWORD': 'Demo-Admin-2026', 'DEMO_WORKER_PASSWORD': 'Demo-Caja-2026'}

USUARIOS = [  # (username, nombre, apellido, rol, variable de entorno)
    ('admin_demo', 'Ana', 'Administradora', Usuario.Rol.ADMIN, 'DEMO_ADMIN_PASSWORD'),
    ('trabajador_demo', 'Tomás', 'Cajero', Usuario.Rol.TRABAJADOR, 'DEMO_WORKER_PASSWORD'),
]
PROVEEDORES = [('Distribuidora Central', '+56 9 1111 2222'), ('Viña del Valle', 'ventas@vinadelvalle.example')]
# Stock con el que parte cada producto (código de barras -> unidades); algunos quedan bajo el mínimo a propósito.
STOCK_INICIAL = {
    '7800000000016': 48, '7800000000023': 24, '7800000000030': 5, '7800000000047': 12, '7800000000054': 10,
    '7800000000061': 6, '7800000000078': 2, '7800000000085': 30, '7800000000092': 4, '7800000000108': 15,
    '7800000000115': 20, '7800000000122': 18,
}


class Command(BaseCommand):
    help = 'Crea o actualiza los datos de demostración (idempotente, solo con DEBUG=True).'

    def add_arguments(self, parser):
        parser.add_argument('--solo-catalogo', action='store_true', help='No crea la compra ni la venta de ejemplo.')

    def handle(self, *args, **opciones):
        if not settings.DEBUG:
            raise CommandError('seed_demo solo se ejecuta con DEBUG=True (nunca en producción).')
        with transaction.atomic():
            usuarios = self._usuarios()
            productos = self._catalogo(usuarios['admin_demo'])
            proveedores = self._proveedores()
            if not opciones['solo_catalogo']:
                self._compra_y_venta(usuarios, productos, proveedores)
        self.stdout.write(self.style.SUCCESS(
            f'Listo: {Usuario.objects.filter(username__in=[u[0] for u in USUARIOS]).count()} usuarios de demo, '
            f'{Categoria.objects.count()} categorías, {Producto.objects.count()} productos, '
            f'{Proveedor.objects.count()} proveedores, {Compra.objects.count()} compras, {Venta.objects.count()} ventas.'))

    def _usuarios(self):
        usuarios = {}
        for username, nombre, apellido, rol, variable in USUARIOS:
            clave = os.environ.get(variable)
            if not clave:
                clave = _CLAVES_POR_DEFECTO[variable]
                self.stdout.write(self.style.WARNING(
                    f'{variable} no está en el .env: {username} usa la contraseña por defecto de desarrollo.'))
            u, creado = Usuario.objects.update_or_create(
                username=username, defaults={'first_name': nombre, 'last_name': apellido, 'rol': rol, 'is_active': True})
            u.set_password(clave)
            u.save(update_fields=['password'])
            usuarios[username] = u
            self.stdout.write(f'{"Creado" if creado else "Actualizado"} usuario {username} ({u.get_rol_display()}).')
        return usuarios

    def _catalogo(self, admin):
        datos = json.loads(CATALOGO.read_text(encoding='utf-8'))
        for d in (x['fields'] for x in datos if x['model'] == 'productos.categoria'):
            Categoria.objects.update_or_create(nombre=d['nombre'], defaults={'es_alcoholica': d['es_alcoholica']})
        productos = {}
        for d in (x['fields'] for x in datos if x['model'] == 'productos.producto'):
            p, _ = Producto.objects.update_or_create(codigo_barras=d['codigo_barras'], defaults={
                'categoria': Categoria.objects.get(nombre=d['categoria'][0]), 'nombre': d['nombre'],
                'precio': d['precio'], 'stock_minimo': d['stock_minimo'], 'activo': True})
            inicial = STOCK_INICIAL.get(p.codigo_barras, 0)
            ya_cargado = MovimientoStock.objects.filter(producto=p, motivo=MOTIVO_STOCK_INICIAL).exists()
            if inicial and not ya_cargado:  # el stock entra como movimiento, una sola vez
                registrar_movimiento(p, MovimientoStock.Tipo.ENTRADA, inicial, MOTIVO_STOCK_INICIAL, admin)
            productos[p.codigo_barras] = p
        self.stdout.write(f'Catálogo: {len(productos)} productos con su stock inicial.')
        return productos

    def _proveedores(self):
        return [Proveedor.objects.update_or_create(nombre=n, defaults={'contacto': c})[0] for n, c in PROVEEDORES]

    def _compra_y_venta(self, usuarios, productos, proveedores):
        admin, cajero = usuarios['admin_demo'], usuarios['trabajador_demo']
        if not Compra.objects.filter(proveedor=proveedores[0], registrada_por=admin).exists():
            compra = Compra.objects.create(proveedor=proveedores[0], registrada_por=admin)
            for codigo, cantidad in (('7800000000016', 24), ('7800000000085', 12)):
                DetalleCompra.objects.create(compra=compra, producto=productos[codigo], cantidad=cantidad)
                registrar_movimiento(productos[codigo], MovimientoStock.Tipo.ENTRADA, cantidad, f'Compra {compra.pk}', admin)
            self.stdout.write(f'Creada compra de ejemplo N° {compra.pk}.')
        if not Venta.objects.filter(usuario=cajero).exists():
            venta = registrar_venta(cajero, {'7800000000016': 2, '7800000000115': 1}, Venta.MedioPago.EFECTIVO,
                                    mayor_edad=True)
            self.stdout.write(f'Creada venta de ejemplo N° {venta.pk} (total ${venta.total:,}).'.replace(',', '.'))
