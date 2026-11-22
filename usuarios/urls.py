from django.contrib.auth.views import LogoutView
from django.urls import path

from . import views

app_name = 'usuarios'

urlpatterns = [
    path('', views.InicioView.as_view(), name='inicio'),
    path('iniciar-sesion/', views.IniciarSesionView.as_view(), name='iniciar_sesion'),
    path('cerrar-sesion/', LogoutView.as_view(), name='cerrar_sesion'),
    path('perfil/', views.PerfilView.as_view(), name='perfil'),
    path('cambiar-contrasena/', views.CambiarContrasenaView.as_view(), name='cambiar_contrasena'),
    path('usuarios/', views.UsuarioListaView.as_view(), name='lista'),
    path('usuarios/nuevo/', views.UsuarioCrearView.as_view(), name='crear'),
]