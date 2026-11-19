from django.test import TestCase
from django.urls import reverse

from usuarios.models import Usuario

from .models import Categoria, Producto

CLAVE = 'Clave-segura-123'


class ProductoTests(TestCase):
    def setUp(self):
        self.admin = Usuario.objects.create_user('admin1', password=CLAVE, rol='admin')
        self.trab = Usuario.objects.create_user('trab1', password=CLAVE, rol='trabajador')
        self.cat = Categoria.objects.create(nombre='Cervezas')
        self.prod = Producto.objects.create(
            categoria=self.cat, codigo_barras='7802', nombre='Cerveza Cristal 470cc',
            precio=1490, stock=48, stock_minimo=12,
        )

    def datos(self, **extra):
        d = {'categoria': self.cat.pk, 'codigo_barras': '9999', 'nombre': 'Cerveza Escudo',
                'precio': 1590, 'stock': 10, 'stock_minimo': 5}
        d.update(extra)
        return d

    def test_trabajador_puede_ver_pero_no_crear(self):
        self.client.login(username='trab1', password=CLAVE)
        self.assertEqual(self.client.get(reverse('productos:lista')).status_code, 200)
        self.assertEqual(self.client.get(reverse('productos:crear')).status_code, 403)

    def test_formulario_producto_ofrece_escaner_con_camara(self):
        self.client.login(username='admin1', password=CLAVE)
        r = self.client.get(reverse('productos:crear'))
        self.assertContains(r, 'html5-qrcode@2.3.8')
        self.assertContains(r, 'EscanerCamara.conectar')
        # El formulario de categoría usa la misma plantilla pero no tiene código de barras.
        self.assertNotContains(self.client.get(reverse('productos:categoria_crear')), 'html5-qrcode')

    def test_admin_crea_producto(self):
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:crear'), self.datos())
        self.assertTrue(Producto.objects.filter(codigo_barras='9999').exists())

    def test_stock_inicial_queda_como_movimiento(self):
        from inventario.models import MovimientoStock
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:crear'), self.datos(stock=10))
        p = Producto.objects.get(codigo_barras='9999')
        self.assertEqual(p.stock, 10)
        m = MovimientoStock.objects.get(producto=p)
        self.assertEqual((m.tipo, m.cantidad, m.motivo), ('entrada', 10, 'Stock inicial'))

    def test_producto_sin_stock_inicial_no_deja_movimiento(self):
        from inventario.models import MovimientoStock
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:crear'), self.datos(stock=0))
        self.assertFalse(MovimientoStock.objects.exists())

    def test_codigo_de_barras_no_se_repite(self):
        self.client.login(username='admin1', password=CLAVE)
        r = self.client.post(reverse('productos:crear'), self.datos(codigo_barras='7802'))
        self.assertContains(r, 'Ya existe un producto con ese código')
        self.assertEqual(Producto.objects.count(), 1)

    def test_precio_debe_ser_mayor_a_cero(self):
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:crear'), self.datos(precio=0))
        self.assertEqual(Producto.objects.count(), 1)

    def test_busqueda_por_codigo_y_por_nombre(self):
        self.client.login(username='admin1', password=CLAVE)
        r = self.client.get(reverse('productos:lista'), {'q': '7802'})
        self.assertContains(r, 'Cerveza Cristal')
        r = self.client.get(reverse('productos:lista'), {'q': 'inexistente'})
        self.assertNotContains(r, 'Cerveza Cristal')

    def test_baja_no_borra_el_producto(self):
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:baja', args=[self.prod.pk]))
        self.prod.refresh_from_db()
        self.assertFalse(self.prod.activo)

    def test_editar_no_cambia_el_stock(self):
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:editar', args=[self.prod.pk]),
        self.datos(codigo_barras='7802', nombre='Cristal 470', stock=1))
        self.prod.refresh_from_db()
        self.assertEqual(self.prod.stock, 48)

    def test_no_se_elimina_categoria_con_productos(self):
        self.client.login(username='admin1', password=CLAVE)
        self.client.post(reverse('productos:categoria_eliminar', args=[self.cat.pk]))
        self.assertTrue(Categoria.objects.filter(pk=self.cat.pk).exists())

class ReglasEnBaseDeDatosTests(TestCase):
    """Las reglas se cumplen aunque los datos no vengan del formulario (admin, scripts, fixtures)."""

    def test_precio_cero_y_cantidades_cero_se_rechazan_en_la_bd(self):
        from django.db import IntegrityError, transaction
        from inventario.models import MovimientoStock
        cat = Categoria.objects.create(nombre='X')
        with self.assertRaises(IntegrityError), transaction.atomic():
            Producto.objects.create(categoria=cat, codigo_barras='0', nombre='Gratis', precio=0)
        p = Producto.objects.create(categoria=cat, codigo_barras='1', nombre='Uno', precio=100)
        with self.assertRaises(IntegrityError), transaction.atomic():
            MovimientoStock.objects.create(producto=p, tipo='entrada', cantidad=0, motivo='x')


class FormatoPesosTests(TestCase):
    def test_formato_chileno(self):
        from productos.templatetags.formato import pesos
        self.assertEqual(pesos(1990), '$1.990')
        self.assertEqual(pesos(1234567), '$1.234.567')
        self.assertEqual(pesos(0), '$0')
        self.assertEqual(pesos('texto'), 'texto')
