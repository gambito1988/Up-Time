# Alembic (preparado, todavía no en uso)

**Estado actual: solo andamiaje.** La app sigue arrancando igual que siempre —
`init_db()` en `app.py` crea y actualiza el esquema en la primera petición,
como desde el principio. Nada de esto se corre en producción todavía.

Esto existe para tener listo el paso a migraciones versionadas el día que se
decida hacerlo de verdad, sin tener que armar nada desde cero en ese momento.

## Por qué está esto acá

`init_db()` funciona bien para agregar columnas, pero no alcanza para un
cambio de esquema más complejo (renombrar una columna, migrar datos a otra
estructura, etc.), y no deja un historial ordenado de qué cambió y cuándo.
Alembic resuelve eso: cada cambio es un archivo con `upgrade()` y
`downgrade()`, y la propia base guarda en qué versión está.

## Probarlo en desarrollo (no toca producción)

```powershell
pip install -r requirements-dev.txt   # ya incluye alembic y SQLAlchemy
$env:DATABASE_URL = "postgresql://usuario:clave@localhost:5432/una_base_de_prueba"
python -m alembic upgrade head
```

Esto crea el esquema completo desde cero en esa base. Para ver el SQL sin
ejecutarlo contra ninguna base real:

```powershell
python -m alembic upgrade head --sql
```

## Cómo cortar de verdad (cuando se decida)

**No corras `alembic upgrade head` contra la base de producción tal cual**:
las tablas ya existen (las creó `init_db()`), y aunque la migración usa
`IF NOT EXISTS` y no rompería nada, Alembic no sabría que ya estás al día.
El paso correcto:

1. **Marcar la base de producción como ya actualizada**, sin ejecutar nada:
   ```
   alembic stamp 4d623f7a3ab9
   ```
   Esto solo escribe en la tabla `alembic_version` que la base ya tiene el
   esquema de la migración baseline — no toca ninguna tabla.
2. **Sacar la creación/actualización de esquema de `init_db()`** (dejarla solo
   para lo que no es esquema, si queda algo), o quitar `init_db()` del
   arranque directamente.
3. **Cambiar el `startCommand` en `render.yaml`** para correr las migraciones
   antes de levantar el servidor, por ejemplo:
   ```yaml
   startCommand: alembic upgrade head && gunicorn --bind 0.0.0.0:$PORT app:app
   ```
4. De ahí en adelante, cada cambio de esquema es una migración nueva:
   ```
   alembic revision -m "agregar tabla de x"
   ```
   escribiendo `upgrade()`/`downgrade()` a mano (no hay modelos de SQLAlchemy
   en este proyecto — la app usa `psycopg` con SQL directo, así que no hay
   `autogenerate`).

## Migraciones

- `4d623f7a3ab9_baseline_esquema_actual.py` — transcribe el esquema que hoy
  crea `init_db()` (al 2026-09-29): las 4 tablas, los índices, y RLS
  habilitado. Es el punto de partida; no se ejecuta contra producción, se
  usa para `stamp` cuando llegue el momento del corte real.
