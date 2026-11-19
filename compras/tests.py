from django.test import TestCase
from django.urls import reverse

from compras.models import Compra, Proveedor
from inventario.models import MovimientoStock
from productos.models import Categoria, Producto
from usuarios.models import Usuario


class CompraTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Categoria.objects.create(nombre='Vinos')
        cls.p1 = Producto.objects.create(categoria=cat, codigo_barras='1', nombre='Tinto', precio=3000, stock=2)
        cls.p2 = Producto.objects.create(categoria=cat, codigo_barras='2', nombre='Blanco', precio=3500, stock=0)
        cls.prov = Proveedor.objects.create(nombre='Viña', contacto='x')
        cls.admin = Usuario.objects.create_user('adm', password='x12345678', rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password='x12345678', rol='trabajador')
        cls.url = reverse('compras:compra_crear')

    def datos(self, **extra):
        d = {
            'proveedor': self.prov.pk, 'fecha': '2026-11-18',
            'detalles-TOTAL_FORMS': 2, 'detalles-INITIAL_FORMS': 0,
            'detalles-MIN_NUM_FORMS': 1, 'detalles-MAX_NUM_FORMS': 1000,
            'detalles-0-producto': self.p1.pk, 'detalles-0-cantidad': 10,
            'detalles-1-producto': self.p2.pk, 'detalles-1-cantidad': 5,
        }
        d.update(extra)
        return d

    def test_trabajador_no_puede_registrar(self):
        self.client.login(username='trab', password='x12345678')
        self.assertEqual(self.client.get(self.url).status_code, 403)
        self.assertEqual(self.client.post(self.url, self.datos()).status_code, 403)
        self.assertEqual(Compra.objects.count(), 0)

    def test_admin_ve_formulario(self):
        self.client.login(username='adm', password='x12345678')
        self.assertEqual(self.client.get(self.url).status_code, 200)

    def test_compra_suma_stock_y_registra_movimientos(self):
        self.client.login(username='adm', password='x12345678')
        r = self.client.post(self.url, self.datos())
        compra = Compra.objects.get()
        self.assertRedirects(r, reverse('compras:compra_detalle', args=[compra.pk]))
        self.p1.refresh_from_db(); self.p2.refresh_from_db()
        self.assertEqual((self.p1.stock, self.p2.stock), (12, 5))
        self.assertEqual(MovimientoStock.objects.filter(tipo='entrada', motivo=f'Compra {compra.pk}').count(), 2)
        self.assertEqual(compra.total_unidades, 15)
        self.assertEqual(compra.registrada_por, self.admin)
        self.assertTrue(all(m.usuario == self.admin for m in MovimientoStock.objects.filter(motivo=f'Compra {compra.pk}')))

    def test_compra_sin_productos_se_rechaza(self):
        self.client.login(username='adm', password='x12345678')
        d = self.datos(**{'detalles-0-producto': '', 'detalles-0-cantidad': '',
                          'detalles-1-producto': '', 'detalles-1-cantidad': ''})
        r = self.client.post(self.url, d)
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Compra.objects.count(), 0)

    def test_cantidad_cero_se_rechaza(self):
        self.client.login(username='adm', password='x12345678')
        r = self.client.post(self.url, self.datos(**{'detalles-0-cantidad': 0}))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Compra.objects.count(), 0)
        self.p1.refresh_from_db()
        self.assertEqual(self.p1.stock, 2)

    def test_historial_lista_la_compra(self):
        self.client.login(username='adm', password='x12345678')
        self.client.post(self.url, self.datos())
        r = self.client.get(reverse('compras:compra_lista'))
        self.assertContains(r, 'Viña')


class ProveedorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('adm2', password='x12345678', rol='admin')
        cls.trab = Usuario.objects.create_user('trab2', password='x12345678', rol='trabajador')

    def test_trabajador_no_accede(self):
        self.client.login(username='trab2', password='x12345678')
        self.assertEqual(self.client.get(reverse('compras:proveedor_lista')).status_code, 403)

    def test_anonimo_va_al_login(self):
        self.assertEqual(self.client.get(reverse('compras:proveedor_lista')).status_code, 302)

    def test_crear_editar_buscar_y_eliminar(self):
        self.client.login(username='adm2', password='x12345678')
        self.client.post(reverse('compras:proveedor_crear'), {'nombre': 'Viña Sur', 'contacto': '+56911111111'})
        p = Proveedor.objects.get()
        self.client.post(reverse('compras:proveedor_editar', args=[p.pk]), {'nombre': 'Viña Norte', 'contacto': 'x'})
        p.refresh_from_db()
        self.assertEqual(p.nombre, 'Viña Norte')
        r = self.client.get(reverse('compras:proveedor_lista'), {'q': 'Norte'})
        self.assertContains(r, 'Viña Norte')
        self.client.post(reverse('compras:proveedor_eliminar', args=[p.pk]))
        self.assertEqual(Proveedor.objects.count(), 0)

    def test_no_elimina_proveedor_con_compras(self):
        self.client.login(username='adm2', password='x12345678')
        p = Proveedor.objects.create(nombre='A', contacto='b')
        Compra.objects.create(proveedor=p)
        self.client.post(reverse('compras:proveedor_eliminar', args=[p.pk]))
        self.assertTrue(Proveedor.objects.filter(pk=p.pk).exists())
