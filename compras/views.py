from django.contrib import messages
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, ListView, UpdateView

from usuarios.views import AdminRequeridoMixin

from .forms import ProveedorForm
from .models import Proveedor


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
