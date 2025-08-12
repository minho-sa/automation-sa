/**
 * 서비스 어드바이저 공통 기능
 */

// 공통 네임스페이스
if (!window.AWSConsoleCheck) {
    window.AWSConsoleCheck = {};
}
if (!AWSConsoleCheck.pages) {
    AWSConsoleCheck.pages = {};
}
if (!AWSConsoleCheck.pages.serviceAdvisor) {
    AWSConsoleCheck.pages.serviceAdvisor = {};
}

// 현재 서비스 이름 가져오기
function getCurrentServiceName() {
    const path = window.location.pathname;
    const matches = path.match(/\/advisor\/([^\/]+)/);
    return matches ? matches[1] : '';
}

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
                this.innerHTML = '<i class="fas fa-eye-slash"></i> 결과 숨기기';
            } else {
                resultArea.style.display = 'none';
                this.innerHTML = '<i class="fas fa-eye"></i> 결과 보기';
            }
        });
        
        actionsDiv.insertBefore(viewResultBtn, actionsDiv.firstChild);
        
        // 결과 버튼 참조 저장
        item.viewResultBtn = viewResultBtn;
        
        // PDF 다운로드 버튼 이벤트 처리
        const downloadPdfBtn = item.querySelector('.download-pdf-btn');
        if (downloadPdfBtn) {
            downloadPdfBtn.addEventListener('click', function(e) {
                e.stopPropagation();
                const checkId = this.getAttribute('data-check-id');
                const serviceName = getCurrentServiceName();
                
                // 버튼 상태 업데이트
                const originalText = this.innerHTML;
                this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 다운로드 중...';
                this.disabled = true;
                
                // PDF 다운로드 URL
                const pdfUrl = `/advisor/export-pdf/${serviceName}/${checkId}`;
                console.log(`PDF 다운로드 URL: ${pdfUrl}`);
                
                // iframe을 사용하여 다운로드 (새 창 팝업 차단 방지)
                const iframe = document.createElement('iframe');
                iframe.style.display = 'none';
                document.body.appendChild(iframe);
                
                iframe.onload = () => {
                    // 다운로드 완료 후 버튼 상태 복원
                    setTimeout(() => {
                        this.innerHTML = originalText;
                        this.disabled = false;
                        document.body.removeChild(iframe);
                    }, 1000);
                };
                
                iframe.src = pdfUrl;
            });
        }
    });
}

/**
 * 검사 항목 호버 효과 초기화
 */
function initCheckItemHover() {
    const checkItems = document.querySelectorAll('.check-item');
    
    checkItems.forEach(item => {
        item.addEventListener('mouseenter', function() {
            this.classList.add('check-item-hover');
        });
        
        item.addEventListener('mouseleave', function() {
            this.classList.remove('check-item-hover');
        });
    });
}

/**
 * 검사 실행 버튼 초기화
 */
function initRunCheckButtons() {
    const runButtons = document.querySelectorAll('.run-check-btn');
    const serviceName = getCurrentServiceName();
    
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
            runCheck(serviceName, checkId)
                .then(result => {
                    // 검사 결과 표시
                    displayCheckResult(checkId, result);
                    
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.innerHTML = originalText;
                    
                    // 마지막 검사 시간 업데이트
                    updateLastCheckDate(checkId, new Date().toISOString());
                    
                    // 결과 보기 버튼 표시 및 텍스트 변경
                    if (checkItem.viewResultBtn) {
                        checkItem.viewResultBtn.style.display = 'inline-flex';
                        checkItem.viewResultBtn.innerHTML = '<i class="fas fa-eye-slash"></i> 결과 숨기기';
                    }
                    
                    // PDF 다운로드 버튼 표시 및 순서 변경
                    const downloadPdfBtn = checkItem.querySelector('.download-pdf-btn');
                    const runCheckBtn = checkItem.querySelector('.run-check-btn');
                    if (downloadPdfBtn && runCheckBtn) {
                        downloadPdfBtn.style.display = 'inline-block';
                        // PDF 다운로드 버튼을 검사하기 버튼 앞으로 이동
                        runCheckBtn.parentNode.insertBefore(downloadPdfBtn, runCheckBtn);
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
            
            // 선택된 항목 수 업데이트
            updateSelectedCount();
        });
    }
    
    // 개별 체크박스 변경 이벤트
    checkboxes.forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateSelectedCount();
        });
    });
    
    // 초기 선택 항목 수 업데이트
    updateSelectedCount();
}

