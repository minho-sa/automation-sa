/**
 * 상세 보기 기능을 위한 JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // 상세 보기 버튼 클릭 이벤트
    const detailButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
    
    detailButtons.forEach(button => {
        if (!button.classList.contains('card-header')) {
            // 원래 텍스트와 아이콘 저장
            const originalHTML = button.innerHTML;
            const hasIcon = button.querySelector('i') !== null;
            const originalText = button.textContent.trim();
            
            // Bootstrap collapse 이벤트 리스너 추가
            const targetId = button.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // collapse가 열릴 때 이벤트
                targetElement.addEventListener('show.bs.collapse', function() {
                    button.innerHTML = '접기';
                });
                
                // collapse가 닫힐 때 이벤트
                targetElement.addEventListener('hide.bs.collapse', function() {
                    // 원래 HTML이 아이콘을 포함하고 있었다면 원래 HTML로 복원
                    if (hasIcon) {
                        button.innerHTML = originalHTML;
                    } else {
                        button.textContent = originalText;
                    }
                });
            }
        }
    });
    
    // 툴팁 초기화 (Bootstrap 5)
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});