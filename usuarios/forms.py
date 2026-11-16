from django import forms
from django.contrib.auth.forms import AuthenticationForm, PasswordChangeForm, UserCreationForm

from .models import Usuario


class EstiloBootstrapMixin:
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            es_select = isinstance(campo.widget, forms.Select)
            campo.widget.attrs['class'] = 'form-select' if es_select else 'form-control'


class LoginForm(EstiloBootstrapMixin, AuthenticationForm):
    pass


class CambioContrasenaForm(EstiloBootstrapMixin, PasswordChangeForm):
    pass


class UsuarioCreacionForm(EstiloBootstrapMixin, UserCreationForm):
    class Meta(UserCreationForm.Meta):
        model = Usuario
        fields = ('username', 'first_name', 'last_name', 'email', 'rol')