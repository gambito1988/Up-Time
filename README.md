# Up Time

Sitio de servicio técnico (Flask + PostgreSQL) con cuentas de clientes, membresías pagas con Mercado Pago y un panel privado.

## Base de datos

La aplicación usa **PostgreSQL** (Supabase). Define `DATABASE_URL` con la cadena **Session pooler** de Supabase (puerto `5432`, con `sslmode=require`); Render opera sobre IPv4 y la conexión directa de Supabase requiere IPv6. No subas la cadena a Git.

El esquema se crea y actualiza solo al recibir la primera petición, y activa Row Level Security en todas las tablas.

## Desarrollo local

```powershell
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://..."   # una base de desarrollo, no la de producción
$env:SECRET_KEY = "cualquier-valor-largo"
$env:ADMIN_USERNAME = "admin"; $env:ADMIN_PASSWORD = "clave"
$env:FLASK_DEBUG = "1"; python app.py
```

Las variables disponibles están en `.env.example`. En Render, `SECRET_KEY` y `DATABASE_URL` son obligatorias: sin ellas la aplicación no arranca.

## Mercado Pago

Configura `MERCADOPAGO_ACCESS_TOKEN` y, en el panel de Mercado Pago (Webhooks), la URL `https://<tu-dominio>/pagos/mercado-pago/webhook`. Copia la clave secreta del webhook en `MERCADOPAGO_WEBHOOK_SECRET` para que se verifique la firma de cada notificación.

## Herramientas para Claude Code

Consulta [docs/herramientas-claude-code.md](docs/herramientas-claude-code.md) para instalar Graphify, claude-mem, Headroom, OmniRoute, claude-code-setup y task-observer.

## Pruebas

```powershell
pip install -r requirements-dev.txt
python -m pytest tests
```

Sin más configuración corren las pruebas unitarias (páginas, seguridad, firma del webhook y lógica de pagos con una base simulada). Las de integración (`tests/test_integration.py`: registro, confirmación de email, login, recuperación de contraseña, panel de administración y membresías) usan PostgreSQL real y se saltan si no defines una base de pruebas:

```powershell
$env:TEST_DATABASE_URL = "postgresql://postgres:clave@localhost:5432/uptime_test"
python -m pytest tests
```

**Vacían las tablas** al empezar cada prueba, por eso solo se ejecutan si el nombre de la base contiene `test`.

## Membresías

Cada pago aprobado suma 30 días de vigencia (`MEMBERSHIP_DAYS` en `app.py`); renovar antes del vencimiento suma sobre los días que quedan. Al vencer, la cuenta muestra "Vencida" y ofrece renovar. No hay cobro recurrente automático: el cliente paga cada período.

En producción el webhook de Mercado Pago exige `MERCADOPAGO_WEBHOOK_SECRET` y rechaza las notificaciones si falta.

## Cuentas de clientes cargadas por el administrador

En el panel privado el admin puede cargar el email del cliente junto con el servicio. Cuando ese cliente se registra con **el mismo nombre y el mismo email**, no se crea un usuario nuevo: recibe un enlace (válido 1 hora) para elegir su contraseña, y al activarla ve el historial que ya tenía. La contraseña nunca se fija en el registro, así nadie puede apropiarse de la cuenta de otro escribiendo su email.

Nombre de usuario y email son únicos sin distinguir mayúsculas. Un nombre cargado sin email no se puede reclamar: hay que agregar el email desde el panel (cargando otro servicio con el mismo nombre y el email).

## Formulario de contacto

`POST /contacto` guarda cada mensaje en la tabla `contact_messages` y después redirige a WhatsApp, como antes. Si la base falla, igual redirige: el visitante no pierde el contacto. Valida el email, limita el largo de los campos y descarta los envíos que completan el campo señuelo `website`.

Si defines `CONTACT_NOTIFY_EMAIL` (y el SMTP), cada mensaje nuevo se avisa por email a esa dirección, en segundo plano. Los mensajes se leen en el panel privado, en **Mensajes de contacto**, donde se marcan como Nuevo, Respondido o Cerrado.
