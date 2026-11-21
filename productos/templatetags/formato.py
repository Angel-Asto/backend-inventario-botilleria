from django import template

register = template.Library()


@register.filter
def pesos(valor):
    """Formato de pesos chilenos: 1990 -> "$1.990" (el peso no usa decimales)."""
    try:
        n = int(valor)
    except (TypeError, ValueError):
        return valor
    signo = '-' if n < 0 else ''
    return f'{signo}${abs(n):,}'.replace(',', '.')
