/**
 * 수집 데이터 목록 보기 모달 관련 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 다른 수집 데이터 보기 버튼 이벤트 리스너 등록 - 링크 방식으로 변경하여 제거
    const viewCollectionsBtn = document.getElementById('view-collections-btn');
    // 이벤트 리스너 제거 - 이제 a 태그의 href 속성으로 이동
    
    // 수집 데이터 드롭다운 이벤트 리스너 등록
    const collectionDropdown = document.getElementById('collection-dropdown');
    if (collectionDropdown) {
        collectionDropdown.addEventListener('change', function() {
            const collectionId = this.value;
            if (collectionId) {
                window.location.href = `/consolidated?collection_id=${collectionId}`;
            }
        });
    }
    
    // 삭제 버튼 이벤트 리스너 등록
    const deleteButtons = document.querySelectorAll('.delete-collection-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const collectionId = this.getAttribute('data-collection-id');
            
            if (confirm('이 수집 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                deleteCollection(collectionId);
            }
        });
    });
});

/**
 * 수집 데이터 목록 모달 표시
 */
function showCollectionsModal(collections) {
    // 기존 모달이 있으면 제거
    let existingModal = document.getElementById('collectionsModal');
    if (existingModal) {
        existingModal.remove();
    }
    
    // 모달 HTML 생성
    const modalHTML = `
    <div class="modal fade" id="collectionsModal" tabindex="-1" aria-labelledby="collectionsModalLabel" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title" id="collectionsModalLabel">수집 데이터 목록</h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    ${collections.length > 0 ? `
                    <div class="table-responsive">
                        <table class="table table-hover">
                            <thead>
                                <tr>
                                    <th>수집 시간</th>
                                    <th>수집 ID</th>
                                    <th>수집된 서비스</th>
                                    <th>작업</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${collections.map(collection => `
                                <tr>
                                    <td>${collection.timestamp.replace('T', ' ').substring(0, 19)}</td>
                                    <td>${collection.collection_id}</td>
                                    <td>${collection.selected_services.join(', ')}</td>
                                    <td>
                                        <a href="/consolidated?collection_id=${collection.collection_id}" class="btn btn-sm btn-primary">
                                            <i class="fas fa-eye"></i> 보기
                                        </a>
                                        <button class="btn btn-sm btn-danger delete-collection-btn" data-collection-id="${collection.collection_id}">
                                            <i class="fas fa-trash"></i> 삭제
                                        </button>
                                    </td>
                                </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    ` : '<div class="alert alert-info">수집된 데이터가 없습니다.</div>'}
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                </div>
            </div>
        </div>
    </div>
    `;
    
    // 모달 추가 및 표시
    document.body.insertAdjacentHTML('beforeend', modalHTML);
    
    // Bootstrap 모달 인스턴스 생성 및 표시
    const collectionsModal = new bootstrap.Modal(document.getElementById('collectionsModal'));
    collectionsModal.show();
    
    // 삭제 버튼 이벤트 리스너 등록
    const deleteButtons = document.querySelectorAll('#collectionsModal .delete-collection-btn');
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            const collectionId = this.getAttribute('data-collection-id');
            
            if (confirm('이 수집 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                deleteCollection(collectionId, collectionsModal);
            }
        });
    });
}

/**
 * 수집 데이터 삭제
 */
function deleteCollection(collectionId, modal) {
    fetch(`/collections/${collectionId}`, {
        method: 'DELETE',
        headers: {
            'Content-Type': 'application/json',
        },
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            // 성공 메시지 표시
            showNotification('success', data.message);
            
            // 모달 닫기
            if (modal) modal.hide();
            
            // 현재 페이지가 삭제된 수집 데이터를 보고 있는 경우 리디렉션
            const urlParams = new URLSearchParams(window.location.search);
            const currentCollectionId = urlParams.get('collection_id');
            
            if (currentCollectionId === collectionId) {
                window.location.href = '/consolidated';
            } else {
                // 1초 후 페이지 새로고침
                setTimeout(() => {
                    window.location.reload();
                }, 1000);
            }
        } else {
            showNotification('error', data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('error', '수집 데이터 삭제 중 오류가 발생했습니다.');
    });
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