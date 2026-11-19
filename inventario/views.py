from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.views.generic import ListView

from productos.models import Producto
from usuarios.views import AdminRequeridoMixin

from .models import MovimientoStock


class StockActualView(LoginRequiredMixin, ListView):
    """HU-10 y HU-11: stock actual con alerta de stock bajo."""
    template_name = 'inventario/stock_actual.html'
    paginate_by = 15

    def get_queryset(self):
        qs = Producto.objects.filter(activo=True).select_related('categoria').order_by('stock', 'nombre')
        if self.request.GET.get('solo_bajo'):
            qs = qs.filter(stock__lt=F('stock_minimo'))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['cantidad_bajo'] = Producto.objects.filter(activo=True, stock__lt=F('stock_minimo')).count()
        ctx['solo_bajo'] = bool(self.request.GET.get('solo_bajo'))
        return ctx


class MovimientoListaView(AdminRequeridoMixin, ListView):
    """HU-12: historial de movimientos."""
    model = MovimientoStock
    template_name = 'inventario/movimiento_lista.html'
    paginate_by = 15

    def get_queryset(self):
        qs = MovimientoStock.objects.select_related('producto', 'usuario')
        tipo = self.request.GET.get('tipo', '')
        q = self.request.GET.get('q', '').strip()
        if tipo in MovimientoStock.Tipo.values:
            qs = qs.filter(tipo=tipo)
        if q:
            qs = qs.filter(Q(producto__nombre__icontains=q) | Q(motivo__icontains=q))
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['qs'] = params.urlencode()
        ctx['tipos'] = MovimientoStock.Tipo.choices
        return ctx
