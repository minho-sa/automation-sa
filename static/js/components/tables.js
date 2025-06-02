/**
 * 테이블 컴포넌트 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 테이블 정렬 기능
    initTableSort();
    
    // 테이블 상세 정보 토글 기능
    initDetailToggle();
});

/**
 * 테이블 정렬 기능 초기화
 */
function initTableSort() {
    const sortableHeaders = document.querySelectorAll('th[data-sort]');
    
    sortableHeaders.forEach(header => {
        // 정렬 방향 표시 아이콘 추가
        const sortIcon = document.createElement('span');
        sortIcon.className = 'awsui-table-sort-icon ms-1';
        sortIcon.innerHTML = '<i class="fas fa-sort"></i>';
        header.appendChild(sortIcon);
        
        // 정렬 상태 초기화
        header.setAttribute('data-sort-direction', 'none');
        
        // 클릭 이벤트 처리
        header.addEventListener('click', function() {
            const table = this.closest('table');
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr:not(.details-row)'));
            const sortKey = this.getAttribute('data-sort');
            const currentDirection = this.getAttribute('data-sort-direction');
            
            // 다른 헤더의 정렬 상태 초기화
            table.querySelectorAll('th[data-sort]').forEach(th => {
                if (th !== this) {
                    th.setAttribute('data-sort-direction', 'none');
                    th.querySelector('.awsui-table-sort-icon').innerHTML = '<i class="fas fa-sort"></i>';
                }
            });
            
            // 정렬 방향 결정
            let direction = 'asc';
            if (currentDirection === 'asc') {
                direction = 'desc';
            } else if (currentDirection === 'desc') {
                direction = 'none';
            }
            
            // 정렬 방향 표시 업데이트
            this.setAttribute('data-sort-direction', direction);
            if (direction === 'asc') {
                this.querySelector('.awsui-table-sort-icon').innerHTML = '<i class="fas fa-sort-up"></i>';
            } else if (direction === 'desc') {
                this.querySelector('.awsui-table-sort-icon').innerHTML = '<i class="fas fa-sort-down"></i>';
            } else {
                this.querySelector('.awsui-table-sort-icon').innerHTML = '<i class="fas fa-sort"></i>';
            }
            
            // 행 정렬
            if (direction !== 'none') {
                rows.sort((a, b) => {
                    const cellA = a.querySelector(`td[data-sort-value="${sortKey}"]`) || 
                                 a.querySelectorAll('td')[Array.from(table.querySelectorAll('th')).indexOf(this)];
                    const cellB = b.querySelector(`td[data-sort-value="${sortKey}"]`) || 
                                 b.querySelectorAll('td')[Array.from(table.querySelectorAll('th')).indexOf(this)];
                    
                    let valueA = cellA.getAttribute('data-sort-value') || cellA.textContent.trim();
                    let valueB = cellB.getAttribute('data-sort-value') || cellB.textContent.trim();
                    
                    // 숫자 정렬 처리
                    if (!isNaN(valueA) && !isNaN(valueB)) {
                        valueA = parseFloat(valueA);
                        valueB = parseFloat(valueB);
                    }
                    
                    // 날짜 정렬 처리
                    const dateA = new Date(valueA);
                    const dateB = new Date(valueB);
                    if (!isNaN(dateA) && !isNaN(dateB)) {
                        valueA = dateA;
                        valueB = dateB;
                    }
                    
                    if (valueA < valueB) return direction === 'asc' ? -1 : 1;
                    if (valueA > valueB) return direction === 'asc' ? 1 : -1;
                    return 0;
                });
                
                // 정렬된 행을 테이블에 다시 추가
                rows.forEach(row => {
                    tbody.appendChild(row);
                    
                    // 상세 정보 행이 있으면 함께 이동
                    const rowId = row.getAttribute('id');
                    if (rowId) {
                        const detailRow = tbody.querySelector(`tr[data-parent="${rowId}"]`);
                        if (detailRow) {
                            tbody.appendChild(detailRow);
                        }
                    }
                });
            }
        });
    });
}

/**
 * 테이블 상세 정보 토글 기능 초기화
 */
function initDetailToggle() {
    const detailButtons = document.querySelectorAll('[data-bs-toggle="collapse"]:not(.awsui-card-header)');
    
    detailButtons.forEach(button => {
        if (!button.classList.contains('card-header')) {
            // 원래 텍스트와 아이콘 저장
            const originalHTML = button.innerHTML;
            const hasIcon = button.querySelector('i') !== null;
            const originalText = button.textContent.trim();
            
            // Bootstrap collapse 이벤트 리스너 추가
            const targetId = button.getAttribute('data-bs-target');
            const targetElement = document.querySelector(targetId);
            
            if (targetElement) {
                // collapse가 열릴 때 이벤트
                targetElement.addEventListener('show.bs.collapse', function() {
                    button.innerHTML = '접기';
                });
                
                // collapse가 닫힐 때 이벤트
                targetElement.addEventListener('hide.bs.collapse', function() {
                    // 원래 HTML이 아이콘을 포함하고 있었다면 원래 HTML로 복원
                    if (hasIcon) {
                        button.innerHTML = originalHTML;
                    } else {
                        button.textContent = originalText;
                    }
                });
            }
        }
    });
}