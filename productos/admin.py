from django.contrib import admin

from .models import Categoria, Producto


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'codigo_barras', 'categoria', 'precio', 'stock', 'activo')
    list_filter = ('categoria', 'activo')
    search_fields = ('nombre', 'codigo_barras')
    readonly_fields = ('stock',)  # el stock solo cambia con compras, ventas y ajustes (deja movimiento)

    def has_delete_permission(self, request, obj=None):
        return False  # los productos se dan de baja, no se borran