/**
 * 선택된 항목 수 업데이트
 */
function updateSelectedCount() {
    const selectedCheckboxes = document.querySelectorAll('.check-select:checked');
    const runSelectedButton = document.getElementById('run-selected-checks');
    const downloadSelectedButton = document.getElementById('download-selected-checks');
    
    if (runSelectedButton) {
        if (selectedCheckboxes.length > 0) {
            runSelectedButton.innerHTML = `<i class="fas fa-play"></i> 선택한 항목 검사하기 (${selectedCheckboxes.length})`;
            runSelectedButton.disabled = false;
        } else {
            runSelectedButton.innerHTML = '<i class="fas fa-play"></i> 선택한 항목 검사하기';
            runSelectedButton.disabled = true;
        }
    }
    
    if (downloadSelectedButton) {
        if (selectedCheckboxes.length > 0) {
            downloadSelectedButton.innerHTML = `<i class="fas fa-file-pdf"></i> 선택한 항목 PDF 다운로드 (${selectedCheckboxes.length})`;
            downloadSelectedButton.disabled = false;
        } else {
            downloadSelectedButton.innerHTML = '<i class="fas fa-file-pdf"></i> 선택한 항목 PDF 다운로드';
            downloadSelectedButton.disabled = true;
        }
    }
}

/**
 * 선택한 항목 검사 버튼 초기화
 */
