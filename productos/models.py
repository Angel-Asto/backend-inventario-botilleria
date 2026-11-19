from django.core.validators import MinValueValidator
from django.db import models


class Categoria(models.Model):
    nombre = models.CharField(
        max_length=60, unique=True,
        error_messages={'unique': 'Ya existe una categoría con ese nombre.'},
    )
    es_alcoholica = models.BooleanField(default=False, help_text='Pide confirmar mayoría de edad al vender.')

    class Meta:
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name='productos')
    codigo_barras = models.CharField(
        max_length=30, unique=True,
        error_messages={'unique': 'Ya existe un producto con ese código de barras.'},
    )
    nombre = models.CharField(max_length=120)
    precio = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    stock = models.PositiveIntegerField(default=0)
    stock_minimo = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)  # False = dado de baja, no se borra

    class Meta:
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gte=1), name='producto_precio_positivo'),
        ]

    @property
    def stock_bajo(self):
        return self.stock < self.stock_minimo

    def __str__(self):
        return self.nombre