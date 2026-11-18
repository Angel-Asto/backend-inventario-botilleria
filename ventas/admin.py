from django.contrib import admin

from .models import DetalleVenta, Venta


class DetalleVentaInline(admin.TabularInline):
    model = DetalleVenta
    extra = 0


@admin.register(Venta)
class VentaAdmin(admin.ModelAdmin):
    list_display = ('pk', 'fecha', 'usuario', 'medio_pago', 'total', 'estado')
    list_filter = ('estado', 'medio_pago')
    inlines = [DetalleVentaInline]
