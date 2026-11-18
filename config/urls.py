from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('usuarios.urls')),
    path('productos/', include('productos.urls')),
    path('compras/', include('compras.urls')),
    path('inventario/', include('inventario.urls')),
    path('ventas/', include('ventas.urls')),
]