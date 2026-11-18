from django.contrib import admin

from .models import Compra, DetalleCompra, Proveedor


@admin.register(Proveedor)
class ProveedorAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'contacto')
    search_fields = ('nombre', 'contacto')


class DetalleCompraInline(admin.TabularInline):
    model = DetalleCompra
    extra = 0


@admin.register(Compra)
class CompraAdmin(admin.ModelAdmin):
    list_display = ('pk', 'proveedor', 'fecha')
    inlines = [DetalleCompraInline]
