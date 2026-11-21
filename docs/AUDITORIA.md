# Auditoría técnica – Sistema de Inventario y Ventas (Botillería)

> Revisión hecha el 19-11-2026 sobre la rama `feature/aastorga` (commit `db6a5cc`).
> Alcance: los 96 archivos versionados (config, 6 apps, migraciones, 24 plantillas, static, README, requirements, .gitignore, .env.example) y el historial de Git de todas las ramas.
> Roles: DBA, backend Django, frontend/UX y revisión de seguridad.

## Cómo se verificó

| Verificación | Resultado |
|---|---|
| `python manage.py test` | **46 tests OK** (37,6 s) |
| `python manage.py makemigrations --check --dry-run` | Sin cambios pendientes ✅ |
| `python manage.py check --deploy` | **1 error y 6 advertencias** (detalle en la sección B) |
| `pip-audit`, `bandit`, `coverage` | **No instalados**: no se pudo medir vulnerabilidades de dependencias, análisis estático ni cobertura real. Se recomienda instalarlos en Fase 2. |
| Pruebas puntuales (BD en memoria, sin tocar `db.sqlite3`) | 15 sondas; los resultados se citan en cada hallazgo como **[Sonda N]** |
| Historial de Git (`git log --all -p`) | Revisado por archivos sensibles y patrones de secretos |
| Visibilidad del repo | **Público** (la API de GitHub responde sin autenticación) |

Resultados de las sondas:

1. `registrar_movimiento(p, 'SALIDA', 3, …)` (tipo en mayúsculas) **sumó** 3 unidades: stock 5 → 8.
2. `registrar_movimiento(..., cantidad=0)` se aceptó y dejó un movimiento de 0 unidades.
3. Cantidad −2 → `IntegrityError` (lo frena el CHECK de la BD, no el servicio).
4. Crear un producto con stock 5 no genera ningún `MovimientoStock`.
5. `Producto(precio=0)` se guarda directo en la BD (el mínimo 1 solo lo valida el formulario).
6. `stock = -1` → `IntegrityError` (CHECK de `PositiveIntegerField`) ✅.
7. Caja con cantidad de 25 dígitos → **HTTP 500** (`OverflowError`).
8. Una compra creada fuera de la vista (como hace el admin de Django) **no suma stock**.
9. 30 logins fallidos seguidos → siempre 200; el login correcto posterior entra (**sin bloqueo**).
10. `?page=abc` y `?page=99999` → 404 (correcto, sin error 500) ✅.
11. Buscador JSON sin sesión → 302 al login ✅; expone `codigo, nombre, precio, stock, alcohol`.
12. `GET /cerrar-sesion/` → 405 (cierre solo por POST) ✅.
13. Sesión: 14 días, no expira al cerrar el navegador; `HttpOnly` y `SameSite=Lax` ✅; `X-Frame-Options: DENY` ✅.
14. `python-dotenv` está instalado y en requirements, pero `settings.py` **no lo usa**: el `.env` se ignora.
15. Con `DEBUG=True` el 404 muestra todas las rutas internas.

---

## 1. Resumen ejecutivo

El proyecto está **bien encaminado**. La estructura es una app por gestor, el ORM se usa siempre (no hay SQL crudo), los roles se validan en el servidor, las anulaciones van por POST con CSRF, el trabajador solo ve sus propias ventas (no hay IDOR) y todo el stock de ventas y compras pasa por un servicio transaccional con pruebas. Los riesgos principales son de **configuración** (secretos y DEBUG en el código, `.env` ignorado), de **integridad del stock** por caminos alternativos (admin de Django, servicio sin validar sus parámetros) y de **presentación** (README desactualizado, panel vacío, reportes sin implementar).

| Área | Nota (1–10) | En una línea |
|---|---|---|
| Base de datos | **6,5** | Buen modelo base y CHECK en enteros positivos; faltan índices, auditoría por usuario, costo de compra y cerrar los caminos que desincronizan el stock. |
| Seguridad | **5,5** | Autorización bien resuelta; la `SECRET_KEY` está publicada en un repo público, la configuración no viene del entorno y no hay límite de intentos de login. |
| Backend | **7** | Código limpio y legible con 46 tests; faltan validaciones en el servicio de stock, un error 500 en la caja, tests de usuarios y la app de reportes. |
| Frontend | **6,5** | Diseño consistente y responsive, caja usable con lector y cámara; el panel está vacío, falta protección ante doble envío y hay detalles de accesibilidad. |
| Presentación y entrega | **5** | El README describe tecnologías que no se usan (DRF, serializadores, `.env`) y no explica cómo tener datos de demo en un clon limpio. |

