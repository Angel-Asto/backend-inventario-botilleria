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
