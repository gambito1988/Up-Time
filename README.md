# Up Time - Servicio Técnico de PC

Sitio web profesional para **Up Time**, empresa de soporte técnico y reparación de computadoras en CABA.

## 🖥️ Características

- **Diseño Responsivo**: Optimizado para desktop, tablet y móvil
- **Servicios**: Reparación de PC, notebooks, armado de PC, limpieza y mantenimiento, actualización de hardware y recuperación de datos
- **Contacto Directo**: Integración con WhatsApp para consultas rápidas
- **FAQ**: Preguntas frecuentes con respuestas expandibles
- **Testimonios**: Sección de opiniones de clientes
- **Información de Ubicación**: CABA con servicio online y a domicilio
- **Colores**: Negro, Blanco, Azul y Naranja

## 📁 Estructura del Proyecto

```
Up-Time/
├── index.html       # Página principal
├── styles.css       # Estilos y diseño
├── script.js        # Funcionalidad e interactividad
└── README.md        # Este archivo
```

## 🎨 Paleta de Colores

- **Naranja Primario**: `#FF8C00` - Llamadas a la acción y destacados
- **Azul Secundario**: `#007BFF` - Elementos secundarios
- **Negro**: `#1a1a1a` - Fondo oscuro, texto principal
- **Blanco**: `#ffffff` - Fondo principal
- **Gris Claro**: `#f5f5f5` - Fondos alternos

## 🚀 Secciones

### 1. **Navegación**
- Logo de la empresa
- Enlaces a todas las secciones
- Menú hamburguesa en dispositivos móviles

### 2. **Hero/Banner Principal**
- Presentación principal
- Botones de acción
- Mensaje de bienvenida

### 3. **Servicios**
- 6 servicios principales con iconos
- Descripción de cada servicio
- Diseño en grid responsivo

### 4. **Nosotros**
- Descripción de la empresa
- Ventajas y diferenciadores
- Estadísticas animadas

### 5. **Testimonios**
- Opiniones de clientes con 5 estrellas
- Diseño elegante y responsive

### 6. **Preguntas Frecuentes (FAQ)**
- Sistema expandible/contraíble
- Respuestas claras a dudas comunes

### 7. **Contacto**
- Información de ubicación
- Teléfono, email, WhatsApp
- Formulario de contacto integrado con WhatsApp
- Mapa de ubicación (preparado para Google Maps)

### 8. **Footer**
- Enlaces rápidos
- Redes sociales
- Información de derechos

## 📱 Responsividad

El sitio se adapta automáticamente a:
- **Desktop**: 1920px y superior
- **Tablet**: 768px - 1024px
- **Móvil**: 320px - 767px

## ⚙️ Funcionalidades JavaScript

- **Menú hamburguesa**: Toggle automático en dispositivos pequeños
- **FAQ expandible**: Click para abrir/cerrar respuestas
- **Formulario WhatsApp**: Envío directo de mensajes a través de WhatsApp
- **Animaciones**: Fade-in de tarjetas al scroll
- **Scroll suave**: Navegación fluida entre secciones
- **Contador animado**: Números de estadísticas que cuentan hacia arriba

## 🔧 Personalización

### Cambiar número de WhatsApp
En `script.js`, línea 33:
```javascript
const numeroWhatsApp = '541234567890'; // Cambiar este número
```

### Cambiar información de contacto
En `index.html`, sección de contacto:
- Teléfono: línea ~360
- Email: línea ~369
- WhatsApp: línea ~376

### Agregar redes sociales
En el footer, actualizar los enlaces:
```html
<a href="https://facebook.com/tuperfil" target="_blank"><i class="fab fa-facebook"></i></a>
<a href="https://instagram.com/tuperfil" target="_blank"><i class="fab fa-instagram"></i></a>
```

## 🎯 Próximas mejoras

- [ ] Integración de Google Maps
- [ ] Blog de tips técnicos
- [ ] Sistema de citas online
- [ ] Galería de trabajos realizados
- [ ] Chat en vivo
- [ ] Integración con métodos de pago

## 📝 Notas

- Font Awesome 6.0.0 se carga desde CDN
- No requiere dependencias externas
- Compatible con navegadores modernos
- SEO friendly

## 👨‍💼 Autor

Desarrollado para **Up Time** - Soporte Técnico Profesional en CABA

## 📄 Licencia

Todos los derechos reservados © 2024 Up Time
