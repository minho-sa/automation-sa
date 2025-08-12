/**
 * ACM 서비스 어드바이저 JavaScript
 */

// ACM 어드바이저 네임스페이스
AWSConsoleCheck.pages.serviceAdvisor.acm = {};

document.addEventListener('DOMContentLoaded', function() {
    // 검사 항목 초기화
    initCheckItems();
    
    // 검사 실행 버튼 이벤트 처리
    initRunCheckButtons();
    
    // 전체 선택 체크박스 이벤트 처리
    initSelectAllChecks();
    
    // 선택한 항목 검사 버튼 이벤트 처리
    initRunSelectedChecks();
    
    // 최신 검사 결과 로드
    loadLatestCheckResults();
    
    // 검사 항목 호버 효과
    initCheckItemHover();
    
    // 검사 항목 클릭으로 체크박스 토글
    initCheckItemClick();
});

/**
 * ACM 검사 결과 표시 (ACM 특화)
 * @param {string} checkId - 검사 ID
 * @param {Object} result - 검사 결과
 */
function displayACMCheckResult(checkId, result) {
    const checkItem = document.querySelector(`.check-item[data-check-id="${checkId}"]`);
    const resultArea = checkItem.querySelector('.check-item-result');
    const loadingArea = resultArea.querySelector('.check-result-loading');
    const resultContent = resultArea.querySelector('.check-result-content');
    
    // 로딩 영역 숨기기
    loadingArea.style.display = 'none';
    
    // 결과 내용 생성
    let resultHtml = '';
    
    // 상태에 따른 스타일 설정
    let statusClass = '';
    let statusText = '';
    let statusIcon = '';
    
    if (result.status === 'ok') {
        statusClass = 'success';
        statusText = '정상';
        statusIcon = '<i class="fas fa-check-circle"></i>';
    } else if (result.status === 'warning') {
        statusClass = 'warning';
        statusText = '경고';
        statusIcon = '<i class="fas fa-exclamation-triangle"></i>';
    } else if (result.status === 'error') {
        statusClass = 'danger';
        statusText = '오류';
        statusIcon = '<i class="fas fa-times-circle"></i>';
    } else {
        statusClass = 'secondary';
        statusText = '알 수 없음';
        statusIcon = '<i class="fas fa-question-circle"></i>';
    }
    
    // 결과 헤더
    resultHtml += `
        <div class="alert alert-${statusClass} mb-3">
            ${statusIcon} <strong>${statusText}:</strong> ${result.message || ''}
        </div>
    `;
    
    // 권장 사항
    if (result.recommendations && result.recommendations.length > 0) {
        resultHtml += '<div class="check-recommendations mb-3">';
        resultHtml += '<h4><i class="fas fa-lightbulb"></i> 권장 조치</h4>';
        resultHtml += '<ul>';
        
        result.recommendations.forEach(recommendation => {
            resultHtml += `<li>${recommendation}</li>`;
        });
        
        resultHtml += '</ul>';
        resultHtml += '</div>';
    }
    
    // ACM 인증서 리소스 목록
    if (result.resources && result.resources.length > 0) {
        resultHtml += '<div class="check-resources">';
        resultHtml += '<h4><i class="fas fa-certificate"></i> 인증서 상세 정보</h4>';
        
        // 리소스 수 표시
        resultHtml += `<div class="resource-count">총 ${result.resources.length}개의 인증서</div>`;
        
        resultHtml += '<div class="table-responsive aws-table" style="overflow-x: auto; max-width: 100%; white-space: nowrap;">';
        resultHtml += '<table id="acm-table-' + checkId + '" class="table table-sm table-hover" style="min-width: 1200px; width: auto;">';
        resultHtml += '<thead>';
        resultHtml += '<tr>';
        resultHtml += '<th style="white-space: nowrap; min-width: 50px;"></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 100px; cursor: pointer;" onclick="sortTable(1)">리전 <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 350px; cursor: pointer;" onclick="sortTable(2)">인증서 ID <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 250px; cursor: pointer;" onclick="sortTable(3)">도메인 이름 <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 120px; cursor: pointer;" onclick="sortTable(4)">유형 <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 100px; cursor: pointer;" onclick="sortTable(5)">상태 <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 120px; cursor: pointer;" onclick="sortTable(6)">만료일 <i class="fas fa-sort"></i></th>';
        resultHtml += '<th style="white-space: nowrap; min-width: 500px;">세부 정보</th>'
        resultHtml += '</tr>';
        resultHtml += '</thead>';
        resultHtml += '<tbody>';
        
        result.resources.forEach(resource => {
            let resourceStatusClass = '';
            let resourceStatusIcon = '';
            
            if (resource.status === 'pass') {
                resourceStatusClass = 'success';
                resourceStatusIcon = '<i class="fas fa-check-circle text-success"></i>';
            } else if (resource.status === 'fail') {
                resourceStatusClass = 'danger';
                resourceStatusIcon = '<i class="fas fa-exclamation-triangle text-danger"></i>';
            } else if (resource.status === 'warning') {
                resourceStatusClass = 'warning';
                resourceStatusIcon = '<i class="fas fa-exclamation-triangle text-warning"></i>';
            } else {
                resourceStatusClass = 'secondary';
                resourceStatusIcon = '<i class="fas fa-question-circle text-secondary"></i>';
            }
            
            resultHtml += `<tr class="table-${resourceStatusClass}">`;
            resultHtml += `<td class="text-center" style="white-space: nowrap;">${resourceStatusIcon}</td>`;
            // 인증서 유형을 한국어로 변환
            let certificateTypeKorean = resource.certificate_type || 'N/A';
            if (certificateTypeKorean === 'AMAZON_ISSUED') {
                certificateTypeKorean = 'Amazon 발급';
            } else if (certificateTypeKorean === 'IMPORTED') {
                certificateTypeKorean = '가져온 인증서';
            }
            
            resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
            resultHtml += `<td style="white-space: nowrap;"><code>${resource.certificate_id || resource.id || 'N/A'}</code></td>`;
            resultHtml += `<td style="white-space: nowrap;"><code>${resource.domain_name || 'N/A'}</code></td>`;
            resultHtml += `<td style="white-space: nowrap;">${certificateTypeKorean}</td>`;
            resultHtml += `<td style="white-space: nowrap;">${resource.status_text || ''}</td>`;
            resultHtml += `<td style="white-space: nowrap;">${resource.expiry_date || 'N/A'}</td>`;
            
            // 세부 정보
            let detailInfo = '';
            if (resource.days_until_expiry !== null && resource.days_until_expiry !== undefined) {
                detailInfo += `만료까지: ${resource.days_until_expiry}일<br>`;
            }
            if (resource.subject_alternative_names && resource.subject_alternative_names.length > 0) {
                detailInfo += `SAN: ${resource.subject_alternative_names.join(', ')} `;
            }
            if (resource.advice) {
                detailInfo += resource.advice;
            }
            
            resultHtml += `<td class="resource-advice" style="white-space: pre-line; word-break: break-word; min-width: 500px; max-width: 600px; line-height: 1.4; vertical-align: top;">${detailInfo}</td>`;
            resultHtml += '</tr>';
        });
        
        resultHtml += '</tbody>';
        resultHtml += '</table>';
        resultHtml += '</div>';
        resultHtml += '</div>';
    }
    
    // 결과 내용 설정
    resultContent.innerHTML = resultHtml;
    resultContent.style.display = 'block';
}