---

## 2. Hallazgos por severidad

Esfuerzo: **S** = menos de 1 hora · **M** = medio día · **L** = 1 día o más.

### Crítico

| # | Archivo:línea | Problema | Riesgo | Corrección propuesta | Esf. |
|---|---|---|---|---|---|
| C1 | `config/settings.py:23` | La `SECRET_KEY` está escrita en el código y commiteada desde el primer commit (`6221d00`). Está en `main`, `develop` y ambas ramas `feature/*` de un **repositorio público**. | Quien la tenga puede falsificar cookies de sesión firmadas, tokens de restablecimiento de contraseña y mensajes firmados de cualquier despliegue que use esa clave. | **Rotarla**: generar una clave nueva, leerla desde el entorno (`SECRET_KEY` en `.env`) y no reutilizar nunca la publicada. No hace falta reescribir el historial (la clave vieja queda inservible al dejar de usarse), pero sí invalidar las sesiones existentes. | S |
| C2 | `config/settings.py:26`, `:29` | `DEBUG = True` fijo en el código y `ALLOWED_HOSTS = ['*']` mientras DEBUG esté activo. | Si se expone con un túnel (ngrok/cloudflared) o en la red del instituto, cualquier error muestra código, variables y rutas internas [Sonda 15], y se acepta cualquier cabecera Host. | Leer `DEBUG` y `ALLOWED_HOSTS` del entorno (`python-dotenv` ya está instalado [Sonda 14]), con `DEBUG=False` por defecto y una lista explícita de hosts. | S |

### Alto

