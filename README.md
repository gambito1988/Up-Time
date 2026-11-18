# Up Time

Sitio de servicio técnico (Flask + PostgreSQL) con cuentas de clientes, membresías pagas con Mercado Pago y un panel privado.

## Base de datos

La aplicación usa **PostgreSQL** (Supabase). Define `DATABASE_URL` con la cadena **Session pooler** de Supabase (puerto `5432`, con `sslmode=require`); Render opera sobre IPv4 y la conexión directa de Supabase requiere IPv6. No subas la cadena a Git.

El esquema se crea y actualiza solo al recibir la primera petición, y activa Row Level Security en todas las tablas.

Hay un andamiaje de Alembic preparado en `migrations/` para el día que haga falta un cambio de esquema más complejo que agregar una columna, pero todavía no está en uso: ver [migrations/README.md](migrations/README.md).

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

## Backups de la base de datos

`.github/workflows/backup.yml` corre todos los días a las 03:00 (ART) y sube un `pg_dump` cifrado a un bucket de Cloudflare R2. Los domingos, además, guarda una copia en `weekly/`. La retención (14 diarios, 8 semanales) la aplican reglas de expiración del propio bucket, que el workflow re-declara en cada corrida.

El cifrado es con [age](https://github.com/FiloSottile/age): el CI solo conoce la **clave pública**, nunca la privada, así que aunque se filtraran los secrets de GitHub no se podría leer un backup viejo.

### Configuración inicial (una sola vez)

1. Generar el par de claves **en tu máquina, no en el CI**:
   ```bash
   age-keygen -o backup-key.txt
   ```
   Guardá `backup-key.txt` (la clave privada) en un lugar seguro fuera del repo (gestor de contraseñas, caja fuerte, etc.). Si se pierde, los backups viejos quedan irrecuperables.

2. Crear un bucket en Cloudflare R2 (ej. `up-time-backups`) y un API token con permiso de lectura/escritura solo sobre ese bucket.

3. Cargar estos **GitHub Secrets** en el repo (Settings → Secrets and variables → Actions):

   | Secret | Valor |
   |---|---|
   | `DATABASE_URL` | cadena de conexión de solo lectura/uso del dump (misma que usa la app) |
   | `BACKUP_AGE_PUBLIC_KEY` | la línea `public key:` que imprimió `age-keygen` |
   | `R2_ACCOUNT_ID` | ID de cuenta de Cloudflare |
   | `R2_ACCESS_KEY_ID` / `R2_SECRET_ACCESS_KEY` | credenciales del API token de R2 |
   | `R2_BUCKET` | nombre del bucket |

### Restaurar un backup

1. Bajar el archivo cifrado del bucket (consola de Cloudflare R2, o `aws s3 cp` con las mismas credenciales apuntando al endpoint `https://<R2_ACCOUNT_ID>.r2.cloudflarestorage.com`).
2. Desencriptar con la clave privada que generaste en el paso 1 de arriba:
   ```bash
   age -d -i backup-key.txt -o backup.dump backup-2026-11-18.dump.age
   ```
3. Restaurar **contra una base de prueba**, nunca directo a producción:
   ```bash
   pg_restore --no-owner --clean --if-exists -d "$TEST_DATABASE_URL" backup.dump
   ```
4. Si todo se ve bien ahí, recién entonces considerar restaurar sobre producción (y avisar al equipo antes de hacerlo).

## Herramientas para Claude Code

Consulta [docs/herramientas-claude-code.md](docs/herramientas-claude-code.md) para instalar Graphify, claude-mem, Headroom, OmniRoute, claude-code-setup y task-observer.

`package.json`, `package-lock.json` y `skills-lock.json` son del skill de Supabase instalado para Claude Code (`.agents/skills/supabase-server`), no de la aplicación Flask: esta app no usa Node ni el paquete `@supabase/server`, solo `psycopg` contra `DATABASE_URL`. `render.yaml` no corre `npm install`, así que no afectan el deploy. Se mantienen porque dan contexto útil a Claude en este repo.

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
