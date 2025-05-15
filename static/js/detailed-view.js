/**
 * 상세 보기 기능을 위한 JavaScript
 */
document.addEventListener('DOMContentLoaded', function() {
    // 상세 보기 버튼 클릭 이벤트
    const detailButtons = document.querySelectorAll('[data-bs-toggle="collapse"]');
    detailButtons.forEach(button => {
        if (!button.classList.contains('card-header')) {
            button.addEventListener('click', function() {
                const target = this.getAttribute('data-bs-target');
                
                if (document.querySelector(target).classList.contains('show')) {
                    this.textContent = '상세 보기';
                } else {
                    this.textContent = '접기';
                }
            });
        }
    });
    
    // 툴팁 초기화 (Bootstrap 5)
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
});