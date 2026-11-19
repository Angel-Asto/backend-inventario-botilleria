import secrets

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.cache import cache
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from productos.models import Producto
from usuarios.views import AdminRequeridoMixin

from .models import Venta
from .servicios import MAX_CANTIDAD_POR_PRODUCTO, VentaInvalida, anular_venta, registrar_venta


def _datos_producto(p):
    return {
        'codigo': p.codigo_barras, 'nombre': p.nombre, 'precio': p.precio,
        'stock': p.stock, 'alcohol': p.categoria.es_alcoholica,
    }


class BuscarProductoView(LoginRequiredMixin, View):
    """Lo usa la caja: al escanear un código devuelve el producto en JSON."""

    def get(self, request):
        codigo = request.GET.get('codigo', '').strip()
        p = Producto.objects.select_related('categoria').filter(codigo_barras=codigo, activo=True).first()
        if not p:
            return JsonResponse({'error': 'Producto no encontrado o dado de baja.'}, status=404)
        return JsonResponse(_datos_producto(p))


def _nuevo_token(request):
    """Token de un solo uso para el formulario de la caja (evita registrar dos veces la misma venta)."""
    token = secrets.token_urlsafe(16)
    request.session['caja_tokens'] = (request.session.get('caja_tokens', []) + [token])[-10:]
    return token


def _usar_token(request, token):
    """True solo la primera vez que llega un token emitido para esta sesión."""
    if not token or token not in request.session.get('caja_tokens', []):
        return False
    request.session['caja_tokens'] = [t for t in request.session['caja_tokens'] if t != token]
    return cache.add(f'caja:token:{token}', 1, 60 * 60)  # atómico: frena dos envíos simultáneos


class CajaView(LoginRequiredMixin, View):
    """HU-13 a HU-15 y HU-17: escanear, totalizar, confirmar edad y cobrar."""
    template_name = 'ventas/caja.html'

    def render_caja(self, request, carrito):
        return render(request, self.template_name, {'carrito': carrito, 'token': _nuevo_token(request)})

    def get(self, request):
        return self.render_caja(request, [])

    def post(self, request):
        if not _usar_token(request, request.POST.get('token')):
            messages.error(request, 'Esta venta ya se había enviado. Revisa el historial antes de cobrar de nuevo.')
            return redirect('ventas:lista')
        items = {}
        for codigo, cantidad in zip(request.POST.getlist('codigo'), request.POST.getlist('cantidad')):
            cantidad = (cantidad or '').strip()
            if not (cantidad.isascii() and cantidad.isdigit()):  # descarta textos, negativos y decimales
                continue
            # Más de 6 dígitos ya supera el máximo: no se convierte un número gigante (evitaba un error 500).
            n = int(cantidad) if len(cantidad) <= 6 else MAX_CANTIDAD_POR_PRODUCTO + 1
            if n > 0:
                codigo = codigo.strip()
                items[codigo] = items.get(codigo, 0) + n

        try:
            venta = registrar_venta(request.user, items, request.POST.get('medio_pago'),
                                    mayor_edad=bool(request.POST.get('mayor_edad')))
        except VentaInvalida as e:
            productos = {p.codigo_barras: p for p in
                         Producto.objects.select_related('categoria').filter(codigo_barras__in=items, activo=True)}
            carrito = [dict(_datos_producto(productos[c]), cantidad=n) for c, n in items.items() if c in productos]
            messages.error(request, str(e))
            return self.render_caja(request, carrito)
        messages.success(request, 'Venta registrada.')
        return redirect('ventas:detalle', pk=venta.pk)


class VentaListaView(LoginRequiredMixin, ListView):
    model = Venta
    template_name = 'ventas/venta_lista.html'
    paginate_by = 15

    def get_queryset(self):
        qs = Venta.objects.select_related('usuario')
        if not self.request.user.es_admin:  # el trabajador solo ve las suyas
            qs = qs.filter(usuario=self.request.user)
        return qs


class VentaDetalleView(LoginRequiredMixin, DetailView):
    """HU-18: comprobante."""
    model = Venta
    template_name = 'ventas/venta_detalle.html'

    def get_queryset(self):
        qs = Venta.objects.select_related('usuario').prefetch_related('detalles__producto')
        if not self.request.user.es_admin:
            qs = qs.filter(usuario=self.request.user)
        return qs


class VentaAnularView(AdminRequeridoMixin, View):
    """HU-16: anula la venta y devuelve el stock."""

    def post(self, request, pk):
        get_object_or_404(Venta, pk=pk)
        if anular_venta(pk):
            messages.success(request, 'Venta anulada y stock devuelto.')
        else:
            messages.error(request, 'La venta ya estaba anulada.')
        return redirect('ventas:detalle', pk=pk)
