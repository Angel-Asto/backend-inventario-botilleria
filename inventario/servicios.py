from django.db import transaction

from productos.models import Producto

from .models import MovimientoStock


def registrar_movimiento(producto, tipo, cantidad, motivo):
    """Único punto donde cambia el stock: actualiza el producto y deja el movimiento.

    Debe llamarse dentro de transaction.atomic() cuando forme parte de una operación mayor.
    """
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