| # | Archivo:línea | Problema | Riesgo | Corrección propuesta | Esf. |
|---|---|---|---|---|---|
| A1 | `inventario/servicios.py:15-20` | El servicio no valida `tipo` ni `cantidad`: cualquier valor distinto de `'salida'` se trata como entrada, y acepta 0 unidades. | Un error de tipeo en una llamada futura (`'SALIDA'`, `'Salida'`) **suma** stock en vez de restarlo [Sonda 1]; se generan movimientos de 0 [Sonda 2]. | Validar `tipo in MovimientoStock.Tipo.values` y `cantidad >= 1` al inicio, con `ValueError` claro. Agregar tests. | S |
| A2 | `inventario/admin.py:6-9`, `productos/admin.py:11-15`, `compras/admin.py:17-20`, `ventas/admin.py:11-15` | El admin de Django permite crear, editar y borrar movimientos, compras, ventas, totales y el stock del producto sin pasar por `registrar_movimiento`. | Stock desincronizado con el historial [Sonda 8], ventas con total o estado modificados sin rastro, compras borradas que no descuentan stock. Solo afecta a usuarios `is_staff`, pero es justo el usuario `admin` de la demo. | Dejar `MovimientoStock`, `Compra`, `Venta` y sus detalles en solo lectura en el admin (`has_add/change/delete_permission = False`) y `stock` como `readonly_fields` en `ProductoAdmin`. | S |
| A3 | `usuarios/views.py:17-20` | No hay límite de intentos de login. | Fuerza bruta sin freno contra cuentas de trabajador o admin [Sonda 9]. | `django-axes` (bloqueo por usuario e IP tras 5 intentos durante 15 min, con registro) o, sin dependencias, un contador en caché en `IniciarSesionView`. | M |
| A4 | `ventas/views.py:43-50`, `:76` | La cantidad de la caja se convierte con `int()` sin tope y el `DetalleVenta` se crea **antes** de validar el stock. | Una cantidad enorme produce `OverflowError` → **HTTP 500** [Sonda 7]; con `DEBUG=True` muestra la traza. La transacción revierte, así que no queda nada a medias. | Acotar (`1 ≤ n ≤ 9999`) al leer el POST y validar el stock antes de crear los detalles. Agregar test. | S |
| A5 | `usuarios/tests.py:1-15` | El archivo de tests de usuarios es una **copia de `urls.py`**: no contiene ninguna prueba. | Login, cambio de contraseña, creación de usuarios y el control de roles (la base de toda la autorización) no tienen tests. | Escribir tests: login correcto e incorrecto, logout por POST, cambio de contraseña, trabajador sin acceso a `usuarios:lista`/`crear`, admin crea un trabajador. | M |
| A6 | `config/settings.py` (falta) | Sin `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, HSTS ni ajustes de sesión. | `check --deploy` da 6 advertencias. En un PC de caja compartido, la sesión dura 14 días aunque se cierre el navegador [Sonda 13]. | Bloque `if not DEBUG:` con cookies seguras, HSTS corto (p. ej. 3600) y redirección SSL. `SESSION_COOKIE_AGE = 8 h` y `SESSION_EXPIRE_AT_BROWSER_CLOSE = True` siempre. | S |

### Medio

| # | Archivo:línea | Problema | Riesgo | Corrección propuesta | Esf. |
|---|---|---|---|---|---|
| M1 | `productos/forms.py:20`, `productos/views.py:45-53` | El stock inicial de un producto nuevo se guarda directo, sin movimiento. | El historial no cuadra con el stock: suma de entradas − salidas ≠ stock [Sonda 4]. | Crear el producto con stock 0 y registrar una `ENTRADA` con motivo «Stock inicial» dentro de la misma transacción. | S |
| M2 | `inventario/models.py:9-13`, `ventas/views.py:111-125`, `compras/models.py:18-20` | Ni `MovimientoStock`, ni la anulación de una venta, ni `Compra` guardan **quién** lo hizo ni **por qué**. | Sin auditoría: no se sabe quién anuló una venta, quién registró una compra ni quién cambió precios. | Agregar `usuario` (FK, PROTECT) a `MovimientoStock` y `Compra`; `anulada_por`, `anulada_en` y `motivo_anulacion` en `Venta`. Bitácora simple (`Bitacora`: usuario, acción, objeto, detalle, fecha) para cambios de precio, altas de usuario y bajas de producto. | M |
| M3 | `inventario/servicios.py:14` | `select_for_update()` **no bloquea en SQLite** (se ignora). | Con dos cajas a la vez, SQLite serializa las escrituras y una de las ventas puede fallar con `database is locked` (no se pierde stock, porque el CHECK y la transacción lo impiden, pero el cajero ve un error). En PostgreSQL sí bloquea la fila. | En SQLite: `OPTIONS: {'transaction_mode': 'IMMEDIATE', 'timeout': 20}` (Django ≥ 5.1). En cualquier motor, descontar con un `UPDATE` condicional: `filter(pk=…, stock__gte=n).update(stock=F('stock') - n)` y verificar las filas afectadas. | S |
| M4 | `productos/models.py:26` | `precio ≥ 1` solo se valida en el formulario; en la BD solo existe `≥ 0`. | Precio 0 desde el admin, un script o un fixture [Sonda 5]. | `CheckConstraint(condition=Q(precio__gte=1), name='precio_positivo')`. Lo mismo con `cantidad ≥ 1` en `DetalleVenta` y `DetalleCompra`. | S |
| M5 | `ventas/models.py:17` | `Venta.fecha` es `DateField`: no guarda la hora. | No se puede hacer cierre de caja por turno ni reportes por hora; el comprobante no muestra la hora. | Agregar `creada_en = DateTimeField(auto_now_add=True)` y mantener `fecha` para filtrar por día. | S |
| M6 | `ventas/models.py:22-23`, `inventario/models.py:15-16` | No hay índices para los filtros y ordenamientos más usados. | Con miles de ventas, los listados y reportes ordenados por fecha escanean la tabla completa. | `indexes`: `Venta(fecha)`, `Venta(usuario, fecha)`, `Venta(estado, fecha)`, `MovimientoStock(fecha)`, `MovimientoStock(producto, fecha)`. Los FK ya tienen índice propio. | S |
| M7 | `compras/models.py:33-36` | `DetalleCompra` no guarda el costo unitario. | Sin costo no hay margen, valorización del inventario ni reporte de gasto en compras. | Agregar `costo_unitario` (`PositiveIntegerField`) y un total de la compra. | S |
| M8 | `config/settings.py:91-96` | Base de datos fija en SQLite; no hay configuración por entorno. | Pasar a PostgreSQL obliga a editar código. | Leer `DATABASE_URL` (con `dj-database-url` o un parseo simple), con SQLite por defecto. | S |
| M9 | `.gitignore:3` y ausencia de seeds | Cada clon parte con la BD vacía: hay que crear superusuario, categorías y productos a mano antes de la demo. | Demo frágil y equipo trabajando con datos distintos. | Comando idempotente `seed_demo` + fixtures del catálogo (ver sección 3). | M |
| M10 | `templates/ventas/caja.html:25`, `:48` | El botón **Pagar** no se deshabilita al enviar. | Un doble clic o un Enter repetido crea **dos ventas** y descuenta el stock dos veces. | Deshabilitar el botón en `submit`. En el servidor, un token de un solo uso en la sesión para la caja. | S |
| M11 | `templates/base.html:8-10`, `templates/includes/escaner_camara.html:10` | Bootstrap, Bootstrap Icons y `html5-qrcode` se cargan desde CDN sin `integrity` (SRI). | Si un CDN sirve código alterado, se ejecuta en la caja con la sesión del usuario. Además, sin internet la app pierde estilos y la cámara. | Agregar `integrity` + `crossorigin`, o copiar las librerías a `static/vendor/` (también sirve para una demo sin internet). | S |
| M12 | ausencia de `templates/403.html`, `404.html`, `500.html` y de `LOGGING` | Páginas de error por defecto y ningún registro de eventos de seguridad. | Con `DEBUG=False` el usuario ve páginas genéricas en inglés; no queda registro de accesos denegados ni de fallos. | Plantillas propias que extienden `base.html` y `LOGGING` a archivo para `django.security` y `django.request`. | S |
| M13 | `README.md:7-8`, `:43`, `:71-75`, `:127`, `:151-160`, `:167` | El README dice Django 5.x (es 6.1), menciona DRF y «serializadores» (no se usan), presenta `.env` como si se leyera (no se lee), tiene la hoja de ruta desactualizada y un enlace roto (`github.com//kinekay`). | En la evaluación se contrasta el README con el código: estas diferencias restan credibilidad. | Corregir versiones y tecnologías, actualizar la hoja de ruta y documentar el flujo de clon limpio, la seguridad aplicada y las pruebas. | S |
| M14 | `reportes/*.py` | La app `reportes` está vacía, pero el README la promete («ventas por período, más y menos vendidos»). | Historia de usuario sin cumplir en la demo. | Vistas de reporte con `annotate`/`Sum` (ver sección 3). | M |

