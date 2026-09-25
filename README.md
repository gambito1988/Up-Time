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

## Grafo de conocimiento con Graphify (opcional)

[Graphify](https://github.com/Graphify-Labs/graphify) analiza el código localmente (sin LLM ni API key) y genera un grafo que Claude Code puede consultar en lugar de releer archivos completos.

1. Instala la CLI (requiere Python 3.10+; el paquete se escribe con doble "y"):

   ```bash
   uv tool install graphifyy   # o: pipx install graphifyy
   ```

2. Registra la skill `/graphify` en Claude Code para este proyecto:

   ```bash
   graphify install --project --platform claude
   ```

3. Genera el grafo y, opcionalmente, mantenlo al día en cada commit:

   ```bash
   graphify update .      # solo código, sin tokens
   graphify hook install  # reconstruye al hacer commit/checkout
   ```

4. Consultas útiles:

   ```bash
   graphify explain "get_db()"
   graphify path "mercado_pago_webhook()" "get_db()"
   graphify query "¿qué depende de la conexión a la base de datos?"
   ```

La salida queda en `graphify-out/` (`graph.html`, `GRAPH_REPORT.md`, `graph.json`), que está excluida de Git.
