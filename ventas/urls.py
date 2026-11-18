from django.urls import path

from . import views

app_name = 'ventas'

urlpatterns = [
    path('', views.CajaView.as_view(), name='caja'),
    path('buscar/', views.BuscarProductoView.as_view(), name='buscar'),
    path('historial/', views.VentaListaView.as_view(), name='lista'),
]