function initRunSelectedChecks() {
    const runSelectedButton = document.getElementById('run-selected-checks');
    const downloadSelectedButton = document.getElementById('download-selected-checks');
    const serviceName = getCurrentServiceName();
    
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
                return runCheck(serviceName, checkId)
                    .then(result => {
                        // 검사 결과 표시
                        displayCheckResult(checkId, result);
                        
                        // 마지막 검사 시간 업데이트
                        updateLastCheckDate(checkId, new Date().toISOString());
                        
                        // 결과 보기 버튼 표시 및 텍스트 변경
                        if (checkItem.viewResultBtn) {
                            checkItem.viewResultBtn.style.display = 'inline-flex';
                            checkItem.viewResultBtn.innerHTML = '<i class="fas fa-eye-slash"></i> 결과 숨기기';
                        }
                        
                        // PDF 다운로드 버튼 표시 및 순서 변경
                        const downloadPdfBtn = checkItem.querySelector('.download-pdf-btn');
                        const runCheckBtn = checkItem.querySelector('.run-check-btn');
                        if (downloadPdfBtn && runCheckBtn) {
                            downloadPdfBtn.style.display = 'inline-block';
                            // PDF 다운로드 버튼을 검사하기 버튼 앞으로 이동
                            runCheckBtn.parentNode.insertBefore(downloadPdfBtn, runCheckBtn);
                        }
                        
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
        
        // 초기 상태 설정
        updateSelectedCount();
    }
    
    // 선택한 항목 PDF 다운로드 버튼 초기화
    if (downloadSelectedButton) {
        downloadSelectedButton.addEventListener('click', function() {
            const selectedCheckboxes = document.querySelectorAll('.check-select:checked');
            
            if (selectedCheckboxes.length === 0) {
                alert('다운로드할 항목을 선택해주세요.');
                return;
            }
            
            // 선택한 항목의 검사 결과 상태 확인
            const checkItems = Array.from(selectedCheckboxes).map(checkbox => {
                return {
                    service_name: serviceName,
                    check_id: checkbox.getAttribute('data-check-id')
                };
            });
            
            // 버튼 상태 업데이트
            this.disabled = true;
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 준비 중...';
            
            // 선택한 항목의 검사 결과 상태 확인
            fetch('/advisor/check-results-status', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken(),
                    'X-Requested-With': 'XMLHttpRequest'
                },
                body: JSON.stringify({ check_items: checkItems })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success && data.results_status) {
                    // 검사 결과가 없는 항목 필터링
                    const noResultItems = data.results_status.filter(item => !item.has_result);
                    
                    if (noResultItems.length > 0) {
                        // 검사 결과가 없는 항목이 있는 경우 경고
                        const noResultIds = noResultItems.map(item => item.check_id);
                        alert(`다음 항목은 검사 결과가 없습니다: ${noResultIds.join(', ')}\n\n검사를 먼저 실행해주세요.`);
                        this.disabled = false;
                        this.innerHTML = originalText;
                        return;
                    }
                    
                    // 모든 항목에 검사 결과가 있는 경우 PDF 다운로드 진행
                    this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 다운로드 중...';
                    
                    // PDF 다운로드 요청
                    const iframe = document.createElement('iframe');
                    iframe.style.display = 'none';
                    document.body.appendChild(iframe);
                    
                    // POST 요청을 위한 폼 생성
                    const form = document.createElement('form');
                    form.method = 'POST';
                    form.action = '/advisor/export-multiple-pdf';
                    form.target = 'download-iframe';
                    form.style.display = 'none';
                    
                    // CSRF 토큰 추가
                    const csrfInput = document.createElement('input');
                    csrfInput.type = 'hidden';
                    csrfInput.name = 'csrf_token';
                    csrfInput.value = getCsrfToken();
                    form.appendChild(csrfInput);
                    
                    // 데이터 추가
                    const dataInput = document.createElement('input');
                    dataInput.type = 'hidden';
                    dataInput.name = 'data';
                    dataInput.value = JSON.stringify({ check_items: checkItems });
                    form.appendChild(dataInput);
                    
                    // 폼 제출
                    document.body.appendChild(form);
                    iframe.name = 'download-iframe';
                    
                    // iframe 로드 이벤트
                    iframe.onload = () => {
                        // 다운로드 완료 후 버튼 상태 복원
                        setTimeout(() => {
                            this.innerHTML = originalText;
                            this.disabled = false;
                            document.body.removeChild(iframe);
                            document.body.removeChild(form);
                        }, 1000);
                    };
                    
                    // 폼 제출 대신 fetch API 사용
                    fetch('/advisor/export-multiple-pdf', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-CSRFToken': getCsrfToken(),
                            'X-Requested-With': 'XMLHttpRequest'
                        },
                        body: JSON.stringify({ check_items: checkItems })
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('PDF 생성 중 오류가 발생했습니다.');
                        }
                        return response.blob();
                    })
                    .then(blob => {
                        // Blob을 다운로드 링크로 변환
                        const url = window.URL.createObjectURL(blob);
                        const a = document.createElement('a');
                        a.style.display = 'none';
                        a.href = url;
                        a.download = `aws-advisor-multiple-checks-${new Date().toISOString().replace(/[:.]/g, '-')}.pdf`;
                        document.body.appendChild(a);
                        a.click();
                        
                        // 정리
                        window.URL.revokeObjectURL(url);
                        document.body.removeChild(a);
                        
                        // 버튼 상태 복원
                        this.innerHTML = originalText;
                        this.disabled = false;
                    })
                    .catch(error => {
                        console.error('PDF 다운로드 중 오류 발생:', error);
                        alert('PDF 다운로드 중 오류가 발생했습니다.');
                        this.innerHTML = originalText;
                        this.disabled = false;
                    });
                } else {
                    alert('검사 결과 상태를 확인하는 중 오류가 발생했습니다.');
                    this.disabled = false;
                    this.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error('Error checking results status:', error);
                alert('검사 결과 상태를 확인하는 중 오류가 발생했습니다.');
                this.disabled = false;
                this.innerHTML = originalText;
            });
        });
        
        // 초기 상태 설정
        updateSelectedCount();
    }
}

/**
 * 최신 검사 결과 로드
 */
