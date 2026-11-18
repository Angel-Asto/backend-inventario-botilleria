from django import forms

from productos.models import Producto
from usuarios.forms import EstiloBootstrapMixin

from .models import Compra, DetalleCompra, Proveedor


class ProveedorForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Proveedor
        fields = ('nombre', 'contacto')


class CompraForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Compra
        fields = ('proveedor', 'fecha')
        widgets = {'fecha': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d')}


class DetalleCompraForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = DetalleCompra
        fields = ('producto', 'cantidad')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['producto'].queryset = Producto.objects.filter(activo=True).order_by('nombre')


DetalleCompraFormSet = forms.inlineformset_factory(
    Compra, DetalleCompra, form=DetalleCompraForm,
    extra=2, min_num=1, validate_min=True, can_delete=False,
)
