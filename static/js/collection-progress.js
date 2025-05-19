// 데이터 수집 진행 상황 관련 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 데이터 수집 기능 추가
    const startCollectionBtn = document.getElementById('start-collection');
    const progressContainer = document.getElementById('collection-progress-container');
    const currentServiceElement = document.getElementById('current-service');
    const progressBar = document.getElementById('progress-bar');
    const completedCountElement = document.getElementById('completed-count');
    const totalServicesElement = document.getElementById('total-services');
    const completedServicesList = document.getElementById('completed-services-list');
    const autoRefreshToggle = document.getElementById('auto-refresh');
    
    // 현재 페이지 확인
    const isConsolidatedPage = window.location.pathname.includes('/consolidated');
    
    // 서비스 ID와 이름 매핑
    const serviceMapping = {
        'EC2': 'ec2',
        'S3': 's3',
        'RDS': 'rds',
        'Lambda': 'lambda',
        'CloudWatch': 'cloudwatch',
        'IAM': 'iam',
        'DynamoDB': 'dynamodb',
        'ECS': 'ecs',
        'EKS': 'eks',
        'SNS': 'sns',
        'SQS': 'sqs',
        'API Gateway': 'apigateway',
        'ElastiCache': 'elasticache',
        'Route 53': 'route53'
    };
    
    // 데이터 수집 시작 버튼 이벤트 처리 - 통합 대시보드 페이지에서만 적용
    if (startCollectionBtn && isConsolidatedPage) {
        startCollectionBtn.addEventListener('click', function() {
            // 버튼 비활성화
            startCollectionBtn.disabled = true;
            startCollectionBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> 수집 시작 중...';
            
            // 자동 새로고침 비활성화
            if (autoRefreshToggle) {
                autoRefreshToggle.checked = false;
                autoRefreshToggle.disabled = true;
                if (typeof stopAutoRefresh === 'function') {
                    stopAutoRefresh();
                }
            }
            
            // 한국 시간 기준으로 고유 ID 생성
            const now = new Date();
            const koreaTime = new Date(now.getTime() + (9 * 60 * 60 * 1000)); // UTC+9 (한국 시간)
            const collectionId = `${koreaTime.getFullYear()}${String(koreaTime.getMonth() + 1).padStart(2, '0')}${String(koreaTime.getDate()).padStart(2, '0')}_${String(koreaTime.getHours()).padStart(2, '0')}${String(koreaTime.getMinutes()).padStart(2, '0')}${String(koreaTime.getSeconds()).padStart(2, '0')}`;
            
            console.log(`데이터 수집 ID: ${collectionId}`);
            
            // 데이터 수집 시작 요청 (ID 포함 및 서비스 선택)
            // 서비스 선택 목록 가져오기
            const selectedServices = [];
            document.querySelectorAll('.service-checkbox').forEach(checkbox => {
                if (checkbox.checked) {
                    selectedServices.push(checkbox.value);
                }
            });
            
            // 선택된 서비스가 없는 경우
            if (selectedServices.length === 0) {
                alert('최소한 하나 이상의 서비스를 선택해야 합니다.');
                startCollectionBtn.disabled = false;
                startCollectionBtn.textContent = '데이터 수집';
                if (autoRefreshToggle) {
                    autoRefreshToggle.disabled = false;
                }
                return;
            }
            
            fetch('/start_collection', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    collectionId: collectionId,
                    selected_services: selectedServices
                }),
            })
            .then(response => response.json())
            .then(data => {
                if (data.status === 'success') {
                    // 수집 시작 성공
                    console.log('데이터 수집이 시작되었습니다.');
                    
                    // 모달 표시 (페이지 새로고침 대신)
                    showProgressModal(selectedServices);
                } else {
                    // 오류 발생 - 서버 오류는 표시하지 않음 (이미 클라이언트에서 검증함)
                    if (data.message !== '최소한 하나 이상의 서비스를 선택해야 합니다.') {
                        alert('오류: ' + data.message);
                    }
                    startCollectionBtn.disabled = false;
                    startCollectionBtn.textContent = '데이터 수집';
                    
                    // 자동 새로고침 다시 활성화
                    if (autoRefreshToggle) {
                        autoRefreshToggle.disabled = false;
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
                alert('데이터 수집 요청 중 오류가 발생했습니다.');
                startCollectionBtn.disabled = false;
                startCollectionBtn.textContent = '데이터 수집';
                
                // 자동 새로고침 다시 활성화
                if (autoRefreshToggle) {
                    autoRefreshToggle.disabled = false;
                }
            });
        });
    }
    
    // 진행 상황 모달 표시 함수
    function showProgressModal(selectedServices) {
        // 모달 객체 생성
        const selectServicesModal = new bootstrap.Modal(document.getElementById('selectServicesModal'));
        
        // 모달이 이미 열려있지 않다면 열기
        if (!document.querySelector('.modal.show')) {
            selectServicesModal.show();
        }
        
        // 모달 내용을 진행 상황 표시로 변경
        const modalBody = document.querySelector('#selectServicesModal .modal-body');
        const modalTitle = document.querySelector('#selectServicesModal .modal-title');
        const modalFooter = document.querySelector('#selectServicesModal .modal-footer');
        
        modalTitle.textContent = '데이터 수집 진행 중';
        
        // 진행 상황 표시 HTML 생성
        modalBody.innerHTML = `
            <p>선택한 서비스의 데이터를 수집하고 있습니다.</p>
            <p>현재 수집 중인 서비스: <strong id="modal-current-service">준비 중...</strong></p>
            <div class="progress mb-3">
                <div id="modal-progress-bar" class="progress-bar progress-bar-striped progress-bar-animated" 
                     role="progressbar" style="width: 0%;" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100">
                    0%
                </div>
            </div>
            <p>완료된 서비스: <span id="modal-completed-count">0</span> / <span id="modal-total-services">${selectedServices.length}</span></p>
            <div class="mb-2">
                <span class="badge bg-success me-1">완료됨</span>
                <span class="badge bg-primary me-1">수집 중</span>
                <span class="badge bg-secondary me-1">수집 예정</span>
            </div>
            <div id="modal-completed-services-list"></div>
        `;
        
        // 모달 푸터 변경
        modalFooter.innerHTML = `
            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">백그라운드에서 계속</button>
        `;
        
        // 상태 확인 시작
        startModalStatusCheck(selectedServices);
    }
    
    // 모달 상태 확인 함수
    function startModalStatusCheck(selectedServices) {
        // 이전 인터벌이 있으면 제거
        if (window.modalStatusCheckInterval) {
            clearInterval(window.modalStatusCheckInterval);
        }
        
        // 새로운 인터벌 시작
        window.modalStatusCheckInterval = setInterval(() => checkModalCollectionStatus(selectedServices), 1000);
        // 즉시 한 번 확인
        checkModalCollectionStatus(selectedServices);
    }
    
    // 모달 내 수집 상태 확인 함수
    function checkModalCollectionStatus(selectedServices) {
        fetch('/collection_status')
            .then(response => response.json())
            .then(data => {
                // 모달 내 요소 업데이트
                const currentServiceElement = document.getElementById('modal-current-service');
                const progressBarElement = document.getElementById('modal-progress-bar');
                const completedCountElement = document.getElementById('modal-completed-count');
                const totalServicesElement = document.getElementById('modal-total-services');
                const completedServicesListElement = document.getElementById('modal-completed-services-list');
                
                if (data.is_collecting) {
                    // 수집 중인 경우
                    if (currentServiceElement) currentServiceElement.textContent = data.current_service || '준비 중...';
                    
                    // 진행률 계산 및 업데이트
                    const progress = data.progress || 0;
                    
                    if (progressBarElement) {
                        progressBarElement.style.width = `${progress}%`;
                        progressBarElement.textContent = `${progress}%`;
                        progressBarElement.setAttribute('aria-valuenow', progress);
                    }
                    
                    // 완료된 서비스 수 업데이트 - 중복 제거 후 계산
                    const uniqueCompletedServices = new Set(data.completed_services);
                    if (completedCountElement) completedCountElement.textContent = uniqueCompletedServices.size;
                    if (totalServicesElement) totalServicesElement.textContent = selectedServices.length;
                    
                    // 완료된 서비스 목록 업데이트
                    if (completedServicesListElement) {
                        completedServicesListElement.innerHTML = '';
                        
                        // 서비스 이름 역매핑 (코드 -> 표시 이름)
                        const reverseMapping = {};
                        Object.entries(serviceMapping).forEach(([displayName, code]) => {
                            reverseMapping[code] = displayName;
                        });
                        
                        // 이미 표시된 서비스 추적
                        const displayedServices = new Set();
                        
                        // 완료된 서비스 배지 추가
                        data.completed_services.forEach(serviceName => {
                            if (!displayedServices.has(serviceName)) {
                                displayedServices.add(serviceName);
                                const badge = document.createElement('span');
                                badge.className = 'badge bg-success me-1 mb-1';
                                badge.textContent = serviceName;
                                completedServicesListElement.appendChild(badge);
                            }
                        });
                        
                        // 현재 수집 중인 서비스 배지 추가
                        if (data.current_service && !displayedServices.has(data.current_service)) {
                            displayedServices.add(data.current_service);
                            const badge = document.createElement('span');
                            badge.className = 'badge bg-primary me-1 mb-1';
                            badge.textContent = data.current_service + ' (수집 중)';
                            completedServicesListElement.appendChild(badge);
                        }
                        
                        // 수집 예정인 서비스 배지 추가
                        selectedServices.forEach(serviceCode => {
                            const serviceName = reverseMapping[serviceCode];
                            if (serviceName && !displayedServices.has(serviceName)) {
                                displayedServices.add(serviceName);
                                const badge = document.createElement('span');
                                badge.className = 'badge bg-secondary me-1 mb-1';
                                badge.textContent = serviceName;
                                completedServicesListElement.appendChild(badge);
                            }
                        });
                    }
                } else {
                    // 수집이 완료된 경우
                    if (data.error) {
                        // 오류가 있는 경우
                        const modalBody = document.querySelector('#selectServicesModal .modal-body');
                        if (modalBody) {
                            modalBody.innerHTML += `<div class="alert alert-danger mt-3">오류: ${data.error}</div>`;
                        }
                    } else if (data.completed_services && data.completed_services.length > 0) {
                        // 수집이 성공적으로 완료된 경우
                        const modalBody = document.querySelector('#selectServicesModal .modal-body');
                        if (modalBody) {
                            modalBody.innerHTML += `<div class="alert alert-success mt-3">데이터 수집이 완료되었습니다!</div>`;
                            
                            // 모달 푸터 변경
                            const modalFooter = document.querySelector('#selectServicesModal .modal-footer');
                            if (modalFooter) {
                                modalFooter.innerHTML = `
                                    <button type="button" class="btn btn-primary" onclick="window.location.reload()">결과 보기</button>
                                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">닫기</button>
                                `;
                            }
                        }
                    }
                    
                    // 상태 확인 중지
                    clearInterval(window.modalStatusCheckInterval);
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    // 데이터 수집 진행 상황 업데이트 함수 (페이지 내 표시용)
    function updateCollectionProgress() {
        if (!progressContainer) return;
        
        fetch('/collection_status')
            .then(response => response.json())
            .then(data => {
                // 현재 수집 중인 서비스 업데이트
                if (currentServiceElement) {
                    currentServiceElement.textContent = data.current_service || '완료됨';
                }
                
                // 진행률 업데이트
                if (progressBar) {
                    const percent = data.progress || 0;
                    progressBar.style.width = `${percent}%`;
                    progressBar.setAttribute('aria-valuenow', percent);
                    progressBar.textContent = `${percent}%`;
                }
                
                // 완료된 서비스 수 업데이트
                if (completedCountElement) {
                    completedCountElement.textContent = data.completed_services.length;
                }
                
                // 완료된 서비스 목록 업데이트
                if (completedServicesList) {
                    completedServicesList.innerHTML = '';
                    
                    // 완료된 서비스 배지 추가
                    data.completed_services.forEach(service => {
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-success me-1 mb-1';
                        badge.textContent = service;
                        completedServicesList.appendChild(badge);
                    });
                    
                    // 수집 예정인 서비스 배지 추가 (완료되지 않은 서비스)
                    const allServices = Object.keys(serviceMapping);
                    const pendingServices = allServices.filter(service => 
                        !data.completed_services.includes(service) && 
                        service !== data.current_service
                    );
                    
                    pendingServices.forEach(service => {
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-pending me-1 mb-1';
                        badge.textContent = service;
                        completedServicesList.appendChild(badge);
                    });
                    
                    // 현재 수집 중인 서비스 배지 추가
                    if (data.current_service) {
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-primary me-1 mb-1';
                        badge.textContent = data.current_service + ' (수집 중)';
                        completedServicesList.appendChild(badge);
                    }
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
    }
    
    // 데이터 수집 중인 경우 주기적으로 진행 상황 업데이트
    if (progressContainer) {
        // 3초마다 진행 상황 업데이트
        setInterval(updateCollectionProgress, 3000);
        // 초기 로드 시 한 번 업데이트
        updateCollectionProgress();
    }
});