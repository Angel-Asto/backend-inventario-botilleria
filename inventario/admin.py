from django.contrib import admin

from .models import MovimientoStock


@admin.register(MovimientoStock)
class MovimientoStockAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'producto', 'tipo', 'cantidad', 'motivo')
    list_filter = ('tipo',)
