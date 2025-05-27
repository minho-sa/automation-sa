/**
 * 서비스 어드바이저 관련 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 서비스 카드 클릭 이벤트 (비활성화된 카드는 제외)
    document.querySelectorAll('.service-card:not(.disabled)').forEach(card => {
        card.addEventListener('click', function(e) {
            // 이미 버튼 클릭으로 이벤트가 발생한 경우 중복 처리 방지
            if (e.target.closest('.awsui-button')) {
                return;
            }
            
            const serviceId = this.getAttribute('data-service-id');
            if (serviceId) {
                window.location.href = `/service-advisor/${serviceId}`;
            }
        });
    });
});