from django.core.cache import cache
from django.test import TestCase
from django.urls import reverse

from .forms import MAX_INTENTOS_IP, MAX_INTENTOS_USUARIO
from .models import Usuario

CLAVE = 'Clave-segura-123'


class BloqueoLoginTests(TestCase):
    """Protección contra fuerza bruta en el inicio de sesión."""

    @classmethod
    def setUpTestData(cls):
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')
        cls.url = reverse('usuarios:iniciar_sesion')

    def setUp(self):
        cache.clear()

    def fallar(self, veces, usuario='trab'):
        for _ in range(veces):
            self.client.post(self.url, {'username': usuario, 'password': 'incorrecta'})

    def test_bloquea_tras_intentos_fallidos_aunque_luego_use_la_clave_correcta(self):
        self.fallar(MAX_INTENTOS_USUARIO)
        r = self.client.post(self.url, {'username': 'trab', 'password': CLAVE})
        self.assertContains(r, 'Demasiados intentos fallidos')
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_bloqueo_no_distingue_mayusculas_del_usuario(self):
        self.fallar(MAX_INTENTOS_USUARIO, usuario='TRAB')
        r = self.client.post(self.url, {'username': 'trab', 'password': CLAVE})
        self.assertContains(r, 'Demasiados intentos fallidos')

    def test_pocos_errores_no_bloquean_y_el_login_correcto_reinicia_el_contador(self):
        self.fallar(MAX_INTENTOS_USUARIO - 1)
        r = self.client.post(self.url, {'username': 'trab', 'password': CLAVE})
        self.assertRedirects(r, reverse('usuarios:inicio'))
        self.client.post(reverse('usuarios:cerrar_sesion'))
        self.fallar(MAX_INTENTOS_USUARIO - 1)
        r = self.client.post(self.url, {'username': 'trab', 'password': CLAVE})
        self.assertRedirects(r, reverse('usuarios:inicio'))

    def test_bloquea_por_ip_aunque_cambie_de_usuario(self):
        for i in range(MAX_INTENTOS_IP):
            self.client.post(self.url, {'username': f'inventado{i}', 'password': 'x'})
        r = self.client.post(self.url, {'username': 'trab', 'password': CLAVE})
        self.assertContains(r, 'Demasiados intentos fallidos')

    def test_mensaje_generico_no_revela_si_el_usuario_existe(self):
        r1 = self.client.post(self.url, {'username': 'trab', 'password': 'mala'})
        r2 = self.client.post(self.url, {'username': 'noexiste', 'password': 'mala'})
        self.assertContains(r1, 'Usuario o contraseña incorrectos.')
        self.assertContains(r2, 'Usuario o contraseña incorrectos.')


