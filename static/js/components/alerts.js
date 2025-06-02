/**
 * 알림 컴포넌트 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 알림 닫기 버튼 기능 구현
    const alertCloseButtons = document.querySelectorAll('.awsui-alert-close');
    
    alertCloseButtons.forEach(button => {
        button.addEventListener('click', function() {
            const alert = this.closest('.awsui-alert');
            if (alert) {
                // 알림 요소에 페이드아웃 효과 추가
                alert.style.opacity = '0';
                alert.style.transition = 'opacity 0.3s ease-out';
                
                // 애니메이션 완료 후 요소 제거
                setTimeout(() => {
                    alert.remove();
                }, 300);
            }
        });
    });
    
    // 자동 닫힘 알림 처리
    const autoCloseAlerts = document.querySelectorAll('.awsui-alert[data-auto-close]');
    
    autoCloseAlerts.forEach(alert => {
        const closeDelay = parseInt(alert.dataset.autoClose) || 5000; // 기본값 5초
        
        setTimeout(() => {
            // 알림 요소에 페이드아웃 효과 추가
            alert.style.opacity = '0';
            alert.style.transition = 'opacity 0.3s ease-out';
            
            // 애니메이션 완료 후 요소 제거
            setTimeout(() => {
                alert.remove();
            }, 300);
        }, closeDelay);
    });
});