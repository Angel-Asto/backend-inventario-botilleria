from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import F, Q
from django.urls import reverse_lazy
from django.views.generic import FormView, ListView

from productos.models import Producto
from usuarios.views import AdminRequeridoMixin

from .forms import AjusteStockForm
from .models import MovimientoStock
from .servicios import registrar_movimiento


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


class AjusteStockView(AdminRequeridoMixin, FormView):
    """Ajuste manual de inventario (mermas, roturas, conteo). Pasa por registrar_movimiento."""
    form_class = AjusteStockForm
    template_name = 'inventario/ajuste_form.html'
    success_url = reverse_lazy('inventario:movimientos')

    def form_valid(self, form):
        d = form.cleaned_data
        try:
            registrar_movimiento(d['producto'], d['tipo'], d['cantidad'], f"Ajuste: {d['motivo']}", self.request.user)
        except ValueError as e:  # por ejemplo, una salida mayor al stock
            form.add_error(None, str(e))
            return self.form_invalid(form)
        messages.success(self.request, f"Ajuste registrado: {d['producto']} ({d['cantidad']} u.).")
        return super().form_valid(form)
