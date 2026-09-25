# Herramientas para Claude Code

Complementos opcionales para trabajar en Up Time con Claude Code. Todos se instalan en tu máquina (no son dependencias de la aplicación ni afectan el despliegue en Render).

| Herramienta | Para qué sirve | Dónde corre | Licencia |
|---|---|---|---|
| [Graphify](#graphify) | Grafo de conocimiento del código | Local | MIT / Apache-2.0 |
| [claude-mem](#claude-mem) | Memoria entre sesiones | Local + servicio de resumen | Apache-2.0 |
| [Headroom](#headroom) | Comprime salidas de herramientas y logs | Proxy local | Apache-2.0 |
| [OmniRoute](#omniroute) | Gateway hacia otros proveedores de modelos | Proxy local | MIT |
| [claude-code-setup](#claude-code-setup) | Recomienda automatizaciones para el repo | Plugin oficial de Anthropic | — |
| [task-observer](#task-observer) | Detecta oportunidades de crear/mejorar skills | Skill local | CC BY 4.0 |

> **Conflicto:** Headroom y OmniRoute funcionan redirigiendo `ANTHROPIC_BASE_URL` hacia un proxy local. Usa solo uno a la vez.

---

## Graphify

[Graphify-Labs/graphify](https://github.com/Graphify-Labs/graphify) analiza el código con tree-sitter (sin LLM ni API key) y genera un grafo que Claude Code puede consultar en lugar de releer archivos completos.

```bash
uv tool install graphifyy                     # o: pipx install graphifyy (doble "y")
graphify update .                             # genera el grafo (solo código, sin tokens)
graphify hook install                         # opcional: reconstruye al hacer commit/checkout
```

Consultas útiles:

```bash
graphify explain "get_db()"
graphify path "mercado_pago_webhook()" "get_db()"
graphify query "¿qué depende de la conexión a la base de datos?"
```

> **Python 3.14:** si `graphify update` falla con `'wrapper_descriptor' object has no attribute '__annotate__'`, reinstala con una versión anterior: `uv tool install --python 3.12 --force graphifyy`.

La skill ya está registrada en el repositorio (`.claude/skills/graphify/`, hooks en `.claude/settings.json` y `CLAUDE.md`); cada desarrollador solo necesita tener la CLI instalada.

La salida queda en `graphify-out/` (`graph.html`, `GRAPH_REPORT.md`, `graph.json`), excluida de Git.

## claude-mem

[thedotmack/claude-mem](https://github.com/thedotmack/claude-mem) registra lo que hace Claude en cada sesión, lo resume y reinyecta el contexto relevante en sesiones futuras. Requiere Node.js 20+.

Dentro de Claude Code:

```
/plugin marketplace add thedotmack/claude-mem
/plugin install claude-mem
```

O desde la terminal: `npx claude-mem install` (no uses `npm install -g claude-mem`: instala solo la librería, sin hooks).

- Los datos se guardan en `~/.claude-mem/` (SQLite + `settings.json`).
- Por defecto los resúmenes usan el servicio alojado de claude-mem (prueba gratuita, luego suscripción). Puedes cambiar el proveedor en `~/.claude-mem/settings.json` o desactivar las funciones en línea con `CLAUDE_MEM_ONLINE_OPTIN=false`.
- Ojo: lo que se resume incluye el contenido de las sesiones. No trabajes con secretos reales (`DATABASE_URL`, credenciales de Mercado Pago) visibles mientras esté activo con un proveedor externo.

## Headroom

[headroomlabs-ai/headroom](https://github.com/headroomlabs-ai/headroom) comprime salidas de herramientas, logs y JSON antes de enviarlos al modelo (reversible; el código reciente no se comprime). Requiere Python 3.10+.

```bash
uv tool install --python 3.13 "headroom-ai[all]"   # o: pip install "headroom-ai[all]"
headroom wrap claude      # levanta el proxy local y configura Claude Code
headroom unwrap claude    # revierte la configuración
```

- La compresión corre en local; no envía prompts ni código.
- Envía por defecto una señal anónima de métricas; desactívala con `HEADROOM_BEACON=off` o `DO_NOT_TRACK=1`.
- Al usar una `ANTHROPIC_BASE_URL` personalizada, Claude Code puede perder la ventana de contexto de 1M ([issue #1158](https://github.com/headroomlabs-ai/headroom/issues/1158)).

## OmniRoute

[diegosouzapw/OmniRoute](https://github.com/diegosouzapw/OmniRoute) es un gateway local (puerto `20128`) que permite usar Claude Code con modelos de otros proveedores y hace *fallback* automático entre ellos.

```bash
npm install -g omniroute
omniroute setup-claude          # genera perfiles en ~/.claude/profiles/
omniroute launch                # arranca Claude Code apuntando al gateway local
omniroute launch --profile glm52
```

Configuración manual equivalente (reinicia Claude Code tras cambiarla):

```bash
export ANTHROPIC_BASE_URL=http://localhost:20128   # sin /v1
export ANTHROPIC_AUTH_TOKEN=<token de OmniRoute>
```

> **Precaución:** todo el tráfico (código, prompts, secretos que aparezcan en la sesión) pasa por el gateway y por los proveedores que configures. Hay reportes públicos de vulnerabilidades en el proyecto, y usar cuentas o cuotas "gratuitas" de terceros puede infringir los términos de esos proveedores. Revísalo antes de usarlo con este repositorio y mantenlo actualizado.

## claude-code-setup

Plugin oficial de Anthropic ([código](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/claude-code-setup)). Analiza el repositorio y recomienda MCP servers, skills, hooks, subagentes y comandos. Es de solo lectura: no modifica archivos.

Dentro de Claude Code:

```
/plugin install claude-code-setup@claude-plugins-official
```

Luego pide, por ejemplo: *"recomienda automatizaciones para este proyecto"*.

## task-observer

[rebelytics/one-skill-to-rule-them-all](https://github.com/rebelytics/one-skill-to-rule-them-all) es una meta-skill que observa tus sesiones y registra correcciones y patrones que conviene convertir en skills nuevas o mejorar.

```bash
npx skills add rebelytics/one-skill-to-rule-them-all --skill task-observer
```

O copia la carpeta completa (`SKILL.md`, `references/`, `scripts/`) en `.claude/skills/task-observer/` (solo este repo) o `~/.claude/skills/task-observer/` (todos los proyectos) y reinicia Claude Code.

- Instalar no basta: añade la instrucción de activación de `references/environments.md` a tu `CLAUDE.md` o instala su hook de inicio de sesión.
- Escribe sus registros en `skill-observations/` y `skill-updates/`.
- Licencia CC BY 4.0: requiere atribución a Eoghan Henn / rebelytics.com si la redistribuyes.
