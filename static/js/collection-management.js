/**
 * 수집 데이터 관리를 위한 JavaScript 파일
 */

document.addEventListener('DOMContentLoaded', function() {
    // 수집 목록 드롭다운 이벤트 리스너 등록
    setupCollectionDropdown();
    
    // 수집 삭제 버튼 이벤트 리스너 등록
    setupDeleteCollectionButtons();
});

/**
 * 수집 목록 드롭다운 설정
 */
function setupCollectionDropdown() {
    const collectionDropdown = document.getElementById('collection-dropdown');
    if (!collectionDropdown) return;
    
    // 드롭다운 변경 시 해당 수집 데이터 로드
    collectionDropdown.addEventListener('change', function() {
        const collectionId = this.value;
        if (collectionId) {
            window.location.href = `/consolidated?collection_id=${collectionId}`;
        }
    });
}

/**
 * 수집 삭제 버튼 설정
 */
function setupDeleteCollectionButtons() {
    // collection-management.js에서는 삭제 버튼 이벤트 리스너를 등록하지 않음
    // 모든 삭제 기능은 view-collections.js에서 처리
    console.log('Delete buttons will be handled by view-collections.js');
}

/**
 * 수집 데이터 삭제 API 호출 - 이 함수는 더 이상 사용되지 않음
 * 모든 삭제 기능은 view-collections.js의 deleteCollection 함수를 사용
 */
function deleteCollection(collectionId) {
    console.warn('collection-management.js의 deleteCollection은 더 이상 사용되지 않습니다. view-collections.js를 사용하세요.');
    // 실제 삭제 코드는 제거하고 경고만 표시
}

/**
 * 알림 메시지 표시
 */
function showNotification(type, message) {
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : 'danger'} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    notificationArea.appendChild(notification);
    
    // 3초 후 자동으로 닫기
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, 3000);
}