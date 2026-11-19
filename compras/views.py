from django.contrib import messages
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from inventario.models import MovimientoStock
from inventario.servicios import registrar_movimiento
from usuarios.views import AdminRequeridoMixin

from .forms import CompraForm, DetalleCompraFormSet, ProveedorForm
from .models import Compra, Proveedor


# ---------------------------------------------------------------- Proveedores
class ProveedorListaView(AdminRequeridoMixin, ListView):
    model = Proveedor
    template_name = 'compras/proveedor_lista.html'
    paginate_by = 10

    def get_queryset(self):
        qs = Proveedor.objects.all()
        q = self.request.GET.get('q', '').strip()
        if q:
            qs = qs.filter(Q(nombre__icontains=q) | Q(contacto__icontains=q))
        return qs


class ProveedorCrearView(AdminRequeridoMixin, CreateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'compras/proveedor_form.html'
    success_url = reverse_lazy('compras:proveedor_lista')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor creado.')
        return super().form_valid(form)


class ProveedorEditarView(AdminRequeridoMixin, UpdateView):
    model = Proveedor
    form_class = ProveedorForm
    template_name = 'compras/proveedor_form.html'
    success_url = reverse_lazy('compras:proveedor_lista')

    def form_valid(self, form):
        messages.success(self.request, 'Proveedor actualizado.')
        return super().form_valid(form)


class ProveedorEliminarView(AdminRequeridoMixin, DeleteView):
    model = Proveedor
    template_name = 'compras/proveedor_confirmar_eliminar.html'
    success_url = reverse_lazy('compras:proveedor_lista')

    def form_valid(self, form):
        try:
            resp = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'No se puede eliminar: el proveedor tiene compras registradas.')
            return redirect(self.success_url)
        messages.success(self.request, 'Proveedor eliminado.')
        return resp


# -------------------------------------------------------------------- Compras
class CompraListaView(AdminRequeridoMixin, ListView):
    model = Compra
    template_name = 'compras/compra_lista.html'
    paginate_by = 10

    def get_queryset(self):
        return Compra.objects.select_related('proveedor').prefetch_related('detalles')


class CompraCrearView(AdminRequeridoMixin, View):
    """HU-20 y HU-21: registra la compra y suma las cantidades al stock."""
    template_name = 'compras/compra_form.html'

    def get(self, request):
        return render(request, self.template_name, {'form': CompraForm(), 'formset': DetalleCompraFormSet(instance=Compra())})

    def post(self, request):
        form = CompraForm(request.POST)
        formset = DetalleCompraFormSet(request.POST, instance=Compra())
        if form.is_valid() and formset.is_valid():
            with transaction.atomic():
                compra = form.save()
                formset.instance = compra
                detalles = formset.save()
                for d in detalles:
                    registrar_movimiento(d.producto, MovimientoStock.Tipo.ENTRADA, d.cantidad, f'Compra {compra.pk}',
                                         request.user)
            messages.success(request, 'Compra registrada y stock actualizado.')
            return redirect('compras:compra_detalle', pk=compra.pk)
        return render(request, self.template_name, {'form': form, 'formset': formset})


class CompraDetalleView(AdminRequeridoMixin, DetailView):
    model = Compra
    template_name = 'compras/compra_detalle.html'
