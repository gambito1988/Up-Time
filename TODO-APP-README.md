# To-Do List Application

Una aplicación de tareas completa con almacenamiento local (Local Storage), construida con HTML, CSS y JavaScript puro.

## 🎯 Características

### ✅ Funcionalidades Principales
- **Crear tareas** con texto y nivel de prioridad
- **Marcar completadas/pendientes** con checkbox
- **Filtrar tareas** por estado (todas, pendientes, completadas, alta prioridad)
- **Eliminar tareas** individuales o en lote
- **Almacenamiento persistente** con Local Storage
- **Contador de tareas** por categoría
- **Estadísticas** de productividad
- **Fecha y hora** de creación de cada tarea
- **Confirmación modal** antes de acciones importantes
- **Notificaciones toast** para feedback del usuario

### 🎨 Diseño y UX
- **Interfaz responsiva** (desktop, tablet, móvil)
- **Colores temáticos** (naranja, azul, negro, blanco)
- **Animaciones suaves** y transiciones
- **Indicadores visuales** por prioridad (rojo, naranja, azul)
- **Menú hamburguesa** en dispositivos pequeños
- **Estados vacíos** con iconos descriptivos

### 🔧 Niveles de Prioridad
- 🔴 **Alta** - Tareas urgentes (fondo rojo suave)
- 🟠 **Media** - Tareas normales (fondo naranja)
- 🔵 **Baja** - Tareas opcionales (fondo azul)

## 📁 Archivos

```
todo-app.html       # Estructura HTML
todo-styles.css     # Estilos y diseño
todo-script.js      # Lógica de la aplicación
```

## 🚀 Cómo Usar

1. **Abrir la aplicación**: Abre `todo-app.html` en tu navegador
2. **Agregar tarea**: Escribe en el campo y selecciona prioridad
3. **Completar tarea**: Haz click en el checkbox
4. **Filtrar**: Usa los botones para ver diferentes vistas
5. **Eliminar**: Click en el icono de papelera

## 💾 Local Storage

La aplicación guarda automáticamente todas las tareas en el navegador. Los datos persisten incluso después de:
- Cerrar la pestaña
- Cerrar el navegador
- Reiniciar la computadora

### Estructura de datos guardados:
```json
[
  {
    "id": 1234567890,
    "texto": "Comprar repuestos",
    "completada": false,
    "prioridad": "alta",
    "fechaCreacion": "2024-01-15T10:30:00.000Z"
  }
]
```

## 🎯 Acciones Principales

### Crear Tarea
```
1. Escribe el texto de la tarea
2. Selecciona el nivel de prioridad
3. Haz click en "Agregar"
```

### Filtrar Tareas
- **Todas**: Muestra todas las tareas
- **Pendientes**: Solo tareas no completadas
- **Completadas**: Solo tareas terminadas
- **Alta Prioridad**: Solo tareas urgentes

### Acciones en Lote
- **Eliminar completadas**: Borra todas las tareas marcadas como completadas
- **Limpiar todo**: Elimina todas las tareas (con confirmación)

## 📊 Estadísticas

La aplicación muestra en tiempo real:
- **Productividad**: Porcentaje de tareas completadas
- **Última actualización**: Hora de la última acción

## 🎨 Paleta de Colores

- Naranja Primario: `#FF8C00`
- Azul Secundario: `#007BFF`
- Rojo (Peligro): `#dc3545`
- Verde (Éxito): `#28a745`
- Negro: `#1a1a1a`
- Blanco: `#ffffff`

## 🔒 Seguridad

- No se envían datos a servidores
- Todos los datos se almacenan localmente en el navegador
- No requiere conexión a internet después de cargar
- Escape de HTML para prevenir XSS

## 📱 Responsividad

- ✅ Desktop (1200px+)
- ✅ Tablet (768px - 1024px)
- ✅ Móvil (hasta 767px)
- ✅ Pantallas pequeñas (480px)

## 🔮 Futuras Mejoras

- [ ] Editar tareas
- [ ] Categorías/Etiquetas
- [ ] Tareas recurrentes
- [ ] Recordatorios
- [ ] Exportar/Importar datos
- [ ] Tema oscuro
- [ ] Sincronización en la nube
- [ ] Compartir tareas
- [ ] Historial de tareas eliminadas

## 🛠️ Requisitos

- Navegador moderno con soporte para:
  - ES6 JavaScript
  - Local Storage API
  - CSS Grid y Flexbox
  - Intersection Observer (para futuras mejoras)

## ⚙️ Configuración

Para cambiar el número de almacenamiento o comportamiento, edita en `todo-script.js`:

```javascript
this.storageKey = 'uptime-todos'; // Clave de storage
```

## 📝 Notas de Uso

- Las tareas se ordenan de más reciente a más antigua
- El contador se actualiza automáticamente
- Las notificaciones desaparecen después de 3 segundos
- Modal de confirmación previene acciones accidentales

## 📄 Licencia

Todos los derechos reservados © 2024 Up Time

## 👨‍💼 Desarrollado para

**Up Time** - Soporte Técnico Profesional en CABA
