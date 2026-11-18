# Backups de la base

Backup diario de la base de Supabase (esquema `public`) hacia Cloudflare R2, **cifrado con age**.
Lo ejecuta `.github/workflows/db-backup.yml` todos los dias a las 03:17 (hora de Argentina) y se
puede lanzar a mano desde GitHub → Actions → "Backup de la base" → Run workflow.

> El repositorio es publico. El dump contiene datos de clientes y pagos, por eso **nunca** se sube
> como artifact de GitHub ni se commitea. Solo sale cifrado hacia un bucket privado.

Se conservan los ultimos 30 dias (`RETENTION_DAYS` en el workflow).

## Configuracion inicial (una sola vez)

### 1. Bucket en Cloudflare R2
1. Cloudflare → R2 → Create bucket (por ejemplo `up-time-backups`). Dejalo **privado**.
2. R2 → Manage API tokens → Create API token con permiso **Object Read & Write** limitado a ese bucket.
3. Anota: Account ID, Access Key ID y Secret Access Key (el secret se muestra una sola vez).

### 2. Clave de cifrado (age)
En tu PC:
```
age-keygen -o up-time-backup.key
```
- La linea `# public key: age1...` es la clave **publica**: va a GitHub.
- El archivo `up-time-backup.key` es la clave **privada**: guardala fuera del repo y en dos lugares
  (por ejemplo, gestor de contrasenas y un pendrive). **Si la perdes, los backups no se pueden abrir.**

### 3. Secretos en GitHub
Repo → Settings → Secrets and variables → Actions → New repository secret:

| Secreto | Valor |
|---|---|
| `DATABASE_URL` | La misma URL del pooler de Supabase que usa Render |
| `BACKUP_AGE_PUBLIC_KEY` | La clave publica `age1...` |
| `R2_ACCOUNT_ID` | Account ID de Cloudflare |
| `R2_ACCESS_KEY_ID` | Access Key del token de R2 |
| `R2_SECRET_ACCESS_KEY` | Secret del token de R2 |
| `R2_BUCKET` | Nombre del bucket |

Usa la URL del **pooler** (`...pooler.supabase.com`), no la conexion directa: la directa de Supabase
es solo IPv6 y los runners de GitHub no la alcanzan.

### 4. Primera prueba
Lanza el workflow a mano y confirma que termina en verde y que aparece un archivo
`db-backups/backup-<fecha>.dump.age` en el bucket.

Los workflows programados solo corren desde la rama por defecto (`main`): hasta que este cambio
no este mergeado, solo funciona el lanzamiento manual.

## Restaurar un backup

1. Descarga el archivo `.dump.age` desde el bucket de R2 (panel de Cloudflare o `aws s3 cp` con el endpoint de R2).
2. Descifralo con la clave privada:
   ```
   age -d -i up-time-backup.key -o backup.dump backup-<fecha>.dump.age
   ```
3. Restaura **primero en una base de prueba**, nunca directo sobre produccion:
   ```
   pg_restore --no-owner --no-acl --clean --if-exists -d "postgresql://USUARIO:CLAVE@HOST:5432/BASE_DE_PRUEBA" backup.dump
   ```
   Necesitas `pg_restore` version 17 o superior (la base de Supabase es PostgreSQL 17).
4. Revisa que las tablas y los datos esten completos antes de apuntar la app a esa base.

`--clean --if-exists` borra y recrea los objetos del esquema `public` en la base destino. No lo
corras contra una base con datos que quieras conservar.

## Limitaciones conocidas

- Los workflows programados de un repo publico se **desactivan tras 60 dias sin actividad** en el
  repositorio. GitHub avisa por mail antes. Si pasa, reactivalo en Actions.
- Si el workflow falla, GitHub envia un mail al dueño del repo, pero conviene mirar de vez en
  cuando que haya un backup reciente en el bucket.
- El backup cubre solo el esquema `public`. Los usuarios de Supabase Auth (`auth`) no se incluyen,
  porque la app no los usa (maneja sus propias cuentas en tablas de `public`).
- Un backup en el mismo ecosistema (Cloudflare) no reemplaza probar la restauracion: hacelo al
  menos una vez, y repetilo cada tanto.
