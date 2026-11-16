from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.contrib.auth.views import LoginView, PasswordChangeView
from django.urls import reverse_lazy
from django.views.generic import CreateView, ListView, TemplateView

from .forms import CambioContrasenaForm, LoginForm, UsuarioCreacionForm
from .models import Usuario


class AdminRequeridoMixin(LoginRequiredMixin, UserPassesTestMixin):
    """El rol se valida en el servidor, no solo en el menú."""
    def test_func(self):
        return self.request.user.es_admin


class IniciarSesionView(LoginView):
    template_name = 'usuarios/iniciar_sesion.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True


class InicioView(LoginRequiredMixin, TemplateView):
    template_name = 'usuarios/inicio.html'


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