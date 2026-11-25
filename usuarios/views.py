import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views.generic import CreateView, FormView, ListView, TemplateView, UpdateView

from .forms import CambioContrasenaForm, LoginForm, PerfilForm, RestablecerClaveForm, UsuarioCreacionForm
from .models import Usuario

log = logging.getLogger('seguridad')

# Qué puede hacer cada rol (se muestra en el perfil).
PERMISOS_POR_ROL = {
    Usuario.Rol.ADMIN: [
        'Registrar ventas y anularlas indicando un motivo',
        'Administrar productos, categorías, proveedores y compras',
        'Ajustar el stock y ver el historial de movimientos',
        'Ver los reportes de todo el local y crear usuarios',
        'Restablecer la contraseña de otros usuarios (confirmando con la suya)',
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

class UsuarioRestablecerClaveView(AdminRequeridoMixin, FormView):
    """El admin asigna una contraseña nueva a otro usuario, confirmando con la suya (no se pueden ver: están con hash)."""
    form_class = RestablecerClaveForm
    template_name = 'usuarios/restablecer_clave.html'
    success_url = reverse_lazy('usuarios:lista')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not request.user.es_admin:
            return super().dispatch(request, *args, **kwargs)  # el mixin responde: login o 403
        self.usuario = get_object_or_404(Usuario, pk=kwargs['pk'])
        if self.usuario == request.user:
            messages.info(request, 'Tu propia contraseña se cambia en «Cambiar contraseña».')
            return redirect('usuarios:cambiar_contrasena')
        if self.usuario.is_superuser and not request.user.is_superuser:
            raise PermissionDenied  # un admin no puede tomar la cuenta de un superusuario
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(usuario=self.usuario, admin=self.request.user)
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx['usuario'] = self.usuario
        return ctx

    def form_valid(self, form):
        form.save()  # guarda el hash nuevo y cierra las sesiones abiertas de ese usuario
        log.warning('Contraseña restablecida: admin=%s usuario=%s', self.request.user.username, self.usuario.username)
        messages.success(self.request, f'Contraseña de {self.usuario.username} restablecida. '
                                       'Entrégasela en persona; podrá cambiarla desde su perfil.')
        return super().form_valid(form)
