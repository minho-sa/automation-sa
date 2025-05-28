/**
 * 서비스 어드바이저 인덱스 페이지 기능
 * 서비스 선택 화면에서 사용되는 기능을 정의합니다.
 */
document.addEventListener('DOMContentLoaded', function() {
  // 서비스 카드 클릭 이벤트 처리
  const serviceCards = document.querySelectorAll('.service-card');
  
  serviceCards.forEach(card => {
    card.addEventListener('click', function() {
      const serviceId = this.getAttribute('data-service-id');
      if (serviceId) {
        window.location.href = `/service-advisor/${serviceId}`;
      }
    });
    
    // 카드 내부의 링크 클릭 시 이벤트 전파 방지
    const cardLinks = card.querySelectorAll('a');
    cardLinks.forEach(link => {
      link.addEventListener('click', function(e) {
        e.stopPropagation();
      });
    });
  });
});