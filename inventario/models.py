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

    class Meta:
        ordering = ['-fecha', '-pk']
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gte=1), name='movimiento_cantidad_positiva'),
        ]

    def __str__(self):
        return f'{self.get_tipo_display()} {self.cantidad} - {self.producto}'
