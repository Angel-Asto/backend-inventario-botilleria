import logging

from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm
from django.core.cache import cache
from django.core.exceptions import ValidationError

from .models import Usuario

log = logging.getLogger('seguridad')

# Protección contra fuerza bruta en el inicio de sesión.
MAX_INTENTOS_USUARIO = 5     # intentos fallidos seguidos con el mismo usuario
MAX_INTENTOS_IP = 20         # intentos fallidos desde la misma IP (cualquier usuario)
BLOQUEO_SEGUNDOS = 15 * 60   # duración del bloqueo


class EstiloBootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            es_select = isinstance(campo.widget, forms.Select)
            campo.widget.attrs['class'] = 'form-select' if es_select else 'form-control'


class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    """Login con bloqueo temporal tras varios intentos fallidos (por usuario y por IP)."""

    error_messages = {
        **AuthenticationForm.error_messages,
        'bloqueado': 'Demasiados intentos fallidos. Espera 15 minutos o pide ayuda al administrador.',
    }
    bloqueado = False

    def _claves(self):
        usuario = (self.data.get('username') or '').strip().lower()
        ip = self.request.META.get('REMOTE_ADDR', '') if self.request else ''
        return f'login:usuario:{usuario}', f'login:ip:{ip}', usuario, ip

    def clean(self):
        clave_usuario, clave_ip, usuario, ip = self._claves()
        if cache.get(clave_usuario, 0) >= MAX_INTENTOS_USUARIO or cache.get(clave_ip, 0) >= MAX_INTENTOS_IP:
            self.bloqueado = True
            log.warning('Login bloqueado: usuario=%s ip=%s', usuario, ip)
            raise ValidationError(self.error_messages['bloqueado'], code='bloqueado')
        try:
            datos = super().clean()
        except ValidationError:
            for clave in (clave_usuario, clave_ip):
                cache.add(clave, 0, BLOQUEO_SEGUNDOS)
                cache.incr(clave)
            log.info('Login fallido: usuario=%s ip=%s', usuario, ip)
            raise
        cache.delete(clave_usuario)  # login correcto: se reinicia el contador del usuario
        return datos


class CambioContrasenaForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class UsuarioCreacionForm(EstiloBootstrapMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'rol')


class PerfilForm(EstiloBootstrapMixin, forms.ModelForm):
    """Datos que cada usuario puede cambiar de sí mismo. El rol y el usuario quedan fuera a propósito:
    aunque alguien los envíe a mano en el formulario, Django ignora los campos que no están en `fields`."""

    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'email')
        labels = {'first_name': 'Nombre', 'last_name': 'Apellido', 'email': 'Correo'}
        error_messages = {
            'first_name': {'required': 'Ingresa tu nombre.'},
            'email': {'invalid': 'Ingresa un correo válido, por ejemplo nombre@botilleria.cl.'},
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True  # el nombre aparece en ventas y comprobantes

    def clean_email(self):
        return self.cleaned_data['email'].strip().lower()