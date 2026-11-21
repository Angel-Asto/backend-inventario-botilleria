from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.db.models import ProtectedError, Q
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from inventario.models import MovimientoStock
from inventario.servicios import registrar_movimiento
from usuarios.views import AdminRequeridoMixin

from .forms import CategoriaForm, ProductoForm
from .models import Categoria, Producto


# ---------- Productos ----------
class ProductoListaView(LoginRequiredMixin, ListView):
    model = Producto
    template_name = 'productos/producto_lista.html'
    paginate_by = 10

    def get_queryset(self):
        qs = Producto.objects.select_related('categoria')
        q = self.request.GET.get('q', '').strip()
        categoria = self.request.GET.get('categoria', '')
        estado = self.request.GET.get('estado', 'activos')
        if q:  # busca por nombre o por código de barras
            qs = qs.filter(Q(nombre__icontains=q) | Q(codigo_barras__icontains=q))
        if categoria.isdigit():
            qs = qs.filter(categoria_id=categoria)
        if estado == 'activos':
            qs = qs.filter(activo=True)
        elif estado == 'bajas':
            qs = qs.filter(activo=False)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        params = self.request.GET.copy()
        params.pop('page', None)
        ctx['qs'] = params.urlencode()
        ctx['categorias'] = Categoria.objects.all()
        ctx['estado'] = self.request.GET.get('estado', 'activos')
        return ctx


class ProductoCrearView(AdminRequeridoMixin, CreateView):
    form_class = ProductoForm
    template_name = 'productos/formulario.html'
    success_url = reverse_lazy('productos:lista')
    extra_context = {'titulo': 'Registrar producto', 'volver': reverse_lazy('productos:lista')}

    def form_valid(self, form):
        # El stock inicial entra como movimiento, para que el historial cuadre con el stock.
        stock_inicial = form.cleaned_data.get('stock') or 0
        with transaction.atomic():
            form.instance.stock = 0
            respuesta = super().form_valid(form)
            if stock_inicial:
                registrar_movimiento(self.object, MovimientoStock.Tipo.ENTRADA, stock_inicial, 'Stock inicial',
                                     self.request.user)
        messages.success(self.request, 'Producto registrado correctamente.')
        return respuesta


class ProductoEditarView(AdminRequeridoMixin, UpdateView):
    model = Producto
    form_class = ProductoForm
    template_name = 'productos/formulario.html'
    success_url = reverse_lazy('productos:lista')
    extra_context = {'titulo': 'Editar producto', 'volver': reverse_lazy('productos:lista')}

    def form_valid(self, form):
        messages.success(self.request, 'Producto actualizado correctamente.')
        return super().form_valid(form)


class ProductoBajaView(AdminRequeridoMixin, DetailView):
    """Da de baja o reactiva. Nunca borra el producto."""
    model = Producto
    template_name = 'productos/producto_confirmar_baja.html'

    def post(self, request, *args, **kwargs):
        producto = self.get_object()
        producto.activo = not producto.activo
        producto.save(update_fields=['activo'])
        estado = 'reactivado' if producto.activo else 'dado de baja'
        messages.success(request, f'Producto {estado} correctamente.')
        return redirect('productos:lista')


# ---------- Categorías ----------
class CategoriaListaView(AdminRequeridoMixin, ListView):
    model = Categoria
    template_name = 'productos/categoria_lista.html'


class CategoriaCrearView(AdminRequeridoMixin, CreateView):
    form_class = CategoriaForm
    template_name = 'productos/formulario.html'
    success_url = reverse_lazy('productos:categoria_lista')
    extra_context = {'titulo': 'Registrar categoría', 'volver': reverse_lazy('productos:categoria_lista')}

    def form_valid(self, form):
        messages.success(self.request, 'Categoría registrada correctamente.')
        return super().form_valid(form)


class CategoriaEditarView(AdminRequeridoMixin, UpdateView):
    model = Categoria
    form_class = CategoriaForm
    template_name = 'productos/formulario.html'
    success_url = reverse_lazy('productos:categoria_lista')
    extra_context = {'titulo': 'Editar categoría', 'volver': reverse_lazy('productos:categoria_lista')}

    def form_valid(self, form):
        messages.success(self.request, 'Categoría actualizada correctamente.')
        return super().form_valid(form)


class CategoriaEliminarView(AdminRequeridoMixin, DeleteView):
    model = Categoria
    template_name = 'productos/confirmar_eliminar.html'
    success_url = reverse_lazy('productos:categoria_lista')

    def form_valid(self, form):
        try:
            respuesta = super().form_valid(form)
        except ProtectedError:
            messages.error(self.request, 'No se puede eliminar: la categoría tiene productos.')
            return redirect(self.success_url)
        messages.success(self.request, 'Categoría eliminada correctamente.')
        return respuesta