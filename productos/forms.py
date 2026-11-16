from django import forms

from usuarios.forms import EstiloBootstrapMixin

from .models import Categoria, Producto


class CategoriaForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Categoria
        fields = ('nombre',)

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip()


class ProductoForm(EstiloBootstrapMixin, forms.ModelForm):
    class Meta:
        model = Producto
        fields = ('categoria', 'codigo_barras', 'nombre', 'precio', 'stock', 'stock_minimo')
        labels = {
            'codigo_barras': 'Código de barras',
            'stock_minimo': 'Stock mínimo (alerta)',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            # Al editar, el stock solo cambia con compras y ventas.
            self.fields['stock'].disabled = True
            self.fields['stock'].help_text = 'El stock cambia con las compras y las ventas.'

    def clean_codigo_barras(self):
        return self.cleaned_data['codigo_barras'].strip()

    def clean_nombre(self):
        return self.cleaned_data['nombre'].strip()