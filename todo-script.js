// ============================================
// TO-DO LIST APP CON LOCAL STORAGE
// ============================================

class TodoApp {
    constructor() {
        this.todos = [];
        this.filtroActivo = 'todas';
        this.storageKey = 'uptime-todos';
        this.init();
    }

    init() {
        this.cargarDatos();
        this.conectarEventos();
        this.renderizar();
        this.actualizarFecha();
        setInterval(() => this.actualizarFecha(), 60000);
    }

    // ============ MÉTODOS DE STORAGE ============
    cargarDatos() {
        const datos = localStorage.getItem(this.storageKey);
        this.todos = datos ? JSON.parse(datos) : [];
    }

    guardarDatos() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.todos));
    }

    // ============ MÉTODOS DE EVENTOS ============
    conectarEventos() {
        // Formulario
        document.getElementById('todoForm').addEventListener('submit', (e) => {
            e.preventDefault();
            this.agregarTarea();
        });

        // Filtros
        document.querySelectorAll('.filter-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                e.target.closest('.filter-btn').classList.add('active');
                this.filtroActivo = e.target.closest('.filter-btn').dataset.filter;
                this.renderizar();
            });
        });

        // Acciones en lote
        document.getElementById('clearCompletedBtn').addEventListener('click', () => {
            this.mostrarModal('Eliminar completadas', '¿Eliminar todas las tareas completadas?', () => {
                this.todos = this.todos.filter(t => !t.completada);
                this.guardarDatos();
                this.renderizar();
                this.mostrarToast('Tareas completadas eliminadas', 'success');
            });
        });

        document.getElementById('clearAllBtn').addEventListener('click', () => {
            this.mostrarModal('Limpiar todo', '¿Estás seguro? Esto no se puede deshacer.', () => {
                this.todos = [];
                this.guardarDatos();
                this.renderizar();
                this.mostrarToast('Todas las tareas han sido eliminadas', 'success');
            });
        });

        // Modal
        document.getElementById('modalCancel').addEventListener('click', () => {
            this.cerrarModal();
        });

        document.getElementById('confirmModal').addEventListener('click', (e) => {
            if (e.target.id === 'confirmModal') {
                this.cerrarModal();
            }
        });
    }

    // ============ MÉTODOS DE TAREAS ============
    agregarTarea() {
        const input = document.getElementById('todoInput');
        const prioridad = document.getElementById('prioridadSelect').value;
        const texto = input.value.trim();

        if (!texto) {
            this.mostrarToast('Por favor ingresa una tarea', 'error');
            return;
        }

        if (texto.length > 200) {
            this.mostrarToast('La tarea no puede exceder 200 caracteres', 'error');
            return;
        }

        const nuevaTarea = {
            id: Date.now(),
            texto: texto,
            completada: false,
            prioridad: prioridad,
            fechaCreacion: new Date().toISOString()
        };

        this.todos.unshift(nuevaTarea);
        this.guardarDatos();
        this.renderizar();
        input.value = '';
        document.getElementById('prioridadSelect').value = 'media';
        this.mostrarToast('Tarea añadida correctamente', 'success');
    }

    eliminarTarea(id) {
        this.mostrarModal('Eliminar tarea', '¿Estás seguro de que deseas eliminar esta tarea?', () => {
            this.todos = this.todos.filter(t => t.id !== id);
            this.guardarDatos();
            this.renderizar();
            this.mostrarToast('Tarea eliminada', 'success');
        });
    }

    toggleTarea(id) {
        const tarea = this.todos.find(t => t.id === id);
        if (tarea) {
            tarea.completada = !tarea.completada;
            this.guardarDatos();
            this.renderizar();
            this.mostrarToast(
                tarea.completada ? 'Tarea marcada como completada' : 'Tarea marcada como pendiente',
                'success'
            );
        }
    }

    // ============ MÉTODOS DE RENDERIZADO ============
    renderizar() {
        const listElement = document.getElementById('todoList');
        const tareasFiltradas = this.filtrarTareas();

        if (tareasFiltradas.length === 0) {
            listElement.innerHTML = `
                <div class="empty-state">
                    <i class="fas fa-inbox"></i>
                    <p>No hay tareas. ¡Añade una para comenzar!</p>
                </div>
            `;
        } else {
            listElement.innerHTML = tareasFiltradas.map(tarea => this.crearTodoHTML(tarea)).join('');
            this.conectarEventosTareas();
        }

        this.actualizarContadores();
        this.actualizarEstadisticas();
    }

    crearTodoHTML(tarea) {
        const fecha = new Date(tarea.fechaCreacion);
        const fechaFormato = fecha.toLocaleDateString('es-AR');
        const horaFormato = fecha.toLocaleTimeString('es-AR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });

        return `
            <div class="todo-item ${tarea.completada ? 'completada' : ''} prioridad-${tarea.prioridad}">
                <input 
                    type="checkbox" 
                    class="todo-checkbox" 
                    ${tarea.completada ? 'checked' : ''}
                    data-id="${tarea.id}"
                >
                <div class="todo-content">
                    <div class="todo-text">${this.escaparHTML(tarea.texto)}</div>
                    <div class="todo-meta">
                        <span class="todo-prioridad ${tarea.prioridad}">
                            ${tarea.prioridad.charAt(0).toUpperCase() + tarea.prioridad.slice(1)}
                        </span>
                        <span class="todo-fecha">
                            <i class="fas fa-clock"></i> ${fechaFormato} ${horaFormato}
                        </span>
                    </div>
                </div>
                <div class="todo-actions">
                    <button class="action-btn edit" data-id="${tarea.id}" title="Editar">
                        <i class="fas fa-pencil-alt"></i>
                    </button>
                    <button class="action-btn delete" data-id="${tarea.id}" title="Eliminar">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
        `;
    }

    conectarEventosTareas() {
        // Checkboxes
        document.querySelectorAll('.todo-checkbox').forEach(checkbox => {
            checkbox.addEventListener('change', (e) => {
                this.toggleTarea(parseInt(e.target.dataset.id));
            });
        });

        // Botones de eliminar
        document.querySelectorAll('.action-btn.delete').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const id = parseInt(e.target.closest('button').dataset.id);
                this.eliminarTarea(id);
            });
        });

        // Botones de editar (pendiente de implementación)
        document.querySelectorAll('.action-btn.edit').forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.mostrarToast('Función de editar próximamente', 'info');
            });
        });
    }

    filtrarTareas() {
        switch (this.filtroActivo) {
            case 'completadas':
                return this.todos.filter(t => t.completada);
            case 'pendientes':
                return this.todos.filter(t => !t.completada);
            case 'alta':
                return this.todos.filter(t => t.prioridad === 'alta');
            default:
                return this.todos;
        }
    }

    // ============ MÉTODOS DE UTILIDAD ============
    actualizarFecha() {
        const opciones = {
            weekday: 'long',
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        };
        const hoy = new Date();
        const fechaFormato = hoy.toLocaleDateString('es-AR', opciones);
        document.getElementById('fechaActual').textContent = 
            'Hoy es ' + fechaFormato.charAt(0).toUpperCase() + fechaFormato.slice(1);
    }

    actualizarContadores() {
        const total = this.todos.length;
        const completadas = this.todos.filter(t => t.completada).length;
        const pendientes = total - completadas;
        const alta = this.todos.filter(t => t.prioridad === 'alta').length;

        document.getElementById('countTotal').textContent = total;
        document.getElementById('countCompletadas').textContent = completadas;
        document.getElementById('countPendientes').textContent = pendientes;
        document.getElementById('countAlta').textContent = alta;
    }

    actualizarEstadisticas() {
        const total = this.todos.length;
        const completadas = this.todos.filter(t => t.completada).length;
        
        if (total === 0) {
            document.getElementById('productividad').textContent = '0%';
        } else {
            const porcentaje = Math.round((completadas / total) * 100);
            document.getElementById('productividad').textContent = porcentaje + '%';
        }

        // Última actualización
        const ahora = new Date();
        const hora = ahora.toLocaleTimeString('es-AR', { 
            hour: '2-digit', 
            minute: '2-digit' 
        });
        document.getElementById('lastUpdate').textContent = hora;
    }

    escaparHTML(texto) {
        const div = document.createElement('div');
        div.textContent = texto;
        return div.innerHTML;
    }

    // ============ MODAL ============
    mostrarModal(titulo, mensaje, onConfirm) {
        document.getElementById('modalTitle').textContent = titulo;
        document.getElementById('modalMessage').textContent = mensaje;
        
        const modal = document.getElementById('confirmModal');
        modal.classList.add('active');

        const confirmBtn = document.getElementById('modalConfirm');
        const handler = () => {
            onConfirm();
            this.cerrarModal();
            confirmBtn.removeEventListener('click', handler);
        };
        
        confirmBtn.addEventListener('click', handler);
    }

    cerrarModal() {
        document.getElementById('confirmModal').classList.remove('active');
    }

    // ============ TOAST ============
    mostrarToast(mensaje, tipo = 'info') {
        const toast = document.getElementById('toast');
        toast.textContent = mensaje;
        toast.className = `toast show ${tipo}`;

        setTimeout(() => {
            toast.classList.remove('show');
        }, 3000);
    }
}

// ============ INICIALIZACIÓN ============
document.addEventListener('DOMContentLoaded', () => {
    const app = new TodoApp();

    // Menú hamburguesa
    const hamburger = document.getElementById('hamburger');
    const navbarMenu = document.getElementById('navbarMenu');

    hamburger.addEventListener('click', () => {
        navbarMenu.classList.toggle('active');
    });

    // Cerrar menú al hacer click en un link
    document.querySelectorAll('.nav-link').forEach(link => {
        link.addEventListener('click', () => {
            navbarMenu.classList.remove('active');
        });
    });

    console.log('✓ To-Do List App cargada correctamente');
});
