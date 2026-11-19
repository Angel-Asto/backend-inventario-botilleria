<p align="center">
  <img src="assets/banner.svg" alt="Backend – Sistema de Inventario y Ventas" width="100%">
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/Django-6.1-092E20?style=for-the-badge&logo=django&logoColor=white" alt="Django 6.1">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-7952B3?style=for-the-badge&logo=bootstrap&logoColor=white" alt="Bootstrap 5.3">
  <img src="https://img.shields.io/badge/SQLite-desarrollo-003B57?style=for-the-badge&logo=sqlite&logoColor=white" alt="SQLite">
  <img src="https://img.shields.io/badge/PostgreSQL-producci%C3%B3n-4169E1?style=for-the-badge&logo=postgresql&logoColor=white" alt="PostgreSQL">
  <img src="https://img.shields.io/badge/Pruebas-99%20OK-15803D?style=for-the-badge" alt="99 pruebas">
</p>

<p align="center">
  Sistema de inventario y ventas para una botillería pequeña: caja con lector de código de barras o cámara del celular, control de stock, compras, reportes y roles.
</p>

---

## Contenido

[Sobre el proyecto](#sobre-el-proyecto) · [Arquitectura](#arquitectura) · [Modelo de datos](#modelo-de-datos) · [Tecnologías](#tecnologías) · [Estructura](#estructura-del-proyecto) · [Instalación](#instalación-clon-limpio) · [Datos de demo](#datos-de-demostración) · [Respaldo](#respaldo-y-restauración) · [Seguridad](#seguridad) · [Pruebas](#pruebas) · [Flujo de trabajo](#flujo-de-trabajo-en-git) · [Hoja de ruta](#hoja-de-ruta) · [Equipo](#equipo)

---

## Sobre el proyecto

El sistema reemplaza el control manual del inventario de una botillería. Las pantallas se generan con plantillas de Django y Bootstrap 5 (el prototipo visual está en el repositorio [`SistemaBotelleria`](https://github.com/Angel-Asto/SistemaBotelleria)).

| Funcionalidad | Descripción | HU |
|---|---|---|
| **Usuarios** | Roles Admin y Trabajador, inicio de sesión con bloqueo por intentos fallidos, cambio de contraseña | |
| **Productos** | Registro, edición, baja lógica, búsqueda por código, nombre o categoría; escaneo con la cámara | |
| **Ventas** | Caja con lector o cámara, total automático, medio de pago, confirmación de edad en alcohol, comprobante, anulación con motivo | HU-13 a HU-18 |
| **Inventario** | Stock actual con alerta de stock bajo, historial de movimientos con usuario, ajuste manual (mermas) | HU-10 a HU-12 |
| **Compras** | Proveedores y registro de compras que suman stock | HU-20, HU-21 |
| **Reportes** | Ventas por período, medio de pago y vendedor; productos más y menos vendidos; exportación a CSV | |
| **Panel** | Ventas del día, ticket promedio, stock bajo y últimas ventas | |

## Arquitectura

```mermaid
flowchart LR
    A["Navegador / celular<br/>Bootstrap 5 · lector o cámara"] -->|HTTP| B["Django 6.1<br/>vistas y plantillas"]
    B --> S["Servicios<br/>registrar_movimiento · registrar_venta"]
    S --> D[("Base de datos<br/>SQLite / PostgreSQL")]
    B --> D
```

Todo cambio de stock pasa por un único servicio (`inventario/servicios.py → registrar_movimiento`): actualiza el producto dentro de una transacción y deja un movimiento con su usuario. Ventas, anulaciones, compras, stock inicial y ajustes lo usan; el admin de Django queda en solo lectura para no saltárselo.

## Modelo de datos

```mermaid
erDiagram
    CATEGORIA ||--o{ PRODUCTO : clasifica
    PRODUCTO ||--o{ MOVIMIENTO_STOCK : genera
    USUARIO ||--o{ MOVIMIENTO_STOCK : registra
    PROVEEDOR ||--o{ COMPRA : abastece
    USUARIO ||--o{ COMPRA : registra
    COMPRA ||--|{ DETALLE_COMPRA : contiene
    PRODUCTO ||--o{ DETALLE_COMPRA : se_compra_en
    USUARIO ||--o{ VENTA : vende
    USUARIO ||--o{ VENTA : anula
    VENTA ||--|{ DETALLE_VENTA : contiene
    PRODUCTO ||--o{ DETALLE_VENTA : se_vende_en

    CATEGORIA {
        string nombre UK
        bool es_alcoholica
    }
    PRODUCTO {
        string codigo_barras UK
        string nombre
        int precio
        int stock
        int stock_minimo
        bool activo
    }
    MOVIMIENTO_STOCK {
        datetime fecha
        string tipo
        int cantidad
        string motivo
    }
    VENTA {
        date fecha
        datetime creada_en
        string medio_pago
        int total
        string estado
        string motivo_anulacion
    }
    DETALLE_VENTA {
        int cantidad
        int precio_unitario
    }
    COMPRA {
        date fecha
    }
    DETALLE_COMPRA {
        int cantidad
    }
```

Decisiones de diseño:

- **Pesos en enteros**: el peso chileno no tiene decimales; no hay errores de redondeo.
- **Precio histórico**: cada detalle de venta guarda el precio del momento, así un cambio de precio no altera ventas pasadas.
- **Baja lógica**: los productos se desactivan, no se borran; categorías, productos, proveedores y usuarios con historial están protegidos (`PROTECT`).
- **Reglas en la base de datos**: precio ≥ 1 y cantidades ≥ 1 (`CheckConstraint`), stock nunca negativo, índices por fecha para listados y reportes.

## Tecnologías

| Componente | Tecnología |
|---|---|
| Lenguaje | Python 3.14 |
| Framework | Django 6.1 (patrón MTV, equivalente a MVC) |
| Interfaz | Plantillas de Django, Bootstrap 5.3, Bootstrap Icons, `html5-qrcode` (cámara) |
| Base de datos | SQLite en desarrollo, PostgreSQL en producción (`DATABASE_URL`) |
| Configuración | `python-dotenv` (`.env`) y `dj-database-url` |
| Control de versiones | Git y GitHub |

## Estructura del proyecto

```text
backend-inventario-botilleria/
├── config/            # settings (lee el .env), urls
├── usuarios/          # Usuario con rol, login, panel, comandos seed_demo y respaldar
├── productos/         # Producto, Categoría, fixture del catálogo, filtro |pesos
├── inventario/        # MovimientoStock, servicio de stock, ajuste manual
├── compras/           # Proveedor, Compra y DetalleCompra
├── ventas/            # Venta, DetalleVenta, servicio de venta, caja y comprobante
├── reportes/          # Reportes y exportación a CSV
├── templates/         # HTML (incluye páginas 403/404/500)
├── static/            # CSS y JS (escáner con cámara)
├── docs/              # Informe de auditoría
├── requirements.txt / requirements-dev.txt
├── .env.example
└── manage.py
```

## Instalación (clon limpio)

```bash
git clone https://github.com/Angel-Asto/backend-inventario-botilleria.git
cd backend-inventario-botilleria
python -m venv venv
venv\Scripts\activate                 # Windows  (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
copy .env.example .env                # Linux/Mac: cp .env.example .env
```

Edita el `.env`:

1. Genera una `SECRET_KEY` propia y pégala:

   ```bash
   python -c "from django.core.management.utils import get_random_secret_key as g; print(g())"
   ```

2. Deja `DEBUG=True` para desarrollo y define `DEMO_ADMIN_PASSWORD` y `DEMO_WORKER_PASSWORD`.

Luego:

```bash
python manage.py migrate
python manage.py seed_demo
python manage.py runserver
```

Abre `http://127.0.0.1:8000/` e inicia sesión con `admin_demo` o `trabajador_demo` y las contraseñas que pusiste en el `.env`.

> [!IMPORTANT]
> Sin `.env` el sistema no arranca (falta `SECRET_KEY`) y queda con `DEBUG=False` por seguridad. El `.env` nunca se sube al repositorio.

<details>
<summary><b>Usar la cámara del celular en la caja (HTTPS local)</b></summary>

<br>

El navegador del celular solo permite la cámara con HTTPS. Para desarrollo:

```bash
pip install -r requirements-dev.txt
python manage.py runserver_plus 0.0.0.0:8443 --cert-file certs/local.crt
```

Agrega la IP del PC a `ALLOWED_HOSTS` y `https://<IP>:8443` a `CSRF_TRUSTED_ORIGINS` en el `.env`, y abre `https://<IP>:8443` en el celular (acepta el aviso del certificado). El servidor de desarrollo trae un depurador: **no lo uses con un túnel público**.

</details>

<details>
<summary><b>Pasar a PostgreSQL</b></summary>

<br>

```bash
pip install "psycopg[binary]"
```

En el `.env`: `DATABASE_URL=postgres://usuario:clave@localhost:5432/botilleria`, y luego `python manage.py migrate`. No hay que cambiar código.

</details>

## Datos de demostración

`python manage.py seed_demo` deja a todo el equipo con los mismos datos:

- Usuarios `admin_demo` (Admin) y `trabajador_demo` (Trabajador), con las contraseñas del `.env`.
- 5 categorías (Cervezas, Vinos y Destilados piden confirmar edad) y 12 productos con códigos EAN-13 válidos.
- Stock inicial cargado como movimientos; algunos productos quedan bajo el mínimo para ver la alerta.
- 2 proveedores, una compra y una venta de ejemplo.

Se puede correr varias veces sin duplicar nada (`--solo-catalogo` omite la compra y la venta). Solo funciona con `DEBUG=True`. El catálogo también está como fixture: `python manage.py loaddata catalogo` (sin usuarios ni contraseñas, con stock 0).

## Respaldo y restauración

```bash
python manage.py respaldar                                  # crea respaldos/respaldo_AAAAMMDD_HHMMSS.json
python manage.py loaddata respaldos/respaldo_<fecha>.json   # restaura sobre una base ya migrada
```

Con SQLite también basta copiar `db.sqlite3` con el servidor detenido; con PostgreSQL se usa `pg_dump`/`pg_restore`. Los respaldos incluyen los hashes de contraseñas: la carpeta `respaldos/` no se sube a git.

## Seguridad

| Medida | Cómo se aplica |
|---|---|
| Secretos y configuración | `SECRET_KEY`, `DEBUG`, hosts y base de datos en `.env` (no se sube); sin `.env`, `DEBUG=False` |
| Contraseñas | Hash de Django (PBKDF2) y validadores de largo, similitud, comunes y numéricas |
| Fuerza bruta | Bloqueo de 15 min tras 5 intentos fallidos por usuario o 20 por IP; queda registrado |
| Roles | Admin y Trabajador validados **en el servidor** en cada vista (403 si no corresponde) |
| Datos de otros usuarios | El trabajador solo ve sus ventas (sin acceso por cambiar el N° en la URL) |
| Acciones destructivas | Solo por POST con token CSRF; anular una venta exige motivo |
| Doble envío | Token de un solo uso en la caja: un doble clic no crea dos ventas |
| Consultas | ORM de Django (parametrizado), sin SQL armado a mano |
| XSS | Escapado automático de plantillas; el JS usa `textContent` y `json_script` |
| Sesión y cookies | 8 horas, se cierra con el navegador, `HttpOnly`, `SameSite`; con `DEBUG=False`: cookies `Secure`, HSTS y redirección a HTTPS |
| Librerías externas | CDN con verificación de integridad (SRI) |
| CSV | Celdas que parecen fórmulas se neutralizan al exportar |
| Auditoría | Cada movimiento de stock y compra guarda el usuario; la anulación guarda quién, cuándo y por qué; `logs/seguridad.log` registra logins fallidos y bloqueos |
| Errores | Páginas 403/404/500 propias, sin información interna |

`python manage.py check --deploy` con `DEBUG=False` no reporta problemas. El detalle de la revisión está en [`docs/AUDITORIA.md`](docs/AUDITORIA.md).

## Pruebas

```bash
python manage.py test
```

99 pruebas automáticas: usuarios, seguridad del login y configuración (25), productos (15), inventario (17), compras (10), ventas (27) y reportes (5). Cubren permisos por rol, cálculo de totales, stock justo e insuficiente, transacciones que no quedan a medias, doble envío, datos inválidos, reglas en la base de datos, idempotencia de `seed_demo` y respaldo/restauración.

## Flujo de trabajo en Git

```mermaid
gitGraph
    commit id: "README"
    branch develop
    checkout develop
    branch "feature/aastorga"
    commit id: "usuarios"
    checkout develop
    merge "feature/aastorga" id: "PR aprobado"
    checkout main
    merge develop id: "Versión 1"
```

- `main`: versión estable, solo recibe cambios desde `develop` mediante Pull Request.
- `develop`: rama de integración y pruebas.
- `feature/<inicial><apellido>`: rama personal de cada integrante, creada desde `develop`.

> [!IMPORTANT]
> No hay commits directos en `main` ni en `develop`. Cada commit es un solo cambio, con mensaje `tipo: descripción` en español.

## Hoja de ruta

- [x] Repositorio, README y ramas
- [x] Proyecto Django y configuración segura por `.env`
- [x] Modelos, migraciones y reglas en la base de datos
- [x] Autenticación, roles y bloqueo de intentos
- [x] Productos, inventario, compras y ventas (caja con lector y cámara)
- [x] Reportes y exportación a CSV
- [x] Pruebas automáticas
- [ ] Cierre de caja diario
- [ ] Despliegue (PostgreSQL + HTTPS)

## Equipo

| Integrante | GitHub | Rama | Apps a cargo |
|---|---|---|---|
| **Angel Astorga** | [@Angel-Asto](https://github.com/Angel-Asto) | `feature/aastorga` | `usuarios`, `inventario`, `compras`, `reportes` |
| **Kinerett Castillo** | [@kinekay](https://github.com/kinekay) | `feature/kcastillo` | `productos`, `ventas` |

<p align="center">
  <sub>Proyecto Integrado – TIHI43 · INACAP Sede Arica · Docente: Valery Rodríguez</sub>
</p>
