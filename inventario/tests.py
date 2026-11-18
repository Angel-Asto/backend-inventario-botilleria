from django.test import TestCase
from django.urls import reverse

from productos.models import Categoria, Producto
from usuarios.models import Usuario

from .models import MovimientoStock
from .servicios import registrar_movimiento


class BaseInventario(TestCase):
    @classmethod
    def setUpTestData(cls):
        cat = Categoria.objects.create(nombre='Cervezas')
        cls.p = Producto.objects.create(categoria=cat, codigo_barras='111', nombre='Cristal', precio=1000, stock=5, stock_minimo=10)
        cls.ok = Producto.objects.create(categoria=cat, codigo_barras='222', nombre='Escudo', precio=1000, stock=50, stock_minimo=10)
        cls.admin = Usuario.objects.create_user('adm', password='x12345678', rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password='x12345678', rol='trabajador')


class ServicioStockTests(BaseInventario):
    def test_entrada_suma_stock_y_deja_movimiento(self):
        registrar_movimiento(self.p, MovimientoStock.Tipo.ENTRADA, 10, 'Compra 1')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 15)
        self.assertEqual(MovimientoStock.objects.filter(producto=self.p, tipo='entrada').count(), 1)

    def test_salida_resta_stock(self):
        registrar_movimiento(self.p, MovimientoStock.Tipo.SALIDA, 3, 'Venta 1')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 2)

    def test_salida_sin_stock_suficiente_falla_y_no_cambia_nada(self):
        with self.assertRaises(ValueError):
            registrar_movimiento(self.p, MovimientoStock.Tipo.SALIDA, 6, 'Venta 1')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 5)
        self.assertEqual(MovimientoStock.objects.count(), 0)


class VistasInventarioTests(BaseInventario):
    def test_stock_requiere_login(self):
        r = self.client.get(reverse('inventario:stock'))
        self.assertEqual(r.status_code, 302)

    def test_trabajador_ve_stock_con_alerta(self):
        self.client.login(username='trab', password='x12345678')
        r = self.client.get(reverse('inventario:stock'))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'Alerta de stock bajo')
        self.assertEqual(r.context['cantidad_bajo'], 1)

    def test_filtro_solo_bajo(self):
        self.client.login(username='trab', password='x12345678')
        r = self.client.get(reverse('inventario:stock'), {'solo_bajo': 1})
        self.assertEqual(list(r.context['object_list']), [self.p])

    def test_historial_es_solo_admin(self):
        self.client.login(username='trab', password='x12345678')
        self.assertEqual(self.client.get(reverse('inventario:movimientos')).status_code, 403)
        self.client.login(username='adm', password='x12345678')
        self.assertEqual(self.client.get(reverse('inventario:movimientos')).status_code, 200)

    def test_historial_filtra_por_tipo(self):
        registrar_movimiento(self.p, 'entrada', 1, 'a')
        registrar_movimiento(self.p, 'salida', 1, 'b')
        self.client.login(username='adm', password='x12345678')
        r = self.client.get(reverse('inventario:movimientos'), {'tipo': 'salida'})
        self.assertEqual([m.tipo for m in r.context['object_list']], ['salida'])
