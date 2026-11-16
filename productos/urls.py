from django.urls import path

from . import views

app_name = 'productos'

urlpatterns = [
    path('', views.ProductoListaView.as_view(), name='lista'),
    path('nuevo/', views.ProductoCrearView.as_view(), name='crear'),
    path('<int:pk>/editar/', views.ProductoEditarView.as_view(), name='editar'),
    path('<int:pk>/baja/', views.ProductoBajaView.as_view(), name='baja'),
    path('categorias/', views.CategoriaListaView.as_view(), name='categoria_lista'),
    path('categorias/nueva/', views.CategoriaCrearView.as_view(), name='categoria_crear'),
    path('categorias/<int:pk>/editar/', views.CategoriaEditarView.as_view(), name='categoria_editar'),
    path('categorias/<int:pk>/eliminar/', views.CategoriaEliminarView.as_view(), name='categoria_eliminar'),
]