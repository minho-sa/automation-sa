/**
 * S3 버킷 상세 정보 토글 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // S3 버킷 상세 보기 버튼 이벤트 처리
    const bucketDetailButtons = document.querySelectorAll('[data-bs-toggle="collapse"][data-bs-target^="#bucket-details-"]');
    
    bucketDetailButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.preventDefault();
            const targetId = this.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // 토글 상태 변경
                if (targetElement.classList.contains('show')) {
                    targetElement.classList.remove('show');
                    this.textContent = '상세 보기';
                } else {
                    targetElement.classList.add('show');
                    this.textContent = '접기';
                }
            }
        });
    });
    
    // 태그 필터링 기능
    const tagBadges = document.querySelectorAll('.tag-badge');
    tagBadges.forEach(badge => {
        badge.addEventListener('click', function() {
            const tagValue = this.textContent.trim();
            alert('태그 필터링: ' + tagValue);
            // 여기에 필터링 로직 추가
        });
        badge.style.cursor = 'pointer';
    });
});