### Bajo

| # | Archivo:línea | Problema | Riesgo | Corrección propuesta | Esf. |
|---|---|---|---|---|---|
| B1 | `config/settings.py:121-127` y `:148-149` | `LANGUAGE_CODE` y `TIME_ZONE` se definen dos veces (la segunda pisa a la primera). | Confusión al mantenerlo. | Dejar una sola definición (`es-cl`, `America/Santiago`). | S |
| B2 | `config/settings.py:139-143` | `check --deploy` falla (`mail.E001`) por el backend de correo de consola. | Bloquea el chequeo de despliegue; hoy no se envían correos. | Correo de consola solo si `DEBUG`; SMTP desde el entorno en producción. | S |
| B3 | `requirements.txt` | Está en **UTF-16** (GitHub lo muestra como binario) y fija `python-dotenv`, que no se usa. | Diffs ilegibles en los PR; dependencia muerta. | Convertir a UTF-8 y usar `python-dotenv` en `settings.py` (C2). | S |
| B4 | `compras/views.py:100-102` | `CompraDetalleView` sin `prefetch_related('detalles__producto')`. | Consulta N+1 en el detalle (una consulta por producto). | Agregar `get_queryset` con prefetch. | S |
| B5 | `templates/compras/proveedor_lista.html:32`, `:34` | `&q={{ request.GET.q }}` sin `urlencode`. | No es XSS (lo escapa el autoescape), pero una búsqueda con `&` o `#` rompe la paginación. | Usar `{{ request.GET.q\|urlencode }}` o el patrón `qs` de las otras listas. | S |
| B6 | `templates/base.html:53` | Los mensajes `warning`/`info` se pintan con estilo de éxito. | Confusión en mensajes futuros. | Mapear `m.tags` a la clase de alerta correspondiente. | S |
| B7 | `templates/productos/producto_lista.html:49-50`, `categoria_lista.html:15-16` | Botones que solo tienen un ícono, sin `aria-label`. | Accesibilidad: el lector de pantalla no anuncia la acción. | Agregar `aria-label="Editar"`, `"Dar de baja"`, etc. | S |
| B8 | `templates/usuarios/inicio.html:4` | El panel dice «Resumen del día», pero no muestra datos. | Primera pantalla de la demo vacía. | KPIs del día (ver sección 3). | M |
| B9 | `usuarios/views.py:37-50` | No se pueden editar, desactivar ni cambiar de rol usuarios desde la app (solo desde el admin de Django). | Si un trabajador deja el local, no hay forma simple de bloquearlo. | Vista de edición y de activar/desactivar, solo para admin, sin permitir que alguien se quite su propio rol de admin. | M |
| B10 | `compras/models.py:6-8` | `Proveedor` sin RUT, teléfono ni correo separados, y sin `unique` en el nombre. | Proveedores duplicados y datos de contacto sin formato. | Agregar `rut` (único, opcional) y separar el contacto en teléfono y correo. | S |
| B11 | `config/settings.py:50-55`, `requirements-dev.txt` | `runserver_plus` deja activo el depurador de Werkzeug (con PIN y limitado a localhost). | Solo para desarrollo; nunca debe usarse con un túnel. | Documentarlo en el README y no usarlo con ngrok/cloudflared. | S |

