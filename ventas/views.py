from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.views import View
from django.views.generic import DetailView, ListView

from inventario.models import MovimientoStock
from inventario.servicios import registrar_movimiento
from productos.models import Producto
from usuarios.views import AdminRequeridoMixin

from .models import DetalleVenta, Venta


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


class CajaView(LoginRequiredMixin, View):
    """HU-13 a HU-15 y HU-17: escanear, totalizar, confirmar edad y cobrar."""
    template_name = 'ventas/caja.html'

    def get(self, request):
        return render(request, self.template_name, {'carrito': []})

    def post(self, request):
        items = {}
        for codigo, cantidad in zip(request.POST.getlist('codigo'), request.POST.getlist('cantidad')):
            try:
                n = int(cantidad)
            except ValueError:
                n = 0
            if n > 0:
                items[codigo] = items.get(codigo, 0) + n

        productos = {p.codigo_barras: p for p in
                     Producto.objects.select_related('categoria').filter(codigo_barras__in=items, activo=True)}
        carrito = [dict(_datos_producto(productos[c]), cantidad=n) for c, n in items.items() if c in productos]
        medio = request.POST.get('medio_pago')

        def error(msg):
            messages.error(request, msg)
            return render(request, self.template_name, {'carrito': carrito})

        if not items:
            return error('Escanea al menos un producto.')
        if len(productos) != len(items):
            return error('Hay productos que no existen o fueron dados de baja.')
        if medio not in Venta.MedioPago.values:
            return error('Elige el medio de pago.')
        if any(p.categoria.es_alcoholica for p in productos.values()) and not request.POST.get('mayor_edad'):
            return error('Confirma que el cliente es mayor de 18 años para vender alcohol.')

        try:
            with transaction.atomic():
                venta = Venta.objects.create(usuario=request.user, medio_pago=medio)
                total = 0
                for codigo, n in items.items():
                    p = productos[codigo]
                    DetalleVenta.objects.create(venta=venta, producto=p, cantidad=n, precio_unitario=p.precio)
                    registrar_movimiento(p, MovimientoStock.Tipo.SALIDA, n, f'Venta {venta.pk}')
                    total += n * p.precio
                venta.total = total
                venta.save(update_fields=['total'])
        except ValueError as e:  # stock insuficiente: nada queda a medias
            return error(str(e))
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
        with transaction.atomic():
            venta = Venta.objects.select_for_update().get(pk=pk)
            if venta.estado == Venta.Estado.ANULADA:
                messages.error(request, 'La venta ya estaba anulada.')
                return redirect('ventas:detalle', pk=pk)
            for d in venta.detalles.select_related('producto'):
                registrar_movimiento(d.producto, MovimientoStock.Tipo.ENTRADA, d.cantidad, f'Anulación venta {venta.pk}')
            venta.estado = Venta.Estado.ANULADA
            venta.save(update_fields=['estado'])
        messages.success(request, 'Venta anulada y stock devuelto.')
        return redirect('ventas:detalle', pk=pk)
