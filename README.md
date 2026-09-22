# Up Time

## Migración a Supabase PostgreSQL

1. Crea un proyecto en Supabase y copia la cadena de conexión **Session pooler** de PostgreSQL (puerto `5432`, incluye `sslmode=require`). Render opera sobre IPv4 y la conexión directa de Supabase requiere IPv6 salvo que se contrate su add-on IPv4.
2. En Render, agrega `DATABASE_URL` en el servicio web con esa cadena. No la subas a Git.
3. Desde una terminal con acceso a la base de Supabase, ejecuta primero la simulación:

   ```powershell
   $env:DATABASE_URL = "postgresql://..."
   python scripts/migrate_sqlite_to_postgres.py
   ```

4. Si los conteos son correctos, realiza la copia:

   ```powershell
   python scripts/migrate_sqlite_to_postgres.py --apply
   ```

5. Recién entonces despliega el cambio en Render. La aplicación crea y actualiza el esquema al iniciar.

Conserva `uptime.db` como respaldo hasta verificar usuarios, servicios y pagos en producción.