### Lo que está bien (verificado)

- **Autorización en el servidor**: todas las vistas tienen `LoginRequiredMixin` o `AdminRequeridoMixin`. Las de admin responden 403 al trabajador (tests en compras, inventario, productos y ventas).
- **Sin IDOR en ventas**: `VentaListaView` y `VentaDetalleView` filtran por usuario si no es admin (`ventas/views.py:92-108`), con test.
- **Acciones destructivas por POST con CSRF**: anular venta (con test de 405 en GET), baja de producto, eliminar categoría o proveedor y cerrar sesión [Sonda 12]. Todos los formularios POST tienen `{% csrf_token %}`.
- **Sin SQL crudo**: no hay `.raw()`, `.extra()` ni `cursor`. Las búsquedas usan `Q` con `icontains`.
- **Sin XSS en el JS de la caja**: el carrito se arma con `createElement` y `textContent`. El único `innerHTML` (`templates/productos/formulario.html:27`) es un texto fijo. El `|safe` de `templates/includes/campos.html:6` solo aplica a `help_text` definidos en el código.
- **El precio se toma del servidor** en la venta (`ventas/views.py:76`), no del formulario. El total se calcula en el backend y se guarda el precio histórico en el detalle.
- **Stock transaccional**: venta, compra y anulación son atómicas. Si falta stock no queda nada a medias (test). El CHECK de `PositiveIntegerField` impide stock negativo en la BD [Sonda 6].
- **`on_delete` coherente**: `PROTECT` en categoría, producto, proveedor y usuario con historial; `CASCADE` solo de cabecera a detalle. La baja de producto es lógica (`activo`), no borra.
- **Dinero en enteros (CLP)**: correcto, el peso chileno no tiene decimales y no hay errores de redondeo.
- **Paginación robusta**: un parámetro de página inválido da 404, no 500 [Sonda 10].
- **Migraciones**: ordenadas, con dependencias explícitas y reversibles (solo `CreateModel`/`AddField`). `makemigrations --check` está limpio y un `migrate` en BD vacía funciona (probado en el worktree).
- **Repositorio**: `.env`, `db.sqlite3`, `venv/` y `certs/` están ignorados y **nunca se commitearon** (verificado en todo el historial). `.env.example` no trae valores reales. Las contraseñas del historial son solo de tests.

---

## 3. Mejoras y funcionalidades priorizadas

✅ = cabe antes de la presentación (≤ medio día cada una) · ⏳ = más largo, opcional.

### Backend

| Prioridad | Mejora | Cabe | Notas |
|---|---|---|---|
| 1 | **Configuración por entorno** (C1, C2, A6, B1-B3, M8): `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL` y cookies seguras desde `.env` | ✅ | Requisito de la Fase 2 |
| 2 | **`seed_demo` idempotente + fixtures del catálogo** (M9) | ✅ | Requisito de la Fase 2 (detalle abajo) |
| 3 | Validaciones del servicio de stock y tope de cantidad en la caja (A1, A4) + tests | ✅ | |
| 4 | Admin de Django en solo lectura para movimientos, compras y ventas (A2) | ✅ | |
| 5 | Tests de usuarios y roles (A5) | ✅ | |
| 6 | Límite de intentos de login (A3) | ✅ | `django-axes` o contador en caché |
| 7 | Stock inicial como movimiento (M1) y CheckConstraints (M4) | ✅ | |
| 8 | Auditoría: usuario en movimiento y compra, datos de anulación, bitácora (M2) | ✅ | Suma puntos en la sección de seguridad |
| 9 | **Reportes** (M14): ventas por día y rango, top 10 más y menos vendidos, ventas por medio de pago y por vendedor | ✅ | `annotate(Sum)` sobre `DetalleVenta` de ventas completadas |
| 10 | **Exportar a CSV** los reportes y el historial de ventas | ✅ | Módulo `csv` nativo, sin dependencias |
| 11 | Ajuste manual de inventario (merma, rotura, conteo) con motivo obligatorio | ✅ | Usa `registrar_movimiento`; solo admin |
| 12 | Hora de la venta (M5) e índices (M6) | ✅ | |
| 13 | Costo de compra y margen (M7) | ✅ | |
| 14 | Comandos de respaldo y restauración (`dumpdata`/copia de archivo) | ✅ | Requisito de la Fase 2 |
| 15 | Cierre de caja diario (total por medio de pago y por vendedor, con arqueo) | ⏳ | Depende de M5 |
| 16 | Gestión completa de usuarios (B9) | ⏳ | |
| 17 | Descuentos o promociones | ⏳ | Cambia el modelo de venta |
| 18 | Lotes y fecha de vencimiento | ⏳ | Modelo nuevo; poco valor para una botillería |
| 19 | API REST con DRF | ⏳ | **Solo si la rúbrica la exige**: el README la promete, pero el frontend actual usa plantillas Django |

