/**
 * 리소스 데이터 관리를 위한 공통 JavaScript 함수
 */

/**
 * 알림 메시지 표시
 * 
 * @param {string} type - 알림 유형 ('success', 'error', 'warning', 'info')
 * @param {string} message - 표시할 메시지
 * @param {number} duration - 표시 시간(ms), 기본값 3000ms
 */
function showNotification(type, message, duration = 3000) {
    const notificationArea = document.getElementById('notification-area');
    if (!notificationArea) return;
    
    const notification = document.createElement('div');
    notification.className = `alert alert-${type === 'success' ? 'success' : type === 'error' ? 'danger' : type} alert-dismissible fade show`;
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    notificationArea.appendChild(notification);
    
    // 지정된 시간 후 자동으로 닫기
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => {
            notification.remove();
        }, 300);
    }, duration);
}

/**
 * 날짜 형식 변환 (ISO 8601 -> 사용자 친화적 형식)
 * 
 * @param {string} isoDateString - ISO 8601 형식의 날짜 문자열
 * @param {boolean} includeTime - 시간 포함 여부
 * @returns {string} 변환된 날짜 문자열
 */
function formatDate(isoDateString, includeTime = true) {
    if (!isoDateString) return '';
    
    const date = new Date(isoDateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    if (!includeTime) {
        return `${year}-${month}-${day}`;
    }
    
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    const seconds = String(date.getSeconds()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

/**
 * 숫자 형식 변환 (천 단위 구분 기호 추가)
 * 
 * @param {number} number - 형식을 변환할 숫자
 * @returns {string} 형식이 변환된 숫자 문자열
 */
function formatNumber(number) {
    return number.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
}

/**
 * 바이트 단위 변환 (B -> KB, MB, GB, TB)
 * 
 * @param {number} bytes - 바이트 수
 * @param {number} decimals - 소수점 자릿수
 * @returns {string} 변환된 크기 문자열
 */
function formatBytes(bytes, decimals = 2) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
}

/**
 * 테이블 정렬 기능 추가
 * 
 * @param {string} tableId - 테이블 요소의 ID
 */
function setupTableSort(tableId) {
    const table = document.getElementById(tableId);
    if (!table) return;
    
    const headers = table.querySelectorAll('th[data-sort]');
    
    headers.forEach(header => {
        header.addEventListener('click', () => {
            const column = header.dataset.sort;
            const direction = header.dataset.direction === 'asc' ? 'desc' : 'asc';
            
            // 모든 헤더의 정렬 방향 초기화
            headers.forEach(h => {
                h.dataset.direction = '';
                h.querySelector('i')?.remove();
            });
            
            // 현재 헤더의 정렬 방향 설정
            header.dataset.direction = direction;
            
            // 정렬 아이콘 추가
            const icon = document.createElement('i');
            icon.className = `fas fa-sort-${direction === 'asc' ? 'up' : 'down'} ms-1`;
            header.appendChild(icon);
            
            // 테이블 정렬
            const tbody = table.querySelector('tbody');
            const rows = Array.from(tbody.querySelectorAll('tr'));
            
            rows.sort((a, b) => {
                const aValue = a.querySelector(`td[data-column="${column}"]`).textContent.trim();
                const bValue = b.querySelector(`td[data-column="${column}"]`).textContent.trim();
                
                // 숫자 정렬
                if (!isNaN(aValue) && !isNaN(bValue)) {
                    return direction === 'asc' 
                        ? parseFloat(aValue) - parseFloat(bValue)
                        : parseFloat(bValue) - parseFloat(aValue);
                }
                
                // 문자열 정렬
                return direction === 'asc'
                    ? aValue.localeCompare(bValue)
                    : bValue.localeCompare(aValue);
            });
            
            // 정렬된 행을 테이블에 다시 추가
            rows.forEach(row => tbody.appendChild(row));
        });
    });
}

/**
 * 테이블 필터링 기능 추가
 * 
 * @param {string} inputId - 입력 필드 요소의 ID
 * @param {string} tableId - 테이블 요소의 ID
 */
function setupTableFilter(inputId, tableId) {
    const input = document.getElementById(inputId);
    const table = document.getElementById(tableId);
    if (!input || !table) return;
    
    input.addEventListener('keyup', () => {
        const filter = input.value.toLowerCase();
        const rows = table.querySelectorAll('tbody tr');
        
        rows.forEach(row => {
            const text = row.textContent.toLowerCase();
            row.style.display = text.includes(filter) ? '' : 'none';
        });
    });
}

/**
 * 섹션 토글 기능 추가
 * 
 * @param {string} buttonId - 토글 버튼 요소의 ID
 * @param {string} targetId - 토글 대상 요소의 ID
 */
function setupSectionToggle(buttonId, targetId) {
    const button = document.getElementById(buttonId);
    const target = document.getElementById(targetId);
    if (!button || !target) return;
    
    button.addEventListener('click', () => {
        const isExpanded = target.classList.contains('show');
        
        if (isExpanded) {
            target.classList.remove('show');
            button.setAttribute('aria-expanded', 'false');
            const icon = button.querySelector('.toggle-icon i');
            if (icon) icon.style.transform = 'rotate(0deg)';
        } else {
            target.classList.add('show');
            button.setAttribute('aria-expanded', 'true');
            const icon = button.querySelector('.toggle-icon i');
            if (icon) icon.style.transform = 'rotate(180deg)';
        }
    });
}