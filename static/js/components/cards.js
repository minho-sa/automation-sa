/**
 * 카드 컴포넌트 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 카드 헤더 토글 기능
    const cardHeaders = document.querySelectorAll('.awsui-card-header[data-bs-toggle="collapse"]');
    
    cardHeaders.forEach(header => {
        // 초기 상태 설정
        const targetId = header.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetId);
        const toggleIcon = header.querySelector('.toggle-icon i');
        
        if (targetElement && targetElement.classList.contains('show')) {
            header.setAttribute('aria-expanded', 'true');
            if (toggleIcon) {
                toggleIcon.style.transform = 'rotate(180deg)';
            }
        } else {
            header.setAttribute('aria-expanded', 'false');
            if (toggleIcon) {
                toggleIcon.style.transform = 'rotate(0deg)';
            }
        }
        
        // 원래 제목 텍스트 저장
        const titleElement = header.querySelector('h5');
        if (titleElement) {
            const originalTitle = titleElement.innerHTML;
            header.setAttribute('data-original-title', originalTitle);
        }
        
        // 클릭 이벤트 처리
        header.addEventListener('click', function() {
            const targetId = this.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            const toggleIcon = this.querySelector('.toggle-icon i');
            
            if (targetElement) {
                if (targetElement.classList.contains('show')) {
                    targetElement.classList.remove('show');
                    this.setAttribute('aria-expanded', 'false');
                    if (toggleIcon) {
                        toggleIcon.style.transform = 'rotate(0deg)';
                    }
                } else {
                    targetElement.classList.add('show');
                    this.setAttribute('aria-expanded', 'true');
                    if (toggleIcon) {
                        toggleIcon.style.transform = 'rotate(180deg)';
                    }
                }
            }
        });
    });
});