### Frontend

| Prioridad | Mejora | Cabe | Notas |
|---|---|---|---|
| 1 | **Panel con indicadores** (B8): ventas de hoy ($ y N°), ticket promedio, productos con stock bajo (enlace), últimas 5 ventas | ✅ | Primera pantalla de la demo |
| 2 | Protección ante doble envío en la caja (M10) | ✅ | |
| 3 | Páginas 403, 404 y 500 propias (M12) | ✅ | |
| 4 | Librerías locales o con SRI (M11) para una demo sin internet | ✅ | |
| 5 | Gráfico simple de ventas de los últimos 7 días en el panel o los reportes | ✅ | Chart.js desde `static/` |
| 6 | Atajos en la caja: `F2` enfoca el escáner, `F9` paga, `Esc` vacía el carrito | ✅ | |
| 7 | Formato de pesos `$1.990` en todas las listas (filtro de plantilla) | ✅ | Hoy solo la caja usa `es-CL` |
| 8 | Accesibilidad: `aria-label` (B7), foco visible y colores de mensajes (B6) | ✅ | |
| 9 | Ticket imprimible con CSS `@media print` (ancho 80 mm, sin menú) | ✅ | El botón «Imprimir» ya existe |
| 10 | Marcar en el menú la sección activa (`.bnav a.on` ya existe en el CSS) | ✅ | |
| 11 | Modo oscuro | ⏳ | El CSS usa variables, pero hay muchos colores fijos |

### Detalle de la propuesta de datos compartidos (Fase 2, obligatoria)

1. **`python manage.py seed_demo`** en `usuarios/management/commands/seed_demo.py`:
   - Se niega a correr si `DEBUG=False`.
   - Es idempotente con `update_or_create` por clave natural (username, nombre de categoría, código de barras, nombre de proveedor).
   - Crea los usuarios `admin_demo` (admin) y `trabajador_demo`, con contraseñas desde `DEMO_ADMIN_PASSWORD` y `DEMO_WORKER_PASSWORD`. Solo con `DEBUG=True`, si faltan, usa un valor por defecto que se avisa en la consola **sin imprimirlo**.
   - Crea categorías (Cervezas, Vinos y Destilados como alcohólicas; Bebidas y Snacks como no alcohólicas), unos 12 productos con código EAN y uno con stock bajo, y 2 proveedores.
   - Opcionalmente (`--con-movimientos`) crea una compra y una venta de ejemplo **mediante `registrar_movimiento`**, una sola vez (las marca con un motivo fijo para no duplicarlas).
2. **Fixtures** `productos/fixtures/catalogo.json` (categorías y productos, sin usuarios) para `loaddata`.
3. **`.env.example`**: `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `DATABASE_URL`, `DEMO_ADMIN_PASSWORD`, `DEMO_WORKER_PASSWORD`, todas sin valores reales.
4. **`DATABASE_URL`** con SQLite por defecto (`sqlite:///db.sqlite3`).
5. **Respaldo**: `python manage.py dumpdata --natural-foreign --exclude contenttypes --exclude auth.permission --exclude sessions -o respaldo.json` y `loaddata respaldo.json`. Alternativa en SQLite: copiar `db.sqlite3` con el servidor detenido. Documentado en el README (y, si se quiere, un comando `respaldar`).
6. **README**: flujo de clon limpio (clonar → venv → `pip install` → `copy .env.example .env` → `migrate` → `seed_demo` → `runserver`).
7. **Prueba final**: clon limpio en una carpeta temporal, ejecutando el flujo completo y mostrando el resultado.

---

## 4. Base de datos: respuestas puntuales

