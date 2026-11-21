from django.contrib import admin

from inventario.admin import SoloLecturaAdmin, SoloLecturaInline

from .models import DetalleVenta, Venta


class DetalleVentaInline(SoloLecturaInline):
    model = DetalleVenta


@admin.register(Venta)
class VentaAdmin(SoloLecturaAdmin):  # las ventas y anulaciones se hacen en la caja para mover el stock
    list_display = ('pk', 'fecha', 'usuario', 'medio_pago', 'total', 'estado')
    list_filter = ('estado', 'medio_pago')
    inlines = [DetalleVentaInline]
