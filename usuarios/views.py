from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView, UpdateView

from .forms import CambioContrasenaForm, LoginForm, PerfilForm, UsuarioCreacionForm
from .models import Usuario

# Qué puede hacer cada rol (se muestra en el perfil).
PERMISOS_POR_ROL = {
    Usuario.Rol.ADMIN: [
        'Registrar ventas y anularlas indicando un motivo',
        'Administrar productos, categorías, proveedores y compras',
        'Ajustar el stock y ver el historial de movimientos',
        'Ver los reportes de todo el local y crear usuarios',
    ],
    Usuario.Rol.TRABAJADOR: [
        'Registrar ventas en la caja',
        'Ver sus propias ventas y comprobantes',
        'Consultar el catálogo y el stock actual',
    ],
}


class PerfilView(LoginRequiredMixin, UpdateView):
    """Perfil del usuario que inició sesión. No recibe un id en la URL: nadie puede abrir el perfil de otro."""
    form_class = PerfilForm
    template_name = 'usuarios/perfil.html'
    success_url = reverse_lazy('usuarios:perfil')

    def get_object(self, queryset=None):
        # Una copia fresca: si el formulario trae errores, la tarjeta (request.user) no muestra datos inválidos.
        return Usuario.objects.get(pk=self.request.user.pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        rol = Usuario.Rol.ADMIN if self.request.user.es_admin else self.request.user.rol
        ctx['permisos'] = PERMISOS_POR_ROL.get(rol, [])
        return ctx

    def form_valid(self, form):
        messages.success(self.request, 'Perfil actualizado correctamente.')
        return super().form_valid(form)


class AdminRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """El rol se valida en el servidor, no solo en el menú."""
    def test_func(self):
        return self.request.user.es_admin


class IniciarSesionView(LoginView):
    template_name = 'usuarios/iniciar_sesion.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class InicioView(LoginRequiredMixin, TemplateView):
    """Panel con los indicadores del día. El admin ve todo el local; el trabajador, solo sus ventas."""
    template_name = 'usuarios/inicio.html'

    def get_context_data(self, **kwargs):
        from django.db.models import Count, F, Sum
        from django.utils import timezone

        from productos.models import Producto
        from ventas.models import Venta

        ctx = super().get_context_data(**kwargs)
        user = self.request.user
        ventas = Venta.objects.select_related('usuario')
        if not user.es_admin:
            ventas = ventas.filter(usuario=user)
        hoy = ventas.filter(fecha=timezone.localdate(), estado=Venta.Estado.COMPLETADA)
        resumen = hoy.aggregate(total=Sum('total'), cantidad=Count('id'))
        total, cantidad = resumen['total'] or 0, resumen['cantidad']
        bajo = Producto.objects.filter(activo=True, stock__lt=F('stock_minimo')).order_by('stock', 'nombre')
        ctx.update({
            'ventas_hoy_total': total,
            'ventas_hoy_cantidad': cantidad,
            'ticket_promedio': total // cantidad if cantidad else 0,
            'stock_bajo_cantidad': bajo.count(),
            'stock_bajo': bajo[:5],
            'ultimas_ventas': ventas[:5],
        })
        return ctx


class CambiarContrasenaView(PasswordChangeView):
    template_name = 'usuarios/cambiar_contrasena.html'
    form_class = CambioContrasenaForm
    success_url = reverse_lazy('usuarios:cambiar_contrasena')

    def form_valid(self, form):
        messages.success(self.request, 'Contraseña actualizada correctamente.')
        return super().form_valid(form)


class UsuarioListaView(AdminRequeridoMixin, ListView):
    model = Usuario
    template_name = 'usuarios/usuario_lista.html'
    ordering = ['username']


class UsuarioCrearView(AdminRequeridoMixin, CreateView):
    form_class = UsuarioCreacionForm
    template_name = 'usuarios/usuario_form.html'
    success_url = reverse_lazy('usuarios:lista')

    def form_valid(self, form):
        messages.success(self.request, 'Usuario creado correctamente.')
        return super().form_valid(form)