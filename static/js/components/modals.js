/**
 * 모달 컴포넌트 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 모달 동작 개선
    const modals = document.querySelectorAll('.modal');
    
    if (modals) {
        modals.forEach(modal => {
            modal.addEventListener('show.bs.modal', function() {
                // 모달 열릴 때 body에 스크롤 방지 클래스 추가
                document.body.classList.add('modal-open');
                
                // 기존 백드롭 제거 후 새로 생성
                const existingBackdrop = document.querySelector('.modal-backdrop');
                if (existingBackdrop) {
                    existingBackdrop.remove();
                }
                
                // 새 백드롭 생성
                const backdrop = document.createElement('div');
                backdrop.className = 'modal-backdrop fade show';
                document.body.appendChild(backdrop);
                
                // 이 모달에 대한 고유 식별자 추가
                backdrop.dataset.modalId = this.id;
            });
            
            modal.addEventListener('hidden.bs.modal', function() {
                // 다른 열린 모달이 없을 경우에만 modal-open 클래스 제거
                const openModals = document.querySelectorAll('.modal.show');
                if (openModals.length <= 1) { // 현재 닫히는 모달만 있는 경우
                    document.body.classList.remove('modal-open');
                }
                
                // 이 모달과 연결된 백드롭 제거
                const backdrop = document.querySelector(`.modal-backdrop[data-modal-id="${this.id}"]`);
                if (backdrop) {
                    backdrop.remove();
                } else {
                    // 특정 백드롭을 찾을 수 없는 경우 모든 백드롭 제거
                    const anyBackdrop = document.querySelector('.modal-backdrop');
                    if (anyBackdrop) {
                        anyBackdrop.remove();
                    }
                }
            });
            
            // 모달 내부 클릭이 뒤에 있는 요소로 전파되지 않도록 방지
            modal.addEventListener('click', function(event) {
                event.stopPropagation();
            });
        });
    }
});