from django.test import TestCase
from django.urls import reverse

from inventario.models import MovimientoStock
from productos.models import Categoria, Producto
from usuarios.models import Usuario

from .models import Venta


class VentaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cerv = Categoria.objects.create(nombre='Cervezas', es_alcoholica=True)
        beb = Categoria.objects.create(nombre='Bebidas')
        cls.cerveza = Producto.objects.create(categoria=cerv, codigo_barras='111', nombre='Cristal', precio=1000, stock=10)
        cls.cola = Producto.objects.create(categoria=beb, codigo_barras='222', nombre='Cola', precio=1500, stock=3)
        cls.baja = Producto.objects.create(categoria=beb, codigo_barras='333', nombre='Vieja', precio=500, stock=5, activo=False)
        cls.admin = Usuario.objects.create_user('adm', password='x12345678', rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password='x12345678', rol='trabajador')
        cls.otro = Usuario.objects.create_user('otro', password='x12345678', rol='trabajador')
        cls.url = reverse('ventas:caja')

    def vender(self, codigos, cantidades, **extra):
        d = {'codigo': codigos, 'cantidad': cantidades, 'medio_pago': 'efectivo'}
        d.update(extra)
        return self.client.post(self.url, d)

    # --- acceso
    def test_caja_requiere_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_caja_ofrece_escaner_con_camara(self):
        self.client.login(username='trab', password='x12345678')
        r = self.client.get(self.url)
        self.assertContains(r, 'id="btn-camara"')
        self.assertContains(r, 'html5-qrcode@2.3.8')

    # --- buscador por código
    def test_buscar_producto_por_codigo(self):
        self.client.login(username='trab', password='x12345678')
        r = self.client.get(reverse('ventas:buscar'), {'codigo': '111'})
        self.assertEqual(r.json()['nombre'], 'Cristal')
        self.assertTrue(r.json()['alcohol'])

    def test_buscar_producto_inexistente_o_de_baja_da_404(self):
        self.client.login(username='trab', password='x12345678')
        self.assertEqual(self.client.get(reverse('ventas:buscar'), {'codigo': '999'}).status_code, 404)
        self.assertEqual(self.client.get(reverse('ventas:buscar'), {'codigo': '333'}).status_code, 404)

    # --- venta
    def test_venta_descuenta_stock_calcula_total_y_registra_movimiento(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender(['222', '111'], ['2', '3'], mayor_edad='on')
        v = Venta.objects.get()
        self.assertRedirects(r, reverse('ventas:detalle', args=[v.pk]))
        self.assertEqual(v.total, 2 * 1500 + 3 * 1000)
        self.assertEqual(v.usuario, self.trab)
        self.cola.refresh_from_db(); self.cerveza.refresh_from_db()
        self.assertEqual((self.cola.stock, self.cerveza.stock), (1, 7))
        self.assertEqual(MovimientoStock.objects.filter(tipo='salida', motivo=f'Venta {v.pk}').count(), 2)

    def test_precio_se_guarda_en_el_detalle(self):
        self.client.login(username='trab', password='x12345678')
        self.vender(['222'], ['1'])
        self.cola.precio = 9999; self.cola.save()
        d = Venta.objects.get().detalles.get()
        self.assertEqual(d.precio_unitario, 1500)

    def test_venta_vacia_se_rechaza(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender([], [])
        self.assertEqual(r.status_code, 200)
        self.assertEqual(Venta.objects.count(), 0)

    def test_alcohol_exige_confirmar_mayoria_de_edad(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender(['111'], ['1'])
        self.assertContains(r, 'mayor de 18')
        self.assertEqual(Venta.objects.count(), 0)
        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.stock, 10)

    def test_sin_alcohol_no_pide_confirmacion(self):
        self.client.login(username='trab', password='x12345678')
        self.vender(['222'], ['1'])
        self.assertEqual(Venta.objects.count(), 1)

    def test_stock_insuficiente_no_deja_nada_a_medias(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender(['111', '222'], ['1', '4'], mayor_edad='on')  # cola solo tiene 3
        self.assertContains(r, 'Stock insuficiente')
        self.assertEqual(Venta.objects.count(), 0)
        self.cerveza.refresh_from_db()
        self.assertEqual(self.cerveza.stock, 10)
        self.assertEqual(MovimientoStock.objects.count(), 0)

    def test_medio_de_pago_invalido(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender(['222'], ['1'], medio_pago='cheque')
        self.assertEqual(Venta.objects.count(), 0)
        self.assertContains(r, 'medio de pago')

    def test_producto_de_baja_no_se_puede_vender(self):
        self.client.login(username='trab', password='x12345678')
        self.vender(['333'], ['1'])
        self.assertEqual(Venta.objects.count(), 0)

    def test_cantidad_invalida_se_ignora(self):
        self.client.login(username='trab', password='x12345678')
        self.vender(['222'], ['-5'])
        self.assertEqual(Venta.objects.count(), 0)

    def test_cantidades_raras_no_provocan_error_500(self):
        self.client.login(username='trab', password='x12345678')
        for cantidad in ('9' * 25, '1.5', '²', 'abc', ''):
            r = self.vender(['222'], [cantidad])
            self.assertEqual(r.status_code, 200, cantidad)
        self.assertEqual(Venta.objects.count(), 0)

    def test_cantidad_sobre_el_maximo_se_rechaza(self):
        self.client.login(username='trab', password='x12345678')
        r = self.vender(['222'], ['1000'])
        self.assertContains(r, 'La cantidad máxima por producto es 999')
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock, 3)

    # --- anular
    def crear_venta(self):
        self.client.login(username='trab', password='x12345678')
        self.vender(['222'], ['2'])
        self.client.logout()
        return Venta.objects.get()

    def test_admin_anula_y_devuelve_stock(self):
        v = self.crear_venta()
        self.client.login(username='adm', password='x12345678')
        self.client.post(reverse('ventas:anular', args=[v.pk]))
        v.refresh_from_db(); self.cola.refresh_from_db()
        self.assertEqual(v.estado, 'anulada')
        self.assertEqual(self.cola.stock, 3)
        self.assertTrue(MovimientoStock.objects.filter(tipo='entrada', motivo=f'Anulación venta {v.pk}').exists())

    def test_no_se_anula_dos_veces(self):
        v = self.crear_venta()
        self.client.login(username='adm', password='x12345678')
        self.client.post(reverse('ventas:anular', args=[v.pk]))
        self.client.post(reverse('ventas:anular', args=[v.pk]))
        self.cola.refresh_from_db()
        self.assertEqual(self.cola.stock, 3)

    def test_trabajador_no_puede_anular(self):
        v = self.crear_venta()
        self.client.login(username='trab', password='x12345678')
        self.assertEqual(self.client.post(reverse('ventas:anular', args=[v.pk])).status_code, 403)
        v.refresh_from_db()
        self.assertEqual(v.estado, 'completada')

    def test_anular_por_get_no_esta_permitido(self):
        v = self.crear_venta()
        self.client.login(username='adm', password='x12345678')
        self.assertEqual(self.client.get(reverse('ventas:anular', args=[v.pk])).status_code, 405)

    # --- historial / comprobante
    def test_trabajador_solo_ve_sus_ventas(self):
        v = self.crear_venta()
        self.client.login(username='otro', password='x12345678')
        self.assertEqual(self.client.get(reverse('ventas:detalle', args=[v.pk])).status_code, 404)
        self.assertEqual(len(self.client.get(reverse('ventas:lista')).context['object_list']), 0)

    def test_admin_ve_todas_y_el_comprobante(self):
        v = self.crear_venta()
        self.client.login(username='adm', password='x12345678')
        self.assertEqual(len(self.client.get(reverse('ventas:lista')).context['object_list']), 1)
        self.assertContains(self.client.get(reverse('ventas:detalle', args=[v.pk])), 'Anular venta')
