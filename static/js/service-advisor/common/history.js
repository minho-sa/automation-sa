/**
 * 서비스 어드바이저 기록 관련 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 서비스 필터 변경 시 자동 제출
    const serviceFilter = document.getElementById('serviceFilter');
    if (serviceFilter) {
        serviceFilter.addEventListener('change', function() {
            document.getElementById('historyFilterForm').submit();
        });
    }
    
    // 표시 개수 필터 변경 시 자동 제출
    const limitFilter = document.getElementById('limitFilter');
    if (limitFilter) {
        limitFilter.addEventListener('change', function() {
            document.getElementById('historyFilterForm').submit();
        });
    }
    
    // 삭제 버튼 이벤트 처리
    const deleteButtons = document.querySelectorAll('.delete-history');
    const confirmDeleteBtn = document.getElementById('confirmDelete');
    const deleteModal = new bootstrap.Modal(document.getElementById('deleteConfirmModal'));
    
    let keyToDelete = null;
    
    deleteButtons.forEach(button => {
        button.addEventListener('click', function() {
            keyToDelete = this.getAttribute('data-key');
            deleteModal.show();
        });
    });
    
    if (confirmDeleteBtn) {
        confirmDeleteBtn.addEventListener('click', function() {
            if (keyToDelete) {
                fetch(`/api/service-advisor/history/delete/${keyToDelete}`, {
                    method: 'DELETE',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        // 페이지 새로고침
                        window.location.reload();
                    } else {
                        alert('삭제 중 오류가 발생했습니다: ' + data.message);
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    alert('삭제 중 오류가 발생했습니다.');
                })
                .finally(() => {
                    deleteModal.hide();
                });
            }
        });
    }
    
    // 테이블 정렬 기능
    const historyTable = document.getElementById('historyTable');
    if (historyTable) {
        const headers = historyTable.querySelectorAll('th');
        
        headers.forEach((header, index) => {
            header.addEventListener('click', function() {
                sortTable(historyTable, index);
            });
            
            // 정렬 아이콘 추가
            header.style.cursor = 'pointer';
            header.innerHTML += ' <span class="sort-icon"><i class="fas fa-sort"></i></span>';
        });
    }
});

/**
 * 테이블 정렬 함수
 */
function sortTable(table, column) {
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 현재 정렬 방향 확인
    const currentDir = table.getAttribute('data-sort-dir') === 'asc' ? 'desc' : 'asc';
    table.setAttribute('data-sort-dir', currentDir);
    
    // 정렬 아이콘 업데이트
    const headers = table.querySelectorAll('th');
    headers.forEach(header => {
        const icon = header.querySelector('.sort-icon');
        icon.innerHTML = '<i class="fas fa-sort"></i>';
    });
    
    const currentHeader = headers[column];
    const icon = currentHeader.querySelector('.sort-icon');
    icon.innerHTML = currentDir === 'asc' 
        ? '<i class="fas fa-sort-up"></i>' 
        : '<i class="fas fa-sort-down"></i>';
    
    // 행 정렬
    rows.sort((a, b) => {
        const cellA = a.querySelectorAll('td')[column].textContent.trim();
        const cellB = b.querySelectorAll('td')[column].textContent.trim();
        
        if (currentDir === 'asc') {
            return cellA.localeCompare(cellB);
        } else {
            return cellB.localeCompare(cellA);
        }
    });
    
    // 정렬된 행 다시 추가
    rows.forEach(row => {
        tbody.appendChild(row);
    });
}