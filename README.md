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

Las pruebas no necesitan una base de datos real: `tests/conftest.py` usa una cadena PostgreSQL ficticia y las consultas de pagos se simulan. Los flujos que sí tocan la base (registro, confirmación de email, login, panel de administración) todavía no tienen cobertura automatizada.
