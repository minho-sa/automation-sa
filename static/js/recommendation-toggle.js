/**
 * 추천사항 페이지 토글 버튼 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 추천사항 페이지의 토글 버튼 처리
    const recommendationButtons = document.querySelectorAll('.toggle-details');
    
    recommendationButtons.forEach(button => {
        // 원래 HTML 저장 (아이콘 포함)
        const originalHTML = button.innerHTML;
        
        // 타겟 요소 찾기
        const targetId = button.getAttribute('data-bs-target');
        const targetElement = document.querySelector(targetId);
        
        if (targetElement) {
            // collapse가 열릴 때 이벤트
            targetElement.addEventListener('show.bs.collapse', function() {
                button.innerHTML = '접기';
            });
            
            // collapse가 닫힐 때 이벤트
            targetElement.addEventListener('hide.bs.collapse', function() {
                button.innerHTML = originalHTML;
            });
        }
    });
});