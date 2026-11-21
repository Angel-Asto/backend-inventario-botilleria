from django.urls import path

from . import views

app_name = 'reportes'

urlpatterns = [
    path('', views.ReporteVentasView.as_view(), name='ventas'),
    path('ventas.csv', views.VentasCsvView.as_view(), name='ventas_csv'),
    path('productos.csv', views.ProductosCsvView.as_view(), name='productos_csv'),
]
