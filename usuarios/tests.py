from django.test import TestCase
from django.urls import reverse

from .models import Usuario

CLAVE = 'Clave-segura-123'


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
