/**
 * 서비스 섹션 토글 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 서비스 섹션 헤더 토글 기능
    const sectionHeaders = document.querySelectorAll('.service-section .card-header[data-bs-toggle="collapse"], .service-section .awsui-card-header[data-bs-toggle="collapse"]');
    
    sectionHeaders.forEach(header => {
        // 초기 상태 설정
        const targetId = header.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetId);
        const toggleIcon = header.querySelector('.toggle-icon i');
        
        if (targetElement && targetElement.classList.contains('show')) {
            header.setAttribute('aria-expanded', 'true');
        } else {
            header.setAttribute('aria-expanded', 'false');
        }
        
        // 원래 제목 텍스트 저장
        const titleElement = header.querySelector('h5');
        if (titleElement) {
            const originalTitle = titleElement.innerHTML;
            header.setAttribute('data-original-title', originalTitle);
        }
        
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            const titleElement = this.querySelector('h5');
            const originalTitle = this.getAttribute('data-original-title');
            
            if (targetElement) {
                if (targetElement.classList.contains('show')) {
                    this.setAttribute('aria-expanded', 'false');
                } else {
                    this.setAttribute('aria-expanded', 'true');
                }
                
                // 항상 원래 제목으로 유지
                if (titleElement && originalTitle) {
                    titleElement.innerHTML = originalTitle;
                }
            }
        });
    });
});