// ACM 특화 결과 표시를 위해 공통 함수 오버라이드
if (typeof displayCheckResult === 'function') {
    const originalDisplayCheckResult = displayCheckResult;
    displayCheckResult = function(checkId, result) {
        // ACM 서비스인 경우 특화 함수 사용
        if (getCurrentServiceName() === 'acm') {
            displayACMCheckResult(checkId, result);
        } else {
            originalDisplayCheckResult(checkId, result);
        }
    };
}

/**
 * 테이블 정렬 함수
 * @param {number} columnIndex - 정렬할 열 인덱스
 */
function sortTable(columnIndex) {
    const table = document.querySelector('.check-resources table');
    if (!table) return;
    
    const tbody = table.querySelector('tbody');
    const rows = Array.from(tbody.querySelectorAll('tr'));
    
    // 현재 정렬 상태 확인
    const header = table.querySelector(`th:nth-child(${columnIndex + 1})`);
    const currentSort = header.getAttribute('data-sort') || 'none';
    const isAscending = currentSort !== 'asc';
    
    // 모든 헤더의 정렬 아이콘 초기화
    table.querySelectorAll('th i').forEach(icon => {
        icon.className = 'fas fa-sort';
    });
    
    // 현재 열의 정렬 아이콘 업데이트
    const icon = header.querySelector('i');
    if (icon) {
        icon.className = isAscending ? 'fas fa-sort-up' : 'fas fa-sort-down';
    }
    header.setAttribute('data-sort', isAscending ? 'asc' : 'desc');
    
    // 행 정렬
    rows.sort((a, b) => {
        const aText = a.cells[columnIndex].textContent.trim();
        const bText = b.cells[columnIndex].textContent.trim();
        
        // 날짜 열인 경우 (만료일)
        if (columnIndex === 6) {
            const aDate = new Date(aText);
            const bDate = new Date(bText);
            if (!isNaN(aDate) && !isNaN(bDate)) {
                return isAscending ? aDate - bDate : bDate - aDate;
            }
        }
        
        // 문자열 비교
        const result = aText.localeCompare(bText, 'ko', { numeric: true });
        return isAscending ? result : -result;
    });
    
    // 정렬된 행들을 tbody에 다시 추가
    rows.forEach(row => tbody.appendChild(row));
}