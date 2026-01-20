/**
 * UX/UI ENHANCEMENTS - DSL Agendamento
 * Funções JavaScript para melhorar a experiência do usuário
 */

// ============================================================================
// LOADING SPINNER - Sistema de loading global
// ============================================================================

const LoadingSpinner = {
    overlay: null,
    
    init() {
        if (!this.overlay) {
            this.overlay = document.createElement('div');
            this.overlay.className = 'spinner-overlay';
            this.overlay.innerHTML = `
                <div class="spinner-container">
                    <div class="spinner"></div>
                    <div class="spinner-dots">
                        <div class="spinner-dot"></div>
                        <div class="spinner-dot"></div>
                        <div class="spinner-dot"></div>
                    </div>
                    <p class="text-slate-600 font-medium">Carregando...</p>
                </div>
            `;
            document.body.appendChild(this.overlay);
        }
    },
    
    show(message = 'Carregando...') {
        this.init();
        const text = this.overlay.querySelector('p');
        if (text) text.textContent = message;
        this.overlay.classList.add('active');
    },
    
    hide() {
        if (this.overlay) {
            this.overlay.classList.remove('active');
        }
    }
};

// ============================================================================
// TOAST NOTIFICATIONS - Sistema de notificações modernas
// ============================================================================

const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },
    
    show(title, message, type = 'info', duration = 5000) {
        this.init();
        
        const icons = {
            success: '✓',
            error: '✕',
            warning: '⚠',
            info: 'ℹ'
        };
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.innerHTML = `
            <div class="toast-icon">${icons[type] || icons.info}</div>
            <div class="toast-content">
                <div class="toast-title">${title}</div>
                <div class="toast-message">${message}</div>
            </div>
        `;
        
        this.container.appendChild(toast);
        
        // Auto remove após duração
        setTimeout(() => {
            toast.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        }, duration);
        
        // Remove ao clicar
        toast.addEventListener('click', () => {
            toast.style.animation = 'fadeOut 0.3s ease forwards';
            setTimeout(() => toast.remove(), 300);
        });
    },
    
    success(title, message) {
        this.show(title, message, 'success');
    },
    
    error(title, message) {
        this.show(title, message, 'error');
    },
    
    warning(title, message) {
        this.show(title, message, 'warning');
    },
    
    info(title, message) {
        this.show(title, message, 'info');
    }
};

// ============================================================================
// SKELETON LOADER - Placeholders durante carregamento
// ============================================================================

const SkeletonLoader = {
    create(type = 'card', count = 1) {
        const skeletons = {
            card: `
                <div class="skeleton-card">
                    <div class="skeleton skeleton-line"></div>
                    <div class="skeleton skeleton-line"></div>
                    <div class="skeleton skeleton-line"></div>
                </div>
            `,
            row: `
                <div class="flex items-center gap-4 p-4">
                    <div class="skeleton skeleton-avatar"></div>
                    <div class="flex-1">
                        <div class="skeleton skeleton-line"></div>
                        <div class="skeleton skeleton-line"></div>
                    </div>
                </div>
            `,
            button: `<div class="skeleton skeleton-button"></div>`
        };
        
        const template = skeletons[type] || skeletons.card;
        return template.repeat(count);
    },
    
    show(element, type = 'card', count = 3) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = this.create(type, count);
        }
    },
    
    hide(element, content = '') {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            element.innerHTML = content;
        }
    }
};

// ============================================================================
// CONFIRM DIALOG - Diálogos de confirmação elegantes
// ============================================================================

const ConfirmDialog = {
    show(title, message, onConfirm, onCancel) {
        return new Promise((resolve) => {
            const overlay = document.createElement('div');
            overlay.className = 'modal-backdrop fixed inset-0 z-50 flex items-center justify-center p-4';
            overlay.innerHTML = `
                <div class="modal-content-enhanced bg-white rounded-2xl shadow-2xl max-w-md w-full p-6">
                    <div class="flex items-start gap-4 mb-6">
                        <div class="flex-shrink-0 w-12 h-12 rounded-full bg-blue-100 flex items-center justify-center">
                            <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path>
                            </svg>
                        </div>
                        <div class="flex-1">
                            <h3 class="text-lg font-semibold text-slate-900 mb-2">${title}</h3>
                            <p class="text-slate-600">${message}</p>
                        </div>
                    </div>
                    <div class="flex gap-3 justify-end">
                        <button class="btn-cancel px-4 py-2 rounded-lg font-medium text-slate-700 hover:bg-slate-100 transition-colors">
                            Cancelar
                        </button>
                        <button class="btn-confirm px-4 py-2 rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors">
                            Confirmar
                        </button>
                    </div>
                </div>
            `;
            
            document.body.appendChild(overlay);
            
            const btnCancel = overlay.querySelector('.btn-cancel');
            const btnConfirm = overlay.querySelector('.btn-confirm');
            
            const remove = () => {
                overlay.style.animation = 'fadeOut 0.3s ease forwards';
                setTimeout(() => overlay.remove(), 300);
            };
            
            btnCancel.addEventListener('click', () => {
                remove();
                if (onCancel) onCancel();
                resolve(false);
            });
            
            btnConfirm.addEventListener('click', () => {
                remove();
                if (onConfirm) onConfirm();
                resolve(true);
            });
            
            overlay.addEventListener('click', (e) => {
                if (e.target === overlay) {
                    remove();
                    if (onCancel) onCancel();
                    resolve(false);
                }
            });
        });
    }
};

