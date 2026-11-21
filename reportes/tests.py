from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from productos.models import Categoria, Producto
from usuarios.models import Usuario
from ventas.models import DetalleVenta, Venta

CLAVE = 'Clave-segura-123'


class ReportesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('adm', password=CLAVE, rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')
        cat = Categoria.objects.create(nombre='Bebidas')
        cls.cola = Producto.objects.create(categoria=cat, codigo_barras='1', nombre='Cola', precio=1000, stock=50)
        cls.agua = Producto.objects.create(categoria=cat, codigo_barras='2', nombre='Agua', precio=500, stock=50)
        cls.raro = Producto.objects.create(categoria=cat, codigo_barras='3', nombre='=HYPERLINK("x")', precio=100, stock=5)
        hoy = timezone.localdate()
        cls.hoy = hoy

        def venta(cantidad, producto, estado='completada', fecha=hoy, medio='efectivo'):
            v = Venta.objects.create(usuario=cls.trab, medio_pago=medio, total=cantidad * producto.precio,
                                     estado=estado, fecha=fecha)
            DetalleVenta.objects.create(venta=v, producto=producto, cantidad=cantidad, precio_unitario=producto.precio)

        venta(3, cls.cola)
        venta(1, cls.agua, medio='tarjeta')
        venta(5, cls.agua, estado='anulada')                    # no cuenta
        venta(9, cls.cola, fecha=hoy - timedelta(days=30))      # fuera del período

    def test_solo_admin(self):
        self.client.login(username='trab', password=CLAVE)
        for nombre in ('ventas', 'ventas_csv', 'productos_csv'):
            self.assertEqual(self.client.get(reverse(f'reportes:{nombre}')).status_code, 403)

    def test_totales_del_periodo_sin_anuladas(self):
        self.client.login(username='adm', password=CLAVE)
        r = self.client.get(reverse('reportes:ventas'))
        self.assertEqual((r.context['total'], r.context['cantidad'], r.context['anuladas']), (3500, 2, 1))
        self.assertEqual(len(r.context['dias']), 7)
        self.assertEqual([p.nombre for p in r.context['mas_vendidos']], ['Cola', 'Agua'])
        self.assertEqual(r.context['mas_vendidos'][0].unidades, 3)
        self.assertEqual(r.context['menos_vendidos'][0].unidades, 0)  # incluye productos sin ventas

    def test_fechas_invalidas_o_invertidas_no_rompen(self):
        self.client.login(username='adm', password=CLAVE)
        r = self.client.get(reverse('reportes:ventas'), {'desde': 'abc', 'hasta': '2026-99-99'})
        self.assertEqual(r.status_code, 200)
        r = self.client.get(reverse('reportes:ventas'), {'desde': self.hoy.isoformat(),
                                                         'hasta': (self.hoy - timedelta(days=40)).isoformat()})
        self.assertEqual(r.context['total'], 3500 + 9000)

    def test_csv_de_ventas_y_productos(self):
        self.client.login(username='adm', password=CLAVE)
        r = self.client.get(reverse('reportes:ventas_csv'))
        self.assertEqual(r['Content-Type'], 'text/csv; charset=utf-8')
        contenido = r.content.decode('utf-8-sig')
        self.assertIn('N°;Fecha y hora;Vendedor', contenido)
        self.assertEqual(contenido.count('\n'), 4)  # encabezado + 3 ventas del período (incluye la anulada)
        r = self.client.get(reverse('reportes:productos_csv'))
        self.assertIn('1;Cola;Bebidas;3;3000;50', r.content.decode('utf-8-sig'))

    def test_csv_neutraliza_formulas(self):
        self.client.login(username='adm', password=CLAVE)
        contenido = self.client.get(reverse('reportes:productos_csv')).content.decode('utf-8-sig')
        import csv
        import io
        celdas = [c for fila in csv.reader(io.StringIO(contenido), delimiter=';') for c in fila]
        self.assertIn("'=HYPERLINK(\"x\")", celdas)  # se guarda como texto, no como fórmula
        self.assertFalse(any(c.startswith('=') for c in celdas))
