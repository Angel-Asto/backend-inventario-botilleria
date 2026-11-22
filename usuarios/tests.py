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


class SeedDemoTests(TestCase):
    """seed_demo: idempotente, coherente con el stock y solo en desarrollo."""

    CLAVES = {'DEMO_ADMIN_PASSWORD': 'Prueba-Admin-987', 'DEMO_WORKER_PASSWORD': 'Prueba-Caja-987'}

    def correr(self, *args):
        import io
        import os
        from unittest import mock

        from django.core.management import call_command
        from django.test import override_settings
        salida = io.StringIO()
        with override_settings(DEBUG=True), mock.patch.dict(os.environ, self.CLAVES):
            call_command('seed_demo', *args, stdout=salida)
        return salida.getvalue()

    def conteos(self):
        from compras.models import Compra, Proveedor
        from inventario.models import MovimientoStock
        from productos.models import Categoria, Producto
        from ventas.models import Venta
        return [m.objects.count() for m in (Usuario, Categoria, Producto, Proveedor, Compra, Venta, MovimientoStock)]

    def test_es_idempotente(self):
        self.correr()
        primera = self.conteos()
        self.correr()
        self.assertEqual(self.conteos(), primera)
        self.assertEqual(primera[:6], [2, 5, 12, 2, 1, 1])

    def test_stock_cuadra_con_los_movimientos(self):
        from django.db.models import Q, Sum

        from productos.models import Producto
        self.correr()
        self.correr()
        for p in Producto.objects.annotate(
                entradas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='entrada'), default=0),
                salidas=Sum('movimientos__cantidad', filter=Q(movimientos__tipo='salida'), default=0)):
            self.assertEqual(p.stock, p.entradas - p.salidas, p.nombre)

    def test_usuarios_con_rol_y_clave_del_entorno_sin_imprimirla(self):
        salida = self.correr('--solo-catalogo')
        self.assertTrue(Usuario.objects.get(username='admin_demo').es_admin)
        self.assertFalse(Usuario.objects.get(username='trabajador_demo').es_admin)
        self.assertTrue(self.client.login(username='trabajador_demo', password=self.CLAVES['DEMO_WORKER_PASSWORD']))
        for clave in self.CLAVES.values():
            self.assertNotIn(clave, salida)

    def test_se_niega_con_debug_apagado(self):
        from django.core.management import CommandError, call_command
        from django.test import override_settings
        with override_settings(DEBUG=False), self.assertRaises(CommandError):
            call_command('seed_demo')
        self.assertFalse(Usuario.objects.filter(username='admin_demo').exists())


class RespaldoTests(TestCase):
    def test_respaldar_y_restaurar(self):
        import io
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        from productos.models import Categoria, Producto
        from ventas.models import Venta
        Usuario.objects.create_user('trab', password=CLAVE)
        cat = Categoria.objects.create(nombre='Bebidas')
        p = Producto.objects.create(categoria=cat, codigo_barras='1', nombre='Cola', precio=1000, stock=3)
        Venta.objects.create(usuario=Usuario.objects.get(), medio_pago='efectivo', total=1000)
        with tempfile.TemporaryDirectory() as carpeta:
            call_command('respaldar', carpeta=carpeta, stdout=io.StringIO())
            archivo = next(Path(carpeta).glob('respaldo_*.json'))
            Venta.objects.all().delete(); Producto.objects.all().delete(); Categoria.objects.all().delete()
            Usuario.objects.all().delete()
            call_command('loaddata', str(archivo), verbosity=0)
        self.assertEqual(Producto.objects.get(codigo_barras='1').stock, 3)
        self.assertEqual(Venta.objects.get().usuario.username, 'trab')
        self.assertTrue(Usuario.objects.get().check_password(CLAVE))


class ConfiguracionTests(TestCase):
    """La configuración del .env.example funciona tal cual en un clon limpio."""

    def test_database_url_vacia_usa_sqlite(self):
        import os
        import subprocess
        import sys
        from pathlib import Path

        from django.conf import settings
        entorno = dict(os.environ, DATABASE_URL='', SECRET_KEY='clave-de-prueba-' + 'x' * 40, DEBUG='True')
        codigo = ("import django, os; os.environ['DJANGO_SETTINGS_MODULE']='config.settings'; django.setup(); "
                  "from django.conf import settings as s; print(s.DATABASES['default']['ENGINE'])")
        r = subprocess.run([sys.executable, '-c', codigo], cwd=Path(settings.BASE_DIR), env=entorno,
                           capture_output=True, text=True, timeout=60)
        self.assertEqual(r.stdout.strip(), 'django.db.backends.sqlite3', r.stderr[-500:])


class PerfilTests(TestCase):
    """Página de perfil: muestra el rol y solo deja editar los datos propios permitidos."""

    @classmethod
    def setUpTestData(cls):
        cls.trab = Usuario.objects.create_user('trab', password=CLAVE, rol='trabajador', first_name='Tomás')
        cls.admin = Usuario.objects.create_user('adm', password=CLAVE, rol='admin', first_name='Ana')
        cls.url = reverse('usuarios:perfil')

    def datos(self, **extra):
        d = {'first_name': 'Tomás', 'last_name': 'Cajero', 'email': 'tomas@botilleria.cl'}
        d.update(extra)
        return d

    def test_exige_login(self):
        self.assertEqual(self.client.get(self.url).status_code, 302)

    def test_muestra_el_rol_y_lo_que_puede_hacer(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.get(self.url)
        self.assertContains(r, 'Rol: Trabajador')
        self.assertContains(r, 'Registrar ventas en la caja')
        self.assertNotContains(r, 'Ver los reportes de todo el local')
        self.client.login(username='adm', password=CLAVE)
        self.assertContains(self.client.get(self.url), 'Rol: Admin')

    def test_edita_nombre_y_correo(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.post(self.url, self.datos(email='  Tomas@Botilleria.CL '))
        self.assertRedirects(r, self.url)
        self.trab.refresh_from_db()
        self.assertEqual((self.trab.last_name, self.trab.email), ('Cajero', 'tomas@botilleria.cl'))

    def test_correo_invalido_y_nombre_vacio_se_rechazan(self):
        self.client.login(username='trab', password=CLAVE)
        r = self.client.post(self.url, self.datos(email='tomas@', first_name='   '))
        self.assertContains(r, 'Ingresa un correo válido')
        self.assertContains(r, 'Ingresa tu nombre.')
        self.trab.refresh_from_db()
        self.assertEqual((self.trab.first_name, self.trab.email), ('Tomás', ''))

    def test_no_puede_cambiarse_el_rol_ni_el_usuario(self):
        self.client.login(username='trab', password=CLAVE)
        self.client.post(self.url, self.datos(rol='admin', username='jefe', is_staff='on', is_superuser='on'))
        self.trab.refresh_from_db()
        self.assertEqual((self.trab.rol, self.trab.username, self.trab.is_staff, self.trab.is_superuser),
                         ('trabajador', 'trab', False, False))
        self.assertFalse(self.trab.es_admin)

    def test_solo_edita_su_propio_perfil(self):
        self.client.login(username='trab', password=CLAVE)
        self.client.post(self.url, self.datos(last_name='Cambiado'))
        self.admin.refresh_from_db()
        self.assertEqual(self.admin.last_name, '')  # el perfil no recibe id: no hay forma de apuntar a otro usuario
