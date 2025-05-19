/**
 * 서비스 섹션 토글 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 서비스 섹션 헤더 토글 기능
    const sectionHeaders = document.querySelectorAll('.service-section .card-header[data-bs-toggle="collapse"], .service-section .awsui-card-header[data-bs-toggle="collapse"]');
    
    sectionHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            const toggleIcon = this.querySelector('.toggle-icon i');
            
            if (targetElement) {
                if (targetElement.classList.contains('show')) {
                    toggleIcon.classList.remove('fa-chevron-up');
                    toggleIcon.classList.add('fa-chevron-down');
                } else {
                    toggleIcon.classList.remove('fa-chevron-down');
                    toggleIcon.classList.add('fa-chevron-up');
                }
            }
        });
    });
    
    // 상세 보기 버튼 토글 기능 - detailed-view.js에서 처리하므로 여기서는 제거
});