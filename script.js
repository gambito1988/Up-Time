// Menú hamburguesa
const hamburger = document.getElementById('hamburger');
const navbarMenu = document.getElementById('navbarMenu');

hamburger.addEventListener('click', () => {
    navbarMenu.classList.toggle('active');
});

// Cerrar menú al hacer click en un link
const navLinks = document.querySelectorAll('.nav-link');
navLinks.forEach(link => {
    link.addEventListener('click', () => {
        navbarMenu.classList.remove('active');
    });
});

// FAQ - Expandir/Contraer respuestas
function toggleFAQ(element) {
    const faqItem = element.parentElement;
    
    // Cerrar otros items
    document.querySelectorAll('.faq-item.active').forEach(item => {
        if (item !== faqItem) {
            item.classList.remove('active');
        }
    });
    
    // Toggle del item actual
    faqItem.classList.toggle('active');
}

// Formulario de contacto
const formularioContacto = document.getElementById('formularioContacto');

formularioContacto.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const nombre = formularioContacto.querySelector('input[type="text"]').value;
    const email = formularioContacto.querySelector('input[type="email"]').value;
    const telefono = formularioContacto.querySelector('input[type="tel"]').value;
    const mensaje = formularioContacto.querySelector('textarea').value;
    
    // Crear el cuerpo del mensaje para WhatsApp
    const textoWhatsApp = `Hola, me gustaría contactarme con Up Time.\n\nNombre: ${nombre}\nEmail: ${email}\nTeléfono: ${telefono}\n\nMensaje: ${mensaje}`;
    
    // Codificar el mensaje para la URL
    const mensajeEncodificado = encodeURIComponent(textoWhatsApp);
    
    // Número de WhatsApp (reemplazar con tu número)
    const numeroWhatsApp = '541234567890';
    
    // Crear URL de WhatsApp
    const urlWhatsApp = `https://wa.me/${numeroWhatsApp}?text=${mensajeEncodificado}`;
    
    // Abrir WhatsApp
    window.open(urlWhatsApp, '_blank');
    
    // Limpiar formulario
    formularioContacto.reset();
    
    // Mostrar mensaje de confirmación
    mostrarAlerta('Redirigiendo a WhatsApp...', 'success');
});

// Función para mostrar alertas
function mostrarAlerta(mensaje, tipo = 'info') {
    const alerta = document.createElement('div');
    alerta.className = `alerta alerta-${tipo}`;
    alerta.textContent = mensaje;
    
    const style = document.createElement('style');
    style.textContent = `
        .alerta {
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 15px 20px;
            border-radius: 5px;
            font-weight: 500;
            z-index: 2000;
            animation: slideIn 0.3s ease;
        }
        
        .alerta-success {
            background-color: #4CAF50;
            color: white;
        }
        
        .alerta-error {
            background-color: #f44336;
            color: white;
        }
        
        .alerta-info {
            background-color: #2196F3;
            color: white;
        }
        
        @keyframes slideIn {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }
    `;
    
    document.head.appendChild(style);
    document.body.appendChild(alerta);
    
    // Eliminar alerta después de 3 segundos
    setTimeout(() => {
        alerta.remove();
    }, 3000);
}

// Efecto de scroll suave
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        const href = this.getAttribute('href');
        if (href !== '#') {
            e.preventDefault();
            const target = document.querySelector(href);
            if (target) {
                target.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
            }
        }
    });
});

// Animación de entrada de elementos cuando aparecen en pantalla
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -100px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.animation = 'fadeInUp 0.6s ease forwards';
            observer.unobserve(entry.target);
        }
    });
}, observerOptions);

// Aplicar observador a tarjetas
document.querySelectorAll('.servicio-card, .testimonio-card').forEach(card => {
    card.style.opacity = '0';
    observer.observe(card);
});

// Agregar animación CSS
const styleSheet = document.createElement('style');
styleSheet.textContent = `
    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }
`;
document.head.appendChild(styleSheet);

// Scroll reveal para números de estadísticas
const stats = document.querySelectorAll('.stat h3');
let animacionRealizada = false;

const observerStats = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && !animacionRealizada) {
            animacionRealizada = true;
            stats.forEach(stat => {
                animarNumero(stat);
            });
        }
    });
}, { threshold: 0.5 });

const statsSection = document.querySelector('.nosotros-stats');
if (statsSection) {
    observerStats.observe(statsSection);
}

function animarNumero(elemento) {
    const numero = parseInt(elemento.textContent);
    const incremento = numero / 30;
    let actual = 0;
    
    const intervalo = setInterval(() => {
        actual += incremento;
        if (actual >= numero) {
            elemento.textContent = numero + '+';
            clearInterval(intervalo);
        } else {
            elemento.textContent = Math.floor(actual) + '+';
        }
    }, 50);
}

// Cambiar color de navbar al hacer scroll
window.addEventListener('scroll', () => {
    const navbar = document.querySelector('.navbar');
    if (window.scrollY > 50) {
        navbar.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.2)';
    } else {
        navbar.style.boxShadow = '0 2px 10px rgba(0, 0, 0, 0.1)';
    }
});

console.log('Up Time - Sitio web cargado correctamente');
