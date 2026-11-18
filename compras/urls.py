from django.urls import path

from . import views

app_name = 'compras'

urlpatterns = [
    # Proveedores
    path('proveedores/', views.ProveedorListaView.as_view(), name='proveedor_lista'),
    path('proveedores/nuevo/', views.ProveedorCrearView.as_view(), name='proveedor_crear'),
    path('proveedores/<int:pk>/editar/', views.ProveedorEditarView.as_view(), name='proveedor_editar'),
    path('proveedores/<int:pk>/eliminar/', views.ProveedorEliminarView.as_view(), name='proveedor_eliminar'),
]
