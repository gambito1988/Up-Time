# AGENTS.md

Guía para agentes de IA que trabajen en este repositorio.

## Qué es este proyecto

Up Time: sitio de servicio técnico de PCs (CABA, Argentina). Flask + PostgreSQL (Supabase), membresías pagas con Mercado Pago, panel privado de administración, y avisos por email vía n8n. Desplegado en Render.

## Stack y estructura

- **`app.py`**: toda la aplicación Flask en un solo archivo (rutas, lógica de negocio, acceso a datos). No hay ORM: consultas SQL directas con `psycopg` (v3) contra `DATABASE_URL`.
- **`templates/`**: Jinja2, HTML servido por Flask (cuentas, membresías, panel admin, legales).
- **`index.html`, `styles.css`, `favicon.svg`**: landing estática servida aparte del resto de la app.
- **`tests/`**: `test_app.py` (unitarias, sin base real) y `test_integration.py` (con PostgreSQL real, se saltan si no hay `TEST_DATABASE_URL`).
- **`migrations/`**: andamiaje de Alembic preparado pero **no activo**; el esquema real se crea/actualiza solo vía `init_db()` en `app.py` (`ALTER TABLE ... ADD COLUMN IF NOT EXISTS`, migraciones ad-hoc). No asumas que Alembic corre en producción.
- **`render.yaml`**: infraestructura como código para Render (web service + Redis/Key Value para rate limiting).
- **`.github/workflows/tests.yml`**: CI que corre pytest (unitarias + integración con Postgres de servicio) en cada push/PR a `main`.

## Cómo correr y probar localmente

```powershell
pip install -r requirements.txt
$env:DATABASE_URL = "postgresql://..."   # una base de desarrollo, nunca la de produccion
$env:SECRET_KEY = "cualquier-valor-largo"
$env:ADMIN_USERNAME = "admin"; $env:ADMIN_PASSWORD = "clave"
$env:FLASK_DEBUG = "1"; python app.py
```

```powershell
pip install -r requirements-dev.txt
python -m pytest tests                     # unitarias, siempre corren
$env:TEST_DATABASE_URL = "postgresql://postgres:clave@localhost:5432/uptime_test"
python -m pytest tests                     # + integracion (requiere que el nombre de la base contenga "test": vacia tablas)
```

Ver `.env.example` para todas las variables disponibles. En Render, `SECRET_KEY` y `DATABASE_URL` son obligatorias.

## Convenciones importantes

- Todo cambio de esquema va en `init_db()` (`app.py`), con `IF NOT EXISTS` — no en migraciones sueltas de Alembic salvo que se decida cortar el corte real (ver `migrations/README.md`).
- Las contraseñas de administrador y de cliente nunca se fijan en el registro cuando el admin cargó la cuenta antes: el cliente la reclama con nombre + email exactos.
- Usuario/email son únicos sin distinguir mayúsculas.
- El webhook de Mercado Pago (`/pagos/mercado-pago/webhook`) verifica firma HMAC (`x-signature`) con `MERCADOPAGO_WEBHOOK_SECRET`; en producción rechaza si falta la clave. El manifest a firmar necesita el `id` del pago con el mismo fallback que usa `payment_id` (ver `mercado_pago_webhook()`), porque el evento "Pagos (legacy)" manda el id como `?id=` en vez de `data.id`.
- Los pagos se validan server-side contra `MEMBERSHIP_PLANS` (precio/moneda), nunca se confía en lo que manda el cliente.
- Antes de tocar `MEMBERSHIP_PLANS` (precios/beneficios), revisar `tests/test_integration.py`: varios tests de checkout/historial de pagos tienen los montos hardcodeados y hay que actualizarlos en el mismo cambio.
- Si `graphify-out/graph.json` existe, hay instrucciones específicas para Claude Code en `CLAUDE.md` y `.claude/CLAUDE.md` sobre usarlo para explorar el código en vez de grep crudo.

## Al terminar un cambio

- Correr `python -m pytest tests` (con `TEST_DATABASE_URL` si el cambio toca lógica de datos).
- Si el cambio afecta el esquema, actualizar `init_db()` y, si aplica, `migrations/versions/`.
- No hacer merge/push a `main` sin que el usuario lo pida explícitamente.