- **Normalización**: está en 3FN. `Venta.total` es un dato derivado guardado a propósito (el total histórico no debe cambiar), y es correcto porque se calcula en el servidor en la misma transacción. Falta un CHECK o un test que asegure `total = Σ cantidad × precio_unitario`.
- **Al borrar** una categoría con productos, un producto con ventas, compras o movimientos, un proveedor con compras o un usuario con ventas: **se bloquea** (`PROTECT`). La app muestra un mensaje para categoría y proveedor; para producto existe la baja lógica. Borrar una compra o una venta borra sus detalles (`CASCADE`), pero **no revierte el stock**: por eso conviene bloquear ese borrado (A2).
- **¿Todo el stock pasa por `registrar_movimiento`?** En la aplicación sí: venta, anulación y compra. **No** pasan por él la creación del producto (M1) ni el admin de Django (A2).
- **SQLite y concurrencia**: SQLite tiene un solo escritor a la vez. `select_for_update` se ignora y Django abre las transacciones en modo `DEFERRED`, así que dos ventas simultáneas pueden chocar con `database is locked`. No se vende de más (CHECK + atomicidad), pero falla una de las ventas. Mitigación: `transaction_mode='IMMEDIATE'` y `timeout`, o `UPDATE` condicional (M3). En PostgreSQL el bloqueo de fila funciona tal como está escrito.
- **Paso a PostgreSQL**: `DATABASE_URL=postgres://usuario:clave@host:5432/botilleria` + `psycopg[binary]`. Los modelos no usan nada específico de SQLite. `icontains` en PostgreSQL usa `ILIKE` (sin índice; para búsquedas grandes se usaría `pg_trgm`). Respaldo con `pg_dump`/`pg_restore`.
- **Rendimiento**: los listados usan `select_related` o `prefetch_related` y están paginados. El único N+1 es el detalle de compra (B4). La lista de categorías no tiene paginación, lo que es aceptable por su tamaño.

## 5. Seguridad: respuestas puntuales

- **Escalada de privilegios**: el trabajador no puede crear usuarios ni cambiar su rol (no hay vista de edición de usuarios). El admin puede crear otros admins, lo cual es esperable. Para entrar al admin de Django se requiere `is_staff`, que la app no asigna.
- **Endpoint JSON** (`/ventas/buscar/`): exige sesión [Sonda 11] y expone solo datos que el trabajador ya ve en la lista de productos. No tiene límite de uso; es aceptable en una red interna, pero con un túnel conviene un límite por usuario.
- **Contraseñas**: los 4 validadores de Django están activos y el hash es el de Django (PBKDF2). El cambio de contraseña exige la actual y mantiene la sesión.
- **Exponer con túnel (ngrok/cloudflared)**: **no hacerlo** hasta aplicar C1, C2, A3 y A6. Mientras tanto: `DEBUG=False`, `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS` con el dominio del túnel, cookies seguras, contraseñas fuertes en las cuentas de demo, sin el admin de Django expuesto (o con una ruta no predecible) y nunca con `runserver_plus` (B11).
- **Dependencias**: Django 6.1.3, sqlparse 0.6.1, asgiref 3.13.0 y tzdata 2026.6 son versiones actuales. **No se pudo verificar** con `pip-audit` porque no está instalado; se recomienda correrlo en la Fase 2.

## 6. Historias de usuario

En el código solo se identifican HU-10 a HU-18, HU-20 y HU-21; las demás (HU-01 a HU-09, HU-19 y siguientes) **no se pueden verificar** sin el documento de HU del informe. Comparado con las funcionalidades que promete el README:

| Funcionalidad | Estado |
|---|---|
| Productos: registro, edición, baja, búsqueda | ✅ Completa |
| Ventas: escaneo, total, edad, anulación, comprobante | ✅ Completa (con lector y cámara) |
| Inventario: descuento automático, historial, alerta | ✅ Completa · ⚠️ falta la **entrada o ajuste manual** de stock |
| Compras: proveedores, registro, suma al stock | ✅ Completa · ⚠️ sin costo |
| **Reportes**: ventas por período, más y menos vendidos | ❌ **No implementado** (app vacía) |
| Usuarios: roles, login, cambio de contraseña | ✅ · ⚠️ sin edición ni desactivación, y sin tests |

## 7. Presentación y entrega

- **Riesgos en vivo**: (1) clon sin datos → usar `seed_demo`; (2) sin internet → la app pierde estilos y la cámara (M11); (3) la cámara en el teléfono exige HTTPS con un certificado autofirmado: probarla antes en el mismo teléfono y la misma red Wi-Fi; (4) firewall de Windows al abrir el puerto; (5) doble clic en Pagar (M10).
- **Guion sugerido (8-10 min)**: login como trabajador → panel → venta escaneando (lector o cámara) → intento de vender alcohol sin confirmar edad (se bloquea) → comprobante → login como admin → anular la venta (el stock vuelve, se ve en movimientos) → registrar una compra → stock bajo → reportes y exportación CSV → mostrar tests (`manage.py test`) y el flujo Git (PR de `feature/*` a `develop`).
- **Qué documentar para la rúbrica**: tabla de seguridad aplicada (roles en el servidor, CSRF, POST para acciones destructivas, ORM, hash, límite de login, cookies, secretos en `.env`), estrategia de pruebas (N° de tests por app y qué cubren), flujo Git con ramas y PR, decisiones de diseño (servicio único de stock, baja lógica, precio histórico en el detalle, enteros para CLP, `PROTECT` en historiales) y el diagrama ER real.

