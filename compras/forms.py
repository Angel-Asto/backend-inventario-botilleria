from django import forms

from usuarios.forms import EstiloBootstrapMixin

from .models import Proveedor


class ProveedorForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ('nombre', 'contacto')