class PaginasDeErrorTests(TestCase):
    """Las páginas de error son propias y no muestran información interna."""

    @classmethod
    def setUpTestData(cls):
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')

    def test_404_propio_sin_rutas_internas(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.get('/no-existe/')
        self.assertContains(r, 'Página no encontrada', status_code=404)
        self.assertNotContains(r, 'URLconf', status_code=404)

    def test_403_propio(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.get(reverse('usuarios:lista'))
        self.assertContains(r, 'No tienes permiso', status_code=403)


class SesionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')

    def setUp(self):
        cache.clear()

    def test_panel_exige_login(self):
        r = self.client.get(reverse('usuarios:inicio'))
        self.assertRedirects(r, f"{reverse('usuarios:iniciar_sesion')}?next=/")

    def test_login_correcto_redirige_al_panel(self):
        r = self.client.post(reverse('usuarios:iniciar_sesion'), {'username': 'trab', 'password': CLAVE})
        self.assertRedirects(r, reverse('usuarios:inicio'))

    def test_login_no_redirige_a_sitios_externos(self):
        r = self.client.post(reverse('usuarios:iniciar_sesion') + '?next=https://malicioso.example',
                             {'username': 'trab', 'password': CLAVE, 'next': 'https://malicioso.example'})
        self.assertRedirects(r, reverse('usuarios:inicio'))

    def test_logout_solo_por_post(self):
        self.client.login(username='trab', password=CLAVE)
        self.assertEqual(self.client.get(reverse('usuarios:cerrar_sesion')).status_code, 405)
        self.client.post(reverse('usuarios:cerrar_sesion'))
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_cambio_de_contrasena_exige_la_actual(self):
        self.client.login(username='trab', password=CLAVE)
        url = reverse('usuarios:cambiar_contrasena')
        self.client.post(url, {'old_password': 'equivocada', 'new_password1': 'Otra-clave-456', 'new_password2': 'Otra-clave-456'})
        self.trab.refresh_from_db()
        self.assertTrue(self.trab.check_password(CLAVE))
        self.client.post(url, {'old_password': CLAVE, 'new_password1': 'Otra-clave-456', 'new_password2': 'Otra-clave-456'})
        self.trab.refresh_from_db()
        self.assertTrue(self.trab.check_password('Otra-clave-456'))

    def test_cambio_de_contrasena_exige_login(self):
        self.assertEqual(self.client.get(reverse('usuarios:cambiar_contrasena')).status_code, 302)


class GestionUsuariosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = Usuario.objects.create_user('adm', password=CLAVE, rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')

    def datos(self, **extra):
        d = {'username': 'nuevo', 'first_name': 'Ana', 'last_name': 'Pérez', 'email': 'ana@example.com',
             'rol': 'trabajador', 'password1': 'Clave-nueva-789', 'password2': 'Clave-nueva-789'}
        d.update(extra)
        return d

    def test_trabajador_no_ve_ni_crea_usuarios(self):
        self.client.login(username='trab', password=CLAVE)
        self.assertEqual(self.client.get(reverse('usuarios:lista')).status_code, 403)
        self.assertEqual(self.client.post(reverse('usuarios:crear'), self.datos(rol='admin')).status_code, 403)
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_admin_crea_trabajador(self):
        self.client.login(username='adm', password=CLAVE)
        r = self.client.post(reverse('usuarios:crear'), self.datos())
        self.assertRedirects(r, reverse('usuarios:lista'))
        nuevo = Usuario.objects.get(username='nuevo')
        self.assertEqual(nuevo.rol, 'trabajador')
        self.assertFalse(nuevo.es_admin)
        self.assertFalse(nuevo.is_staff)  # no entra al admin de Django

    def test_contrasena_debil_se_rechaza(self):
        self.client.login(username='adm', password=CLAVE)
        self.client.post(reverse('usuarios:crear'), self.datos(password1='12345678', password2='12345678'))
        self.assertFalse(Usuario.objects.filter(username='nuevo').exists())

    def test_superusuario_cuenta_como_admin(self):
        su = Usuario.objects.create_superuser('root', password=CLAVE)
        self.assertTrue(su.es_admin)


class PanelTests(TestCase):
    """El panel muestra los indicadores del día según el rol."""

    @classmethod
    def setUpTestData(cls):
        from productos.models import Categoria, Producto
        from ventas.models import Venta
        cls.admin = Usuario.objects.create_user('adm', password=CLAVE, rol='admin')
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador')
        cls.otro = Usuario.objects.create_user('otro', password=CLAVE, rol='trabajador')
        cat = Categoria.objects.create(nombre='Bebidas')
        Producto.objects.create(categoria=cat, codigo_barras='1', nombre='Agua', precio=900, stock=1, stock_minimo=5)
        Venta.objects.create(usuario=cls.trab, medio_pago='efectivo', total=3000)
        Venta.objects.create(usuario=cls.otro, medio_pago='tarjeta', total=1000)
        Venta.objects.create(usuario=cls.trab, medio_pago='efectivo', total=500, estado='anulada')

    def test_admin_ve_totales_del_local_sin_anuladas(self):
        self.client.login(username='adm', password=CLAVE)
        r = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual((r.context['ventas_hoy_total'], r.context['ventas_hoy_cantidad']), (4000, 2))
        self.assertEqual(r.context['ticket_promedio'], 2000)
        self.assertEqual(r.context['stock_bajo_cantidad'], 1)
        self.assertContains(r, '$4.000')

    def test_trabajador_solo_ve_sus_numeros(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.get(reverse('usuarios:inicio'))
        self.assertEqual((r.context['ventas_hoy_total'], r.context['ventas_hoy_cantidad']), (3000, 1))
        self.assertTrue(all(v.usuario == self.trab for v in r.context['ultimas_ventas']))
