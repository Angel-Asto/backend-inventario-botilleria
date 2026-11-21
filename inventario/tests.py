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

    def test_salida_de_todo_el_stock_justo_se_permite(self):
        registrar_movimiento(self.p, MovimientoStock.Tipo.SALIDA, 5, 'Venta 1')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 0)

    def test_tipo_invalido_se_rechaza_y_no_suma_stock(self):
        for tipo in ('SALIDA', 'Salida', 'ajuste', ''):
            with self.assertRaises(ValueError):
                registrar_movimiento(self.p, tipo, 3, 'x')
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 5)
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_cantidad_cero_negativa_o_no_entera_se_rechaza(self):
        for cantidad in (0, -2, 1.5, '3', True):
            with self.assertRaises(ValueError):
                registrar_movimiento(self.p, MovimientoStock.Tipo.ENTRADA, cantidad, 'x')
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_motivo_vacio_se_rechaza(self):
        with self.assertRaises(ValueError):
            registrar_movimiento(self.p, MovimientoStock.Tipo.ENTRADA, 1, '  ')


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


class AdminDjangoSoloLecturaTests(BaseInventario):
    """En el admin de Django los historiales se ven pero no se editan (el stock no se desincroniza)."""

    def setUp(self):
        self.su = Usuario.objects.create_superuser('root', password='x12345678')
        self.client.force_login(self.su)

    def test_no_se_crean_ni_borran_movimientos_compras_ni_ventas(self):
        for modelo in ('inventario/movimientostock', 'compras/compra', 'ventas/venta'):
            self.assertEqual(self.client.get(f'/admin/{modelo}/add/').status_code, 403, modelo)
            self.assertEqual(self.client.get(f'/admin/{modelo}/').status_code, 200, modelo)

    def test_stock_del_producto_es_solo_lectura(self):
        r = self.client.post(f'/admin/productos/producto/{self.p.pk}/change/', {
            'categoria': self.p.categoria_id, 'codigo_barras': '111', 'nombre': 'Cristal',
            'precio': 1000, 'stock': 999, 'stock_minimo': 10, 'activo': 'on'})
        self.assertEqual(r.status_code, 302)
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 5)


class AjusteStockTests(BaseInventario):
    url = '/inventario/ajuste/'

    def test_solo_admin(self):
        self.client.login(username='trab', password='x12345678')
        self.assertEqual(self.client.get(self.url).status_code, 403)

    def test_merma_resta_stock_y_queda_en_el_historial(self):
        self.client.login(username='adm', password='x12345678')
        r = self.client.post(self.url, {'producto': self.p.pk, 'tipo': 'salida', 'cantidad': 2, 'motivo': 'Botella rota'})
        self.assertRedirects(r, reverse('inventario:movimientos'))
        self.p.refresh_from_db()
        self.assertEqual(self.p.stock, 3)
        m = MovimientoStock.objects.get()
        self.assertEqual((m.motivo, m.usuario), ('Ajuste: Botella rota', self.admin))

    def test_no_deja_stock_negativo_ni_acepta_motivo_corto(self):
        self.client.login(username='adm', password='x12345678')
        r = self.client.post(self.url, {'producto': self.p.pk, 'tipo': 'salida', 'cantidad': 6, 'motivo': 'Conteo físico'})
        self.assertContains(r, 'Stock insuficiente')
        self.client.post(self.url, {'producto': self.p.pk, 'tipo': 'entrada', 'cantidad': 1, 'motivo': 'x'})
        self.assertEqual(MovimientoStock.objects.count(), 0)
