from django.urls import path

from . import views

app_name = 'inventario'

urlpatterns = [
    path('stock/', views.StockActualView.as_view(), name='stock'),
    path('movimientos/', views.MovimientoListaView.as_view(), name='movimientos'),
    path('ajuste/', views.AjusteStockView.as_view(), name='ajuste'),
]
