from django import forms

from productos.models import Producto
from usuarios.forms import EstiloBootstrapMixin

from .models import MovimientoStock


class AjusteStockForm(EstiloBootstrapMixin, forms.Form):
    """Ajuste manual: mermas, roturas, vencidos o diferencias del conteo físico."""

    producto = forms.ModelChoiceField(queryset=Producto.objects.filter(activo=True).order_by('nombre'))
    tipo = forms.ChoiceField(choices=[
        (MovimientoStock.Tipo.ENTRADA, 'Entrada (suma al stock)'),
        (MovimientoStock.Tipo.SALIDA, 'Salida (merma, rotura o vencido)'),
    ])
    cantidad = forms.IntegerField(min_value=1, max_value=9999)
    motivo = forms.CharField(min_length=5, max_length=150,
                             help_text='Obligatorio. Ej.: "Botella rota en bodega" o "Conteo físico del viernes".')

    def clean_motivo(self):
        return self.cleaned_data['motivo'].strip()