function loadLatestCheckResults() {
    const checkItems = document.querySelectorAll('.check-item');
    const serviceName = getCurrentServiceName();
    
    checkItems.forEach(item => {
        const checkId = item.getAttribute('data-check-id');
        
        // 최신 검사 결과 API 호출
        fetch(`/advisor/history/${serviceName}/${checkId}`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
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
                        item.viewResultBtn.style.display = 'inline-flex';
                    }
                    
                    // PDF 다운로드 버튼 표시 및 순서 변경
                    const downloadPdfBtn = item.querySelector('.download-pdf-btn');
                    const runCheckBtn = item.querySelector('.run-check-btn');
                    if (downloadPdfBtn && runCheckBtn) {
                        downloadPdfBtn.style.display = 'inline-block';
                        // PDF 다운로드 버튼을 검사하기 버튼 앞으로 이동
                        runCheckBtn.parentNode.insertBefore(downloadPdfBtn, runCheckBtn);
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
 * @param {string} serviceName - 서비스 이름
 * @param {string} checkId - 검사 ID
 * @returns {Promise} - 검사 결과 Promise
 */
function runCheck(serviceName, checkId) {
    // 올바른 API 경로 사용
    const url = `/advisor/${serviceName}/run-check`;
    console.log(`API 호출: ${url}`);
    
    return fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
            'X-Requested-With': 'XMLHttpRequest'
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
    
    // 리소스 목록
    let resources = [];
    
    // 서비스별 데이터 구조 처리
    if (result.resources && result.resources.length > 0) {
        resources = result.resources;
    } else if (result.data) {
        // IAM 등 다른 서비스의 데이터 구조 처리
        if (result.data.users) {
            resources = result.data.users;
        } else if (result.data.roles) {
            resources = result.data.roles;
        } else if (result.data.policies) {
            resources = result.data.policies;
        } else if (result.data.instances) {
            resources = result.data.instances;
        } else if (result.data.buckets) {
            resources = result.data.buckets;
        } else if (result.data.functions) {
            resources = result.data.functions;
        } else if (Array.isArray(result.data)) {
            resources = result.data;
        }
    }
    
    if (resources.length > 0) {
        resultHtml += '<div class="check-resources">';
        resultHtml += '<h4><i class="fas fa-server"></i> 리소스 상세 정보</h4>';
        
        // 리소스 수 표시
        resultHtml += `<div class="resource-count">총 ${resources.length}개의 리소스</div>`;
        
        resultHtml += '<div class="table-responsive aws-table" style="overflow-x: auto; max-width: 100%; border: 1px solid #dee2e6; border-radius: 0.375rem; position: relative;">';
        resultHtml += '<table class="table table-sm table-hover" style="min-width: 1800px; width: auto; margin-bottom: 0; table-layout: fixed;">';
        resultHtml += '<thead>';
        resultHtml += '<tr>';
        resultHtml += '<th width="5%"></th>';
        // S3 버킷, RDS 인스턴스, Lambda 함수의 경우 리소스 ID 컬럼 제거
        const hasS3Buckets = resources.some(r => r.bucket_name);
        const hasRDSInstances = resources.some(r => r.instance_id && r.engine);
        const hasLambdaFunctions = resources.some(r => r.function_name || r.memory_size !== undefined);
        const hasIAMUsers = resources.some(r => r.user_name);
        const hasIAMPolicies = resources.some(r => r.policy_name);
        const hasEC2SecurityGroups = resources.some(r => r.sg_name && r.sg_id);
        const hasEBSVolumes = resources.some(r => r.volume_name && r.volume_id);
        const hasEC2Instances = resources.some(r => r.instance_name && r.instance_id);
        const hasUnusedResources = resources.some(r => r.resource_type && (r.resource_type === 'Elastic IP' || r.resource_type === 'EBS Volume'));
        const hasReservedInstances = resources.some(r => r.ri_id);
        const hasRDSEngineVersions = resources.some(r => r.db_identifier && r.engine);
        if (hasS3Buckets) {
            resultHtml += '<th width="15%">리전</th>';
            resultHtml += '<th width="25%">버킷 이름</th>';
            resultHtml += '<th width="15%">상태</th>';
            resultHtml += '<th width="45%">세부 정보</th>';
        } else if (hasRDSInstances) {
            resultHtml += '<th width="15%">리전</th>';
            resultHtml += '<th width="25%">DB 인스턴스 식별자</th>';
            resultHtml += '<th width="15%">상태</th>';
            resultHtml += '<th width="45%">세부 정보</th>';
        } else if (hasLambdaFunctions) {
            resultHtml += '<th width="15%">리전</th>';
            resultHtml += '<th width="25%">함수 이름</th>';
            resultHtml += '<th width="15%">상태</th>';
            resultHtml += '<th width="45%">세부 정보</th>';
        } else if (hasIAMUsers || hasIAMPolicies) {
            if (hasIAMPolicies) {
                resultHtml += '<th width="30%">정책 이름</th>';
                resultHtml += '<th width="20%">상태</th>';
                resultHtml += '<th width="50%">세부 정보</th>';
            } else {
                resultHtml += '<th width="25%">사용자 이름</th>';
                resultHtml += '<th width="20%">상태</th>';
                resultHtml += '<th width="50%">세부 정보</th>';
            }
        } else if (hasEC2SecurityGroups) {
            resultHtml += '<th style="width: 80px; max-width: 80px;">리전</th>';
            resultHtml += '<th style="width: 280px; max-width: 280px;">보안그룹 이름</th>';
            resultHtml += '<th style="width: 160px; max-width: 160px;">보안그룹 ID</th>';
            resultHtml += '<th style="width: 70px; max-width: 70px;">상태</th>';
            resultHtml += '<th style="width: 350px;">세부 정보</th>';
        } else if (hasEBSVolumes) {
            resultHtml += '<th style="width: 100px; min-width: 100px;">리전</th>';
            resultHtml += '<th style="width: 200px; min-width: 200px;">볼륨 이름</th>';
            resultHtml += '<th style="width: 180px; min-width: 180px;">볼륨 ID</th>';
            resultHtml += '<th style="width: 120px; min-width: 120px;">상태</th>';
            resultHtml += '<th style="min-width: 300px;">세부 정보</th>';
        } else if (hasEC2Instances) {
            resultHtml += '<th style="width: 80px; max-width: 80px;">리전</th>';
            resultHtml += '<th style="width: 150px; max-width: 150px;">인스턴스 이름</th>';
            resultHtml += '<th style="width: 90px; max-width: 90px;">인스턴스 ID</th>';
            resultHtml += '<th style="width: 80px; max-width: 80px;">상태</th>';
            resultHtml += '<th style="width: 500px;">세부 정보</th>';
        } else if (hasUnusedResources) {
            resultHtml += '<th style="width: 80px; max-width: 80px;">리전</th>';
            resultHtml += '<th style="width: 100px; max-width: 100px;">리소스 이름</th>';
            resultHtml += '<th style="width: 160px; max-width: 160px;">리소스 ID</th>';
            resultHtml += '<th style="width: 80px; max-width: 80px;">상태</th>';
            resultHtml += '<th style="width: 480px;">세부 정보</th>';
        } else if (hasReservedInstances) {
            resultHtml += '<th width="15%">인스턴스 타입</th>';
            resultHtml += '<th width="10%">개수</th>';
            resultHtml += '<th width="15%">가용 영역</th>';
            resultHtml += '<th width="10%">만료일</th>';
            resultHtml += '<th width="10%">사용률</th>';
            resultHtml += '<th width="10%">상태</th>';
            resultHtml += '<th width="25%">세부 정보</th>';
        } else if (hasRDSEngineVersions) {
            resultHtml += '<th width="10%">리전</th>';
            resultHtml += '<th width="20%">DB 식별자</th>';
            resultHtml += '<th width="15%">엔진</th>';
            resultHtml += '<th width="15%">현재 버전</th>';
            resultHtml += '<th width="15%">최신 버전</th>';
            resultHtml += '<th width="10%">상태</th>';
            resultHtml += '<th width="15%">세부 정보</th>';
        } else {
            resultHtml += '<th style="width: 80px; max-width: 80px;">리전</th>';
            resultHtml += '<th style="width: 280px; max-width: 280px;">리소스 ID</th>';
            resultHtml += '<th style="width: 80px; max-width: 80px;">상태</th>';
            resultHtml += '<th style="width: 460px;">세부 정보</th>';
        }
        resultHtml += '</tr>';
        resultHtml += '</thead>';
        resultHtml += '<tbody>';
        
        resources.forEach(resource => {
            let resourceStatusClass = '';
            let resourceStatusIcon = '';
            
            if (resource.status === 'pass') {
                resourceStatusClass = 'success';
                resourceStatusIcon = '<i class="fas fa-check-circle text-success"></i>';
            } else if (resource.status === 'fail') {
                resourceStatusClass = 'danger';
                resourceStatusIcon = '<i class="fas fa-exclamation-triangle text-danger"></i>';
            } else if (resource.status === 'warning') {
                resourceStatusClass = 'danger';
                resourceStatusIcon = '<i class="fas fa-exclamation-triangle text-danger"></i>';
            } else {
                resourceStatusClass = 'secondary';
                resourceStatusIcon = '<i class="fas fa-question-circle text-secondary"></i>';
            }
            
            // 리소스 ID 추출
            const resourceId = resource.id || resource.user_name || resource.role_name || resource.policy_name || resource.bucket_name || resource.instance_id || resource.function_name || '';
            
            resultHtml += `<tr class="table-${resourceStatusClass}">`;
            resultHtml += `<td class="text-center">${resourceStatusIcon}</td>`;
            // S3 버킷, RDS 인스턴스, Lambda 함수의 경우 이름과 ID를 하나로 표시
            if (resource.bucket_name) {
                resultHtml += `<td>${resource.region || 'N/A'}</td>`;
                resultHtml += `<td><code>${resource.bucket_name}</code></td>`;
            } else if (resource.instance_id && resource.engine) {
                resultHtml += `<td>${resource.region || 'N/A'}</td>`;
                resultHtml += `<td><code>${resource.instance_id}</code></td>`;
            } else if (resource.function_name || resource.memory_size !== undefined) {
                const functionName = resource.function_name || resourceId;
                resultHtml += `<td>${resource.region || 'N/A'}</td>`;
                resultHtml += `<td><code>${functionName}</code></td>`;
            } else if (resource.user_name) {
                resultHtml += `<td><code>${resource.user_name}</code></td>`;
            } else if (resource.policy_name) {
                resultHtml += `<td><code>${resource.policy_name}</code></td>`;
            } else if (resource.sg_name && resource.sg_id) {
                resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
                resultHtml += `<td style="word-break: break-word; white-space: normal; max-width: 280px;">${resource.sg_name}</td>`;
                resultHtml += `<td style="word-break: break-all; white-space: normal; max-width: 160px;"><code>${resource.sg_id}</code></td>`;
            } else if (resource.volume_name && resource.volume_id) {
                resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
                resultHtml += `<td>${resource.volume_name}</td>`;
                resultHtml += `<td><code>${resource.volume_id}</code></td>`;
            } else if (resource.instance_name && resource.instance_id) {
                resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
                resultHtml += `<td>${resource.instance_name}</td>`;
                resultHtml += `<td><code>${resource.instance_id}</code></td>`;
            } else if (resource.resource_type && (resource.resource_type === 'Elastic IP' || resource.resource_type === 'EBS Volume')) {
                let displayName = '-';
                let displayId = resourceId;
                
                if (resource.resource_type === 'Elastic IP') {
                    displayName = resource.eip_name || '-';
                    displayId = resource.allocation_id || resourceId;
                } else if (resource.resource_type === 'EBS Volume') {
                    displayName = resource.volume_name || '-';
                    displayId = resource.volume_id || resourceId;
                }
                
                resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
                resultHtml += `<td>${displayName}</td>`;
                resultHtml += `<td><code>${displayId}</code></td>`;
            } else if (resource.ri_id) {
                const instanceType = resource.instance_type || 'N/A';
                const instanceCount = resource.instance_count || 0;
                const availabilityZone = resource.availability_zone || 'N/A';
                const daysUntilExpiry = resource.days_until_expiry || 0;
                const utilization = resource.utilization || 0;
                
                resultHtml += `<td><code>${instanceType}</code></td>`;
                resultHtml += `<td>${instanceCount}</td>`;
                resultHtml += `<td>${availabilityZone}</td>`;
                resultHtml += `<td>${daysUntilExpiry}일</td>`;
                resultHtml += `<td>${utilization.toFixed(1)}%</td>`;
            } else if (resource.db_identifier && resource.engine) {
                const dbIdentifier = resource.db_identifier || resourceId;
                const engine = resource.engine || 'N/A';
                const currentVersion = resource.current_version || 'N/A';
                const latestVersion = resource.latest_version || 'N/A';
                
                resultHtml += `<td>${resource.region || 'N/A'}</td>`;
                resultHtml += `<td><code>${dbIdentifier}</code></td>`;
                resultHtml += `<td>${engine}</td>`;
                resultHtml += `<td>${currentVersion}</td>`;
                resultHtml += `<td>${latestVersion}</td>`;
            } else {
                resultHtml += `<td style="white-space: nowrap;">${resource.region || 'N/A'}</td>`;
                resultHtml += `<td><code>${resourceId}</code></td>`;
            }
            resultHtml += `<td>${resource.status_text || ''}</td>`;
            // 서비스별 추가 정보 표시
            let additionalInfo = '';
            
            // S3 버킷 정보
            if (resource.bucket_name) {
                if (resource.public_acl === true) {
                    additionalInfo = '<span class="badge bg-danger">퍼블릭 ACL</span> ';
                }
                if (resource.all_blocked === false) {
                    additionalInfo += '<span class="badge bg-warning">퍼블릭 액세스 차단 미설정</span>';
                }
            }
            
            // Lambda 함수 정보
            if (resource.function_name && resource.memory_size) {
                additionalInfo = `메모리: ${resource.memory_size}MB`;
                if (resource.avg_memory && resource.avg_memory !== 'N/A' && resource.avg_memory !== 'Error') {
                    additionalInfo += `, 평균 사용률: ${resource.avg_memory}%`;
                }
            }
            
            // IAM 사용자 정보
            if (resource.user_name) {
                if (resource.is_admin === true) {
                    additionalInfo = '<span class="badge bg-danger">관리자 권한</span> ';
                }
                if (resource.has_console_access === true && resource.has_mfa === false) {
                    additionalInfo += '<span class="badge bg-warning">MFA 미설정</span>';
                }
            }
            
            // RDS 인스턴스 정보
            if (resource.instance_id && resource.retention_period !== undefined) {
                additionalInfo = `백업 보존: ${resource.retention_period}일`;
                if (resource.engine) {
                    additionalInfo += `, 엔진: ${resource.engine}`;
                }
            }
            
            let adviceText = resource.advice ? resource.advice.replace(/보안\s*위협\s*발견\s*:?\s*/g, '').replace(/보안\s*위험\s*발견\s*:?\s*/g, '').trim() : '';
            
            // '있습니다.', '됩니다.', '세요.', '않습니다.', '없습니다.', '있지만,' 뒤에 줄바꿈 추가
            if (adviceText) {
                adviceText = adviceText.replace(/(있습니다\.|됩니다\.|세요\.|않습니다\.|없습니다\.|있지만,)\s*/g, '$1<br>');
                
                // 대상 버킷 정보를 더 보기 좋게 표시
                adviceText = adviceText.replace(/대상 버킷:\s*/g, '대상 버킷:<br>');
                adviceText = adviceText.replace(/, ([a-zA-Z0-9-]+)/g, ',<br>$1');
            }
            
            // 세부 정보를 두 줄로 나누어 표시
            let detailInfo = '';
            if (additionalInfo && adviceText) {
                detailInfo = `${additionalInfo}<br>${adviceText}`;
            } else if (additionalInfo) {
                detailInfo = additionalInfo;
            } else if (adviceText) {
                detailInfo = adviceText;
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
 * 검사 항목 클릭으로 체크박스 토글
 */
function initCheckItemClick() {
    const checkItems = document.querySelectorAll('.check-item');
    
    checkItems.forEach(item => {
        const checkbox = item.querySelector('.check-select');
        const header = item.querySelector('.check-item-header');
        const description = item.querySelector('.check-item-description');
        
        function toggleCheckbox(e) {
            // 버튼이나 체크박스 자체를 클릭한 경우는 제외
            if (e.target.closest('button') || e.target.closest('input[type="checkbox"]')) {
                return;
            }
            
            // 체크박스 토글
            checkbox.checked = !checkbox.checked;
            
            // 선택된 항목 수 업데이트
            updateSelectedCount();
        }
        
        if (header && checkbox) {
            header.addEventListener('click', toggleCheckbox);
            header.style.cursor = 'pointer';
        }
        
        if (description && checkbox) {
            description.addEventListener('click', toggleCheckbox);
            description.style.cursor = 'pointer';
        }
    });
}

/**
 * CSRF 토큰 가져오기
 * @returns {string} - CSRF 토큰
 */
function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}