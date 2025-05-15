// Main JavaScript file for AWS Console Check application

document.addEventListener('DOMContentLoaded', function() {
    // Add event listener for password visibility toggle
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    if (togglePasswordButtons) {
        togglePasswordButtons.forEach(button => {
            button.addEventListener('click', function() {
                const passwordInput = document.querySelector(this.getAttribute('data-target'));
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.textContent = '숨기기';
                } else {
                    passwordInput.type = 'password';
                    this.textContent = '보기';
                }
            });
        });
    }

    // Add tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    // Add confirmation for logout
    const logoutLink = document.querySelector('a[href*="logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            if (!confirm('로그아웃 하시겠습니까?')) {
                e.preventDefault();
            }
        });
    }
    
    // 테이블 정렬 기능은 table-sort.js로 이동되었습니다
    
    // Enhance modal behavior to prevent background interaction
    const modals = document.querySelectorAll('.modal');
    if (modals) {
        modals.forEach(modal => {
            modal.addEventListener('show.bs.modal', function() {
                // Add a class to the body to prevent scrolling
                document.body.classList.add('modal-open');
                
                // Remove any existing backdrop before creating a new one
                const existingBackdrop = document.querySelector('.modal-backdrop');
                if (existingBackdrop) {
                    existingBackdrop.remove();
                }
                
                // Create a new backdrop
                const backdrop = document.createElement('div');
                backdrop.className = 'modal-backdrop fade show';
                document.body.appendChild(backdrop);
                
                // Add a unique identifier to the backdrop for this modal
                backdrop.dataset.modalId = this.id;
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                // Check if there are other open modals before removing modal-open class
                const openModals = document.querySelectorAll('.modal.show');
                if (openModals.length <= 1) { // Only the current one that's being closed
                    document.body.classList.remove('modal-open');
                }
                
                // Remove the backdrop associated with this modal
                const backdrop = document.querySelector(`.modal-backdrop[data-modal-id="${this.id}"]`);
                if (backdrop) {
                    backdrop.remove();
                } else {
                    // Fallback: remove any backdrop if the specific one can't be found
                    const anyBackdrop = document.querySelector('.modal-backdrop');
                    if (anyBackdrop) {
                        anyBackdrop.remove();
                    }
                }
            });
            
            // Prevent clicks on the modal from propagating to elements behind it
            modal.addEventListener('click', function(event) {
                event.stopPropagation();
            });
        });
    }
});