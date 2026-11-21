import csv
from datetime import date, timedelta

from django.db.models import Count, F, Q, Sum
from django.db.models.functions import Coalesce
from django.http import HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView

from productos.models import Producto
from usuarios.views import AdminRequeridoMixin
from ventas.models import Venta

MAX_DIAS = 366


def rango_fechas(request):
    """Lee ?desde=AAAA-MM-DD&hasta=AAAA-MM-DD. Por defecto, los últimos 7 días. Ignora fechas inválidas."""
    hoy = timezone.localdate()

    def leer(nombre, defecto):
        try:
            return date.fromisoformat(request.GET.get(nombre, ''))
        except ValueError:
            return defecto

    hasta = leer('hasta', hoy)
    desde = leer('desde', hasta - timedelta(days=6))
    if desde > hasta:
        desde, hasta = hasta, desde
    if (hasta - desde).days >= MAX_DIAS:
        desde = hasta - timedelta(days=MAX_DIAS - 1)
    return desde, hasta


def ranking_productos(desde, hasta):
    """Unidades y monto vendidos por producto en el período (solo ventas completadas)."""
    filtro = Q(detalles_venta__venta__estado=Venta.Estado.COMPLETADA,
               detalles_venta__venta__fecha__range=(desde, hasta))
    return Producto.objects.select_related('categoria').annotate(
        unidades=Coalesce(Sum('detalles_venta__cantidad', filter=filtro), 0),
        monto=Coalesce(Sum(F('detalles_venta__cantidad') * F('detalles_venta__precio_unitario'), filter=filtro), 0),
    )


class ReporteVentasView(AdminRequeridoMixin, TemplateView):
    """Ventas por período, por medio de pago y por vendedor; productos más y menos vendidos."""
    template_name = 'reportes/ventas.html'

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        desde, hasta = rango_fechas(self.request)
        ventas = Venta.objects.filter(fecha__range=(desde, hasta))
        completadas = ventas.filter(estado=Venta.Estado.COMPLETADA)
        resumen = completadas.aggregate(total=Sum('total'), cantidad=Count('id'))
        total, cantidad = resumen['total'] or 0, resumen['cantidad']

        por_fecha = {f['fecha']: f for f in completadas.values('fecha').annotate(total=Sum('total'), cantidad=Count('id'))}
        dias = [{'fecha': desde + timedelta(days=i), 'total': por_fecha.get(desde + timedelta(days=i), {}).get('total', 0),
                 'cantidad': por_fecha.get(desde + timedelta(days=i), {}).get('cantidad', 0)}
                for i in range((hasta - desde).days + 1)]
        maximo = max([d['total'] for d in dias] + [1])
        for d in dias:
            d['porcentaje'] = round(d['total'] * 100 / maximo)

        ranking = ranking_productos(desde, hasta)
        medios = dict(Venta.MedioPago.choices)
        ctx.update({
            'desde': desde, 'hasta': hasta,
            'total': total, 'cantidad': cantidad, 'ticket_promedio': total // cantidad if cantidad else 0,
            'anuladas': ventas.filter(estado=Venta.Estado.ANULADA).count(),
            'dias': dias,
            'por_medio': [dict(m, nombre=medios.get(m['medio_pago'], m['medio_pago']))
                          for m in completadas.values('medio_pago').annotate(total=Sum('total'), cantidad=Count('id')).order_by('-total')],
            'por_vendedor': completadas.values('usuario__username').annotate(total=Sum('total'), cantidad=Count('id')).order_by('-total'),
            'mas_vendidos': ranking.filter(unidades__gt=0).order_by('-unidades', 'nombre')[:10],
            'menos_vendidos': ranking.filter(activo=True).order_by('unidades', 'nombre')[:10],
            'qs': f'desde={desde.isoformat()}&hasta={hasta.isoformat()}',
        })
        return ctx


def _celda(valor):
    """Evita la inyección de fórmulas al abrir el CSV en Excel (texto que empieza con = + - @)."""
    texto = str(valor)
    return "'" + texto if texto[:1] in ('=', '+', '-', '@', '\t', '\r') else texto


def _respuesta_csv(nombre, encabezado, filas):
    resp = HttpResponse(content_type='text/csv; charset=utf-8')
    resp['Content-Disposition'] = f'attachment; filename="{nombre}"'
    resp.write('﻿')  # BOM: Excel reconoce los tildes
    w = csv.writer(resp, delimiter=';')  # Excel en español usa punto y coma
    w.writerow(encabezado)
    for fila in filas:
        w.writerow([_celda(v) if isinstance(v, str) else v for v in fila])
    return resp


class VentasCsvView(AdminRequeridoMixin, View):
    def get(self, request):
        desde, hasta = rango_fechas(request)
        ventas = Venta.objects.filter(fecha__range=(desde, hasta)).select_related('usuario').order_by('creada_en')
        filas = ((v.pk, timezone.localtime(v.creada_en).strftime('%d-%m-%Y %H:%M'), v.usuario.username,
                  v.get_medio_pago_display(), v.total, v.get_estado_display()) for v in ventas)
        return _respuesta_csv(f'ventas_{desde}_{hasta}.csv',
                              ['N°', 'Fecha y hora', 'Vendedor', 'Medio de pago', 'Total', 'Estado'], filas)


class ProductosCsvView(AdminRequeridoMixin, View):
    def get(self, request):
        desde, hasta = rango_fechas(request)
        ranking = ranking_productos(desde, hasta).order_by('-unidades', 'nombre')
        filas = ((p.codigo_barras, p.nombre, p.categoria.nombre, p.unidades, p.monto, p.stock) for p in ranking)
        return _respuesta_csv(f'productos_vendidos_{desde}_{hasta}.csv',
                              ['Código', 'Producto', 'Categoría', 'Unidades vendidas', 'Monto', 'Stock actual'], filas)
