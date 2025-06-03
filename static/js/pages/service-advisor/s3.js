/**
 * S3 서비스 어드바이저 기능
 */

// S3 어드바이저 네임스페이스
AWSConsoleCheck.pages.serviceAdvisor.s3 = {};

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
});

/**
 * 검사 항목 초기화
 */
function initCheckItems() {
    const checkItems = document.querySelectorAll('.check-item');
    
    checkItems.forEach(item => {
        // 검사 항목 헤더에 클릭 이벤트를 추가하지 않음
        // 검사 결과가 있을 때만 결과 표시 버튼을 추가
        const checkId = item.getAttribute('data-check-id');
        const header = item.querySelector('.check-item-header');
        
        // 검사 결과 확인 버튼 추가
        const actionsDiv = header.querySelector('.check-item-actions');
        const viewResultBtn = document.createElement('button');
        viewResultBtn.className = 'awsui-button awsui-button-normal view-result-btn';
        viewResultBtn.innerHTML = '<i class="fas fa-eye"></i> 결과 보기';
        viewResultBtn.style.display = 'none'; // 기본적으로 숨김
        viewResultBtn.setAttribute('data-check-id', checkId);
        
        // 결과 보기 버튼 클릭 이벤트
        viewResultBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            const resultArea = item.querySelector('.check-item-result');
            if (resultArea.style.display === 'none') {
                resultArea.style.display = 'block';
            } else {
                resultArea.style.display = 'none';
            }
        });
        
        actionsDiv.insertBefore(viewResultBtn, actionsDiv.firstChild);
        
        // 결과 버튼 참조 저장
        item.viewResultBtn = viewResultBtn;
    });
}

/**
 * 검사 실행 버튼 초기화
 */
function initRunCheckButtons() {
    const runButtons = document.querySelectorAll('.run-check-btn');
    
    runButtons.forEach(button => {
        button.addEventListener('click', function(e) {
            e.stopPropagation(); // 이벤트 버블링 방지
            
            const checkId = this.getAttribute('data-check-id');
            const checkItem = document.querySelector(`.check-item[data-check-id="${checkId}"]`);
            const resultArea = checkItem.querySelector('.check-item-result');
            const loadingArea = resultArea.querySelector('.check-result-loading');
            const resultContent = resultArea.querySelector('.check-result-content');
            
            // 결과 영역 표시
            resultArea.style.display = 'block';
            loadingArea.style.display = 'flex';
            resultContent.style.display = 'none';
            
            // 버튼 상태 업데이트
            this.disabled = true;
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 검사 중...';
            
            // 검사 실행
            runCheck(checkId)
                .then(result => {
                    // 검사 결과 표시
                    displayCheckResult(checkId, result);
                    
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.innerHTML = originalText;
                    
                    // 마지막 검사 시간 업데이트
                    updateLastCheckDate(checkId, new Date().toISOString());
                    
                    // 결과 보기 버튼 표시
                    if (checkItem.viewResultBtn) {
                        checkItem.viewResultBtn.style.display = 'inline-block';
                    }
                })
                .catch(error => {
                    console.error('Error running check:', error);
                    
                    // 오류 메시지 표시
                    resultContent.innerHTML = `<div class="alert alert-danger">검사 실행 중 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}</div>`;
                    loadingArea.style.display = 'none';
                    resultContent.style.display = 'block';
                    
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.innerHTML = originalText;
                });
        });
    });
}

/**
 * 전체 선택 체크박스 초기화
 */
function initSelectAllChecks() {
    const selectAllCheckbox = document.getElementById('select-all-checks');
    const checkboxes = document.querySelectorAll('.check-select');
    
    if (selectAllCheckbox) {
        selectAllCheckbox.addEventListener('change', function() {
            const isChecked = this.checked;
            
            checkboxes.forEach(checkbox => {
                checkbox.checked = isChecked;
            });
        });
    }
}

/**
 * 선택한 항목 검사 버튼 초기화
 */
