from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Venta(models.Model):
    class MedioPago(models.TextChoices):
        EFECTIVO = 'efectivo', 'Efectivo'
        TARJETA = 'tarjeta', 'Tarjeta'

    class Estado(models.TextChoices):
        COMPLETADA = 'completada', 'Completada'
        ANULADA = 'anulada', 'Anulada'

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='ventas')
    fecha = models.DateField(default=timezone.localdate)
    creada_en = models.DateTimeField(default=timezone.now, editable=False)  # hora exacta (cierre de caja, reportes)
    medio_pago = models.CharField(max_length=20, choices=MedioPago.choices)
    total = models.PositiveIntegerField(default=0)
    estado = models.CharField(max_length=20, choices=Estado.choices, default=Estado.COMPLETADA)
    # Auditoría de la anulación: quién, cuándo y por qué.
    anulada_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, null=True, blank=True,
                                    related_name='ventas_anuladas', editable=False)
    anulada_en = models.DateTimeField(null=True, blank=True, editable=False)
    motivo_anulacion = models.CharField(max_length=200, blank=True, editable=False)

    class Meta:
        ordering = ['-fecha', '-pk']

    def __str__(self):
        return f'Venta {self.pk}'


class DetalleVenta(models.Model):
    venta = models.ForeignKey(Venta, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey('productos.Producto', on_delete=models.PROTECT, related_name='detalles_venta')
    cantidad = models.PositiveIntegerField(validators=[MinValueValidator(1)])
    precio_unitario = models.PositiveIntegerField()

    class Meta:
        constraints = [
            models.CheckConstraint(condition=models.Q(cantidad__gte=1), name='detalleventa_cantidad_positiva'),
        ]

    @property
    def subtotal(self):
        return self.cantidad * self.precio_unitario

    def __str__(self):
        return f'{self.cantidad} x {self.producto}'