// ============================================================================
// BUTTON LOADING STATE - Estado de carregamento em botões
// ============================================================================

const ButtonLoader = {
    start(button) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }
        if (button) {
            button.disabled = true;
            button.classList.add('btn-loading');
            button.dataset.originalText = button.innerHTML;
        }
    },
    
    stop(button) {
        if (typeof button === 'string') {
            button = document.querySelector(button);
        }
        if (button) {
            button.disabled = false;
            button.classList.remove('btn-loading');
            if (button.dataset.originalText) {
                button.innerHTML = button.dataset.originalText;
            }
        }
    }
};

// ============================================================================
// FORM VALIDATION - Validação visual de formulários
// ============================================================================

const FormValidator = {
    showError(input, message) {
        if (typeof input === 'string') {
            input = document.querySelector(input);
        }
        if (input) {
            input.classList.add('input-error');
            
            // Remove erro existente
            const existingError = input.parentElement.querySelector('.error-message');
            if (existingError) existingError.remove();
            
            // Adiciona nova mensagem de erro
            const errorDiv = document.createElement('div');
            errorDiv.className = 'error-message text-red-500 text-sm mt-1';
            errorDiv.textContent = message;
            input.parentElement.appendChild(errorDiv);
            
            // Remove erro após 3 segundos
            setTimeout(() => {
                input.classList.remove('input-error');
                errorDiv.remove();
            }, 3000);
        }
    },
    
    clearError(input) {
        if (typeof input === 'string') {
            input = document.querySelector(input);
        }
        if (input) {
            input.classList.remove('input-error');
            const errorDiv = input.parentElement.querySelector('.error-message');
            if (errorDiv) errorDiv.remove();
        }
    }
};

// ============================================================================
// SMOOTH SCROLL - Scroll suave para elementos
// ============================================================================

const SmoothScroll = {
    to(element, offset = 0) {
        if (typeof element === 'string') {
            element = document.querySelector(element);
        }
        if (element) {
            const top = element.getBoundingClientRect().top + window.pageYOffset - offset;
            window.scrollTo({
                top: top,
                behavior: 'smooth'
            });
        }
    },
    
    toTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }
};

// ============================================================================
// COPY TO CLIPBOARD - Copiar para área de transferência com feedback
// ============================================================================

const ClipboardHelper = {
    async copy(text, successMessage = 'Copiado!') {
        try {
            await navigator.clipboard.writeText(text);
            Toast.success('Sucesso', successMessage);
            return true;
        } catch (err) {
            Toast.error('Erro', 'Não foi possível copiar');
            return false;
        }
    }
};

// ============================================================================
// DEBOUNCE - Otimização de eventos frequentes
// ============================================================================

function debounce(func, wait = 300) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// ============================================================================
// THROTTLE - Limitação de execução de funções
// ============================================================================

function throttle(func, limit = 300) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ============================================================================
// AUTO-INIT - Inicialização automática de componentes
// ============================================================================

document.addEventListener('DOMContentLoaded', () => {
    // Adiciona classe enhanced aos botões
    document.querySelectorAll('.btn, button').forEach(btn => {
        if (!btn.classList.contains('btn-enhanced')) {
            btn.classList.add('btn-enhanced');
        }
    });
    
    // Adiciona classe enhanced aos cards
    document.querySelectorAll('.card, [class*="card-"]').forEach(card => {
        if (!card.classList.contains('card-enhanced')) {
            card.classList.add('card-enhanced');
        }
    });
    
    // Adiciona classe enhanced aos inputs
    document.querySelectorAll('input, textarea, select').forEach(input => {
        if (!input.classList.contains('input-enhanced')) {
            input.classList.add('input-enhanced');
        }
    });
    
    // Adiciona classe enhanced às linhas de tabela
    document.querySelectorAll('tbody tr').forEach(row => {
        if (!row.classList.contains('table-row-enhanced')) {
            row.classList.add('table-row-enhanced');
        }
    });
    
    // Scroll to top button
    const scrollBtn = document.createElement('button');
    scrollBtn.className = 'fixed bottom-6 right-6 w-12 h-12 bg-blue-600 text-white rounded-full shadow-lg hover:bg-blue-700 transition-all opacity-0 pointer-events-none z-50';
    scrollBtn.innerHTML = '↑';
    scrollBtn.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
    document.body.appendChild(scrollBtn);
    
    window.addEventListener('scroll', throttle(() => {
        if (window.pageYOffset > 300) {
            scrollBtn.style.opacity = '1';
            scrollBtn.style.pointerEvents = 'auto';
        } else {
            scrollBtn.style.opacity = '0';
            scrollBtn.style.pointerEvents = 'none';
        }
    }, 100));
    
    scrollBtn.addEventListener('click', () => SmoothScroll.toTop());
});

// ============================================================================
// EXPORT - Exportar funções globalmente
// ============================================================================

window.UX = {
    LoadingSpinner,
    Toast,
    SkeletonLoader,
    ConfirmDialog,
    ButtonLoader,
    FormValidator,
    SmoothScroll,
    ClipboardHelper,
    debounce,
    throttle
};
