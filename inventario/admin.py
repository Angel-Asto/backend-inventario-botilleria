from django.contrib import admin

from .models import MovimientoStock


class SoloLecturaAdmin(admin.ModelAdmin):
    """Historiales que solo cambian desde la aplicación: el admin de Django puede verlos, no editarlos.

    Así ningún cambio de stock, compra o venta se salta registrar_movimiento ni deja el stock desincronizado.
    """

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


class SoloLecturaInline(admin.TabularInline):
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MovimientoStock)
class MovimientoStockAdmin(SoloLecturaAdmin):
    list_display = ('fecha', 'producto', 'tipo', 'cantidad', 'motivo')
    list_filter = ('tipo',)
    search_fields = ('producto__nombre', 'motivo')
