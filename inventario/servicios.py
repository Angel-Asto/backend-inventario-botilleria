from django.db import transaction

from productos.models import Producto

from .models import MovimientoStock


def registrar_movimiento(producto, tipo, cantidad, motivo):
    """Único punto donde cambia el stock: actualiza el producto y deja el movimiento.

    Debe llamarse dentro de transaction.atomic() cuando forme parte de una operación mayor.
    Lanza ValueError si el tipo no es válido, si la cantidad no es un entero positivo o si falta stock.
    """
    if tipo not in MovimientoStock.Tipo.values:
        raise ValueError(f'Tipo de movimiento no válido: {tipo!r}.')
    if not isinstance(cantidad, int) or isinstance(cantidad, bool) or cantidad < 1:
        raise ValueError('La cantidad debe ser un número entero mayor que cero.')
    if not (motivo or '').strip():
        raise ValueError('El movimiento necesita un motivo.')
    with transaction.atomic():
        p = Producto.objects.select_for_update().get(pk=producto.pk)
        if tipo == MovimientoStock.Tipo.SALIDA:
            if p.stock < cantidad:
                raise ValueError(f'Stock insuficiente de {p.nombre}: quedan {p.stock}.')
            p.stock -= cantidad
        else:
            p.stock += cantidad
        p.save(update_fields=['stock'])
        return MovimientoStock.objects.create(producto=p, tipo=tipo, cantidad=cantidad, motivo=motivo)