---

---

## 8. Estado de las correcciones (Fase 2)

Aplicadas el 19-11-2026 en `feature/aastorga` (sin ramas nuevas), un commit por corrección y los tests ejecutados después de cada una. Resultado final: **99 tests OK**, `makemigrations --check` limpio y `check --deploy` con `DEBUG=False` sin problemas.

| Hallazgo | Estado | Commit |
|---|---|---|
| C1 SECRET_KEY publicada | ✅ Se lee del `.env`; sin clave el sistema no arranca. **Cada integrante debe generar una nueva** (la publicada no se vuelve a usar). | `983fb4d` |
| C2 DEBUG / ALLOWED_HOSTS fijos | ✅ Desde `.env`, con `DEBUG=False` por defecto | `983fb4d` |
| A1 Servicio de stock sin validar | ✅ Valida tipo, cantidad y motivo | `03ef9fe` |
| A2 Admin de Django salta el stock | ✅ Solo lectura para movimientos, compras y ventas; stock de solo lectura | `aaa0b79` |
| A3 Sin límite de login | ✅ 5 intentos por usuario / 20 por IP, bloqueo de 15 min, registrado | `8839f35` |
| A4 Error 500 en la caja | ✅ Tope de 999 por producto y conversión segura | `f3998c5` |
| A5 Sin tests de usuarios | ✅ 25 tests en `usuarios` | `5d1e5c5` y siguientes |
| A6 Cookies y sesión | ✅ Sesión de 8 h; cookies seguras, HSTS y SSL con `DEBUG=False` | `386cccb` |
| M1 Stock inicial sin movimiento | ✅ | `84b364c` |
| M2 Auditoría por usuario | ✅ Usuario en movimientos y compras; quién, cuándo y por qué en anulaciones | `ae58dfa`, `2826dc4`, `3bcecd9` |
| M3 Concurrencia en SQLite | ✅ `transaction_mode=IMMEDIATE` y `timeout` | `983fb4d` |
| M4 CheckConstraints | ✅ Precio ≥ 1 y cantidades ≥ 1 en la BD | `4d30cac` |
| M5 Hora de la venta | ✅ `creada_en` (las ventas antiguas quedan a las 00:00 de su fecha) | `d3ecbc6`, `fbbf494` |
| M6 Índices | ✅ | `f073499` |
| M7 Costo de compra | ⏸ Pendiente (no incluido en esta fase) | — |
| M8 DATABASE_URL | ✅ | `983fb4d` |
| M9 Datos compartidos | ✅ `seed_demo`, fixture `catalogo`, comando `respaldar` | `0f19d8e`, `729a275`, `278d3d8` |
| M10 Doble envío | ✅ Botón deshabilitado + token de un solo uso | `b604dbd` |
| M11 CDN sin SRI | ✅ `integrity` en Bootstrap, íconos y `html5-qrcode` | `0b530f5` |
| M12 Páginas de error y logging | ✅ 403/404/500 propias y `logs/seguridad.log` | `736d23e` |
| M13 README desactualizado | ✅ | `8e4a906` |
| M14 Reportes | ✅ Por período, medio de pago, vendedor, más y menos vendidos, CSV | `925989c` |
| B1–B3 settings y requirements | ✅ | `4fc9aa9`, `983fb4d`, `386cccb` |
| B4 N+1 en detalle de compra | ✅ | `2826dc4` |
| B5–B7 Paginación, mensajes, aria-label | ✅ | `43fea89` |
| B8 Panel vacío | ✅ Indicadores del día | `142ab47` |
| B9 Gestión de usuarios | ⏸ Pendiente | — |
| B10 Datos del proveedor | ⏸ Pendiente | — |
| B11 Depurador de runserver_plus | ✅ Documentado en el README | `8e4a906` |
| Clon limpio (prueba final) | ✅ Se encontró y corrigió que `DATABASE_URL=` vacío (como en `.env.example`) rompía el arranque | `10ebb16` |

Otras mejoras de la lista: refactor de la venta a un servicio (`89b03f6`), la caja conserva el carrito si se rechaza la venta (`cdfc551`, error encontrado durante la Fase 2), formato `$1.990` (`f8877aa`) y ajuste manual de inventario (`67b5f2d`).

**Pendientes recomendados**: costo de compra y margen (M7), editar y desactivar usuarios (B9), RUT y contacto del proveedor (B10), cierre de caja diario, y ejecutar `pip-audit` y `coverage` (no estaban instalados).
