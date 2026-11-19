from django.contrib import admin

from inventario.admin import SoloLecturaAdmin, SoloLecturaInline

from .models import Compra, DetalleCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto')
    search_fields = ('nombre', 'contacto')


class DetalleCompraInline(SoloLecturaInline):
    model = DetalleCompra


@admin.register(Compra)
class CompraAdmin(SoloLecturaAdmin):  # las compras se registran en la app para que sumen stock
    list_display = ('pk', 'proveedor', 'fecha')
    inlines = [DetalleCompraInline]