function initRunSelectedChecks() {
    const runSelectedButton = document.getElementById('run-selected-checks');
    
    if (runSelectedButton) {
        runSelectedButton.addEventListener('click', function() {
            const selectedCheckboxes = document.querySelectorAll('.check-select:checked');
            
            if (selectedCheckboxes.length === 0) {
                alert('검사할 항목을 선택해주세요.');
                return;
            }
            
            // 버튼 상태 업데이트
            this.disabled = true;
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 검사 중...';
            
            // 선택한 항목 검사 실행
            const promises = Array.from(selectedCheckboxes).map(checkbox => {
                const checkId = checkbox.getAttribute('data-check-id');
                const checkItem = document.querySelector(`.check-item[data-check-id="${checkId}"]`);
                const resultArea = checkItem.querySelector('.check-item-result');
                const loadingArea = resultArea.querySelector('.check-result-loading');
                const resultContent = resultArea.querySelector('.check-result-content');
                
                // 결과 영역 표시
                resultArea.style.display = 'block';
                loadingArea.style.display = 'flex';
                resultContent.style.display = 'none';
                
                // 검사 실행
                return runCheck(checkId)
                    .then(result => {
                        // 검사 결과 표시
                        displayCheckResult(checkId, result);
                        
                        // 마지막 검사 시간 업데이트
                        updateLastCheckDate(checkId, new Date().toISOString());
                        
                        return result;
                    })
                    .catch(error => {
                        console.error(`Error running check ${checkId}:`, error);
                        
                        // 오류 메시지 표시
                        resultContent.innerHTML = `<div class="alert alert-danger">검사 실행 중 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}</div>`;
                        loadingArea.style.display = 'none';
                        resultContent.style.display = 'block';
                        
                        return null;
                    });
            });
            
            // 모든 검사 완료 후 버튼 상태 복원
            Promise.all(promises)
                .then(() => {
                    this.disabled = false;
                    this.innerHTML = originalText;
                })
                .catch(() => {
                    this.disabled = false;
                    this.innerHTML = originalText;
                });
        });
    }
}

/**
 * 최신 검사 결과 로드
 */
function loadLatestCheckResults() {
    const checkItems = document.querySelectorAll('.check-item');
    
    checkItems.forEach(item => {
        const checkId = item.getAttribute('data-check-id');
        
        // 최신 검사 결과 API 호출
        fetch(`/service_advisor/api/service-advisor/history/s3/${checkId}`)
            .then(response => response.json())
            .then(data => {
                const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
                
                if (data.success && data.result) {
                    // 마지막 검사 시간 업데이트
                    if (lastCheckDateElement && data.timestamp) {
                        const formattedDate = formatTimestamp(data.timestamp);
                        lastCheckDateElement.textContent = `마지막 검사: ${formattedDate}`;
                    }
                    
                    // 검사 결과 표시
                    displayCheckResult(checkId, data.result);
                    
                    // 결과 보기 버튼 표시
                    if (item.viewResultBtn) {
                        item.viewResultBtn.style.display = 'inline-block';
                    }
                } else {
                    // 검사 결과가 없는 경우 기본 메시지 표시
                    if (lastCheckDateElement) {
                        lastCheckDateElement.textContent = '검사 기록 없음';
                    }
                }
            })
            .catch(error => {
                console.error(`Error loading check results for ${checkId}:`, error);
                const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
                if (lastCheckDateElement) {
                    lastCheckDateElement.textContent = '검사 기록 없음';
                }
            });
    });
}

/**
 * 검사 실행
 * @param {string} checkId - 검사 ID
 * @returns {Promise} - 검사 결과 Promise
 */
function runCheck(checkId) {
    // 올바른 API 경로 사용
    const url = `/service_advisor/api/service-advisor/s3/run-check`;
    
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        },
        body: JSON.stringify({ check_id: checkId })
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    });
}

/**
 * 검사 결과 표시
 * @param {string} checkId - 검사 ID
 * @param {Object} result - 검사 결과
 */
