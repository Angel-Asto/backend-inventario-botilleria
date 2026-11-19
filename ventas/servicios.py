from django.db import transaction

from inventario.models import MovimientoStock
from inventario.servicios import registrar_movimiento
from productos.models import Producto

from .models import DetalleVenta, Venta


MAX_CANTIDAD_POR_PRODUCTO = 999


class VentaInvalida(ValueError):
    """La venta no cumple una regla de negocio; el mensaje se muestra al cajero."""


def registrar_venta(usuario, items, medio_pago, mayor_edad=False):
    """Registra una venta completa o nada (HU-13 a HU-15, HU-17).

    items: diccionario {codigo_barras: cantidad} con cantidades enteras positivas.
    Usa siempre el precio guardado en la base de datos, nunca uno enviado por el navegador.
    """
    if not items:
        raise VentaInvalida('Escanea al menos un producto.')
    if any(n > MAX_CANTIDAD_POR_PRODUCTO for n in items.values()):
        raise VentaInvalida(f'La cantidad máxima por producto es {MAX_CANTIDAD_POR_PRODUCTO}.')
    productos = {p.codigo_barras: p for p in
                 Producto.objects.select_related('categoria').filter(codigo_barras__in=items, activo=True)}
    if len(productos) != len(items):
        raise VentaInvalida('Hay productos que no existen o fueron dados de baja.')
    if medio_pago not in Venta.MedioPago.values:
        raise VentaInvalida('Elige el medio de pago.')
    if any(p.categoria.es_alcoholica for p in productos.values()) and not mayor_edad:
        raise VentaInvalida('Confirma que el cliente es mayor de 18 años para vender alcohol.')

    try:
        with transaction.atomic():
            venta = Venta.objects.create(usuario=usuario, medio_pago=medio_pago)
            total = 0
            for codigo, n in items.items():
                p = productos[codigo]
                DetalleVenta.objects.create(venta=venta, producto=p, cantidad=n, precio_unitario=p.precio)
                registrar_movimiento(p, MovimientoStock.Tipo.SALIDA, n, f'Venta {venta.pk}')
                total += n * p.precio
            venta.total = total
            venta.save(update_fields=['total'])
    except ValueError as e:  # stock insuficiente: la transacción se revierte y nada queda a medias
        raise VentaInvalida(str(e)) from e
    return venta


def anular_venta(venta_id):
    """Anula la venta y devuelve el stock (HU-16). Devuelve False si ya estaba anulada."""
    with transaction.atomic():
        venta = Venta.objects.select_for_update().get(pk=venta_id)
        if venta.estado == Venta.Estado.ANULADA:
            return False
        for d in venta.detalles.select_related('producto'):
            registrar_movimiento(d.producto, MovimientoStock.Tipo.ENTRADA, d.cantidad, f'Anulación venta {venta.pk}')
        venta.estado = Venta.Estado.ANULADA
        venta.save(update_fields=['estado'])
    return True
