/**
 * VPN 서비스 어드바이저 JavaScript
 */

// VPN 어드바이저 네임스페이스
AWSConsoleCheck.pages.serviceAdvisor.vpn = {};

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
 * VPN 검사 결과 표시 (VPN 특화)
 * @param {string} checkId - 검사 ID
 * @param {Object} result - 검사 결과
 */
function displayVPNCheckResult(checkId, result) {
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
    
    // VPN 리소스 목록
    if (result.resources && result.resources.length > 0) {
        resultHtml += '<div class="check-resources">';
        resultHtml += '<h4><i class="fas fa-network-wired"></i> VPN 리소스 상세 정보</h4>';
        
        // 리소스 수 표시
        resultHtml += `<div class="resource-count">총 ${result.resources.length}개의 리소스</div>`;
        
        resultHtml += '<div class="table-responsive aws-table">';
        resultHtml += '<table class="table table-sm table-hover">';
        resultHtml += '<thead>';
        resultHtml += '<tr>';
        resultHtml += '<th width="5%"></th>';
        resultHtml += '<th width="10%">리전</th>';
        resultHtml += '<th width="15%">리소스 ID</th>';
        resultHtml += '<th width="15%">리소스 타입</th>';
        resultHtml += '<th width="10%">상태</th>';
        resultHtml += '<th width="45%">세부 정보</th>';
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
            resultHtml += `<td class="text-center">${resourceStatusIcon}</td>`;
            resultHtml += `<td>${resource.region || 'N/A'}</td>`;
            
            // 리소스 ID 표시 (VPN 연결 ID 또는 리소스 타입별 ID)
            let resourceId = resource.vpn_connection_id || resource.id || 'N/A';
            resultHtml += `<td><code>${resourceId}</code></td>`;
            
            // 리소스 타입 표시
            let resourceType = 'VPN 연결';
            if (resource.resource_type) {
                resourceType = resource.resource_type;
            } else if (resource.vpn_name) {
                resourceType = 'VPN 연결';
            }
            resultHtml += `<td>${resourceType}</td>`;
            
            resultHtml += `<td>${resource.status_text || ''}</td>`;
            
            // 세부 정보
            let detailInfo = '';
            if (resource.vpn_name && resource.vpn_name !== resourceId) {
                detailInfo += `이름: ${resource.vpn_name}<br>`;
            }
            if (resource.vpn_state) {
                detailInfo += `상태: ${resource.vpn_state}<br>`;
            }
            if (resource.vpn_type) {
                detailInfo += `타입: ${resource.vpn_type}<br>`;
            }
            if (resource.current_usage !== undefined && resource.service_limit !== undefined) {
                detailInfo += `사용량: ${resource.current_usage}/${resource.service_limit} (${resource.usage_percentage}%)<br>`;
            }
            if (resource.tunnel_status && resource.tunnel_status.length > 0) {
                detailInfo += `터널 상태: ${resource.tunnel_status.join(', ')}<br>`;
            }
            if (resource.advice) {
                detailInfo += resource.advice;
            }
            
            resultHtml += `<td class="resource-advice" style="white-space: pre-wrap; word-break: break-word;">${detailInfo}</td>`;
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

// VPN 특화 결과 표시를 위해 공통 함수 오버라이드
if (typeof displayCheckResult === 'function') {
    const originalDisplayCheckResult = displayCheckResult;
    displayCheckResult = function(checkId, result) {
        // VPN 서비스인 경우 특화 함수 사용
        if (getCurrentServiceName() === 'vpn') {
            displayVPNCheckResult(checkId, result);
        } else {
            originalDisplayCheckResult(checkId, result);
        }
    };
}