function displayCheckResult(checkId, result) {
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
    
    if (result.status === 'ok') {
        statusClass = 'success';
        statusText = '정상';
    } else if (result.status === 'warning') {
        statusClass = 'warning';
        statusText = '경고';
    } else if (result.status === 'error') {
        statusClass = 'danger';
        statusText = '오류';
    } else {
        statusClass = 'secondary';
        statusText = '알 수 없음';
    }
    
    // 결과 헤더
    resultHtml += `
        <div class="alert alert-${statusClass} mb-3">
            <strong>${statusText}:</strong> ${result.message || ''}
        </div>
    `;
    
    // 권장 사항
    if (result.recommendations && result.recommendations.length > 0) {
        resultHtml += '<div class="check-recommendations mb-3">';
        resultHtml += '<h4>권장 조치</h4>';
        resultHtml += '<ul>';
        
        result.recommendations.forEach(recommendation => {
            resultHtml += `<li>${recommendation}</li>`;
        });
        
        resultHtml += '</ul>';
        resultHtml += '</div>';
    }
    
    // 리소스 목록
    if (result.data) {
        let resources = [];
        
        // 검사 유형에 따라 리소스 데이터 추출
        if (result.data.buckets) {
            resources = result.data.buckets;
        }
        
        if (resources.length > 0) {
            resultHtml += '<div class="check-resources">';
            resultHtml += '<h4>리소스 상세 정보</h4>';
            resultHtml += '<div class="table-responsive">';
            resultHtml += '<table class="table table-sm">';
            resultHtml += '<thead>';
            resultHtml += '<tr>';
            resultHtml += '<th>상태</th>';
            resultHtml += '<th>버킷 이름</th>';
            resultHtml += '<th>상태 텍스트</th>';
            resultHtml += '<th>세부 정보</th>';
            resultHtml += '</tr>';
            resultHtml += '</thead>';
            resultHtml += '<tbody>';
            
            resources.forEach(resource => {
                let resourceStatusClass = '';
                
                if (resource.status === 'pass') {
                    resourceStatusClass = 'success';
                } else if (resource.status === 'fail') {
                    resourceStatusClass = 'danger';
                } else if (resource.status === 'warning') {
                    resourceStatusClass = 'warning';
                } else {
                    resourceStatusClass = 'secondary';
                }
                
                resultHtml += `<tr class="table-${resourceStatusClass}">`;
                resultHtml += `<td>${resource.status_text || getStatusText(resource.status)}</td>`;
                resultHtml += `<td>${resource.bucket_name || resource.id}</td>`;
                resultHtml += `<td>${resource.status_text || ''}</td>`;
                resultHtml += `<td>${resource.advice || ''}</td>`;
                resultHtml += '</tr>';
            });
            
            resultHtml += '</tbody>';
            resultHtml += '</table>';
            resultHtml += '</div>';
            resultHtml += '</div>';
        }
    }
    
    // 결과 내용 설정
    resultContent.innerHTML = resultHtml;
    resultContent.style.display = 'block';
}

/**
 * 마지막 검사 시간 업데이트
 * @param {string} checkId - 검사 ID
 * @param {string} timestamp - ISO 형식 타임스탬프
 */
function updateLastCheckDate(checkId, timestamp) {
    const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
    
    if (lastCheckDateElement) {
        const formattedDate = formatTimestamp(timestamp);
        lastCheckDateElement.textContent = `마지막 검사: ${formattedDate}`;
    }
}

/**
 * 상태 텍스트 반환
 * @param {string} status - 상태 코드
 * @returns {string} - 상태 텍스트
 */
function getStatusText(status) {
    switch (status) {
        case 'pass':
            return '정상';
        case 'fail':
            return '문제 있음';
        case 'warning':
            return '경고';
        case 'unknown':
            return '알 수 없음';
        default:
            return status;
    }
}

/**
 * 타임스탬프 포맷팅
 * @param {string} timestamp - ISO 형식 타임스탬프
 * @returns {string} - 포맷팅된 타임스탬프
 */
function formatTimestamp(timestamp) {
    const date = new Date(timestamp);
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * CSRF 토큰 가져오기
 * @returns {string} - CSRF 토큰
 */
function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}