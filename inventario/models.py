from django.conf import settings
from django.db import models


class MovimientoStock(models.Model):
    class Tipo(models.TextChoices):
        ENTRADA = 'entrada', 'Entrada'
        SALIDA = 'salida', 'Salida'

    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='movimientos')
    fecha = models.DateTimeField(auto_now_add=True)
    tipo = models.CharField(max_length=10, choices=Tipo.choices)
    cantidad = models.PositiveIntegerField()
    motivo = models.CharField(max_length=200)
    # Quién hizo el cambio (auditoría). Vacío en movimientos anteriores a este campo.
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                related_name='movimientos_stock')

    class Meta:
        ordering = ['-fecha', '-pk']
        indexes = [  # historial ordenado por fecha y kardex de cada producto
            models.Index(fields=['-fecha'], name='movimiento_fecha_idx'),
            models.Index(fields=['producto', '-fecha'], name='movimiento_producto_fecha_idx'),
        ]
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gte=1), name='movimiento_cantidad_positiva'),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad} - {self.producto}'
