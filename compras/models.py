from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Proveedor(models.Model):
    nombre = models.CharField(max_length=120)
    contacto = models.CharField(max_length=120)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'proveedores'

    def __str__(self):
        return self.nombre


class Compra(models.Model):
    proveedor = models.ForeignKey(Proveedor, on_delete=models.PROTECT, related_name='compras')
    fecha = models.DateField(default=timezone.localdate)

    class Meta:
        ordering = ['-fecha', '-pk']

    @property
    def total_unidades(self):
        return sum(d.cantidad for d in self.detalles.all())

    def __str__(self):
        return f'Compra {self.pk} - {self.proveedor}'


class DetalleCompra(models.Model):
    compra = models.ForeignKey(Compra, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='detalles_compra')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gte=1), name='detallecompra_cantidad_positiva'),
        ]

    def __str__(self):
        return f'{self.cantidad} x {self.producto}'
