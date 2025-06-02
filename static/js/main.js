/**
 * 메인 JavaScript 파일
 */
document.addEventListener('DOMContentLoaded', function() {
    // 전역 초기화 함수
    
    // 툴팁 초기화
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
    
    // 로그아웃 확인
    const logoutLink = document.querySelector('a[href*="logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            if (!confirm('로그아웃 하시겠습니까?')) {
                e.preventDefault();
            }
        });
    }
});