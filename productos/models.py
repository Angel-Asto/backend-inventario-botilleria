from django.core.validators import MinValueValidator
from django.db import models


class CategoriaManager(models.Manager):
    def get_by_natural_key(self, nombre):
        return self.get(nombre=nombre)


class ProductoManager(models.Manager):
    def get_by_natural_key(self, codigo_barras):
        return self.get(codigo_barras=codigo_barras)


class Categoria(models.Model):
    nombre = models.CharField(
        max_length=60, unique=True,
        error_messages={'unique': 'Ya existe una categoría con ese nombre.'},
    )
    es_alcoholica = models.BooleanField(default=False, help_text='Pide confirmar mayoría de edad al vender.')

    objects = CategoriaManager()  # clave natural: fixtures y respaldos usan el nombre, no el id

    class Meta:
        ordering = ['nombre']

    def natural_key(self):
        return (self.nombre,)

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

    objects = ProductoManager()  # clave natural: el código de barras

    class Meta:
        ordering = ['nombre']
        constraints = [
            models.CheckConstraint(condition=models.Q(precio__gte=1), name='producto_precio_positivo'),
        ]

    @property
    def stock_bajo(self):
        return self.stock < self.stock_minimo

    def natural_key(self):
        return (self.codigo_barras,)
    natural_key.dependencies = ['productos.categoria']

    def __str__(self):
        return self.nombre