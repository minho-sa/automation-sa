/**
 * 수집 데이터 UI 관련 JavaScript 모듈
 */

// 모듈 패턴 사용
const CollectionUI = (function() {
    /**
     * 수집 진행 상황 UI 업데이트
     * 
     * @param {Object} data - 수집 상태 데이터
     * @param {Object} elements - UI 요소 객체
     * @param {Object} serviceMapping - 서비스 ID와 이름 매핑
     */
    function updateProgressUI(data, elements, serviceMapping) {
        // 현재 수집 중인 서비스 업데이트
        if (elements.currentService) {
            elements.currentService.textContent = data.current_service || '준비 중...';
        }
        
        // 진행률 업데이트
        if (elements.progressBar) {
            const percent = data.progress || 0;
            elements.progressBar.style.width = `${percent}%`;
            elements.progressBar.setAttribute('aria-valuenow', percent);
            elements.progressBar.textContent = `${percent}%`;
        }
        
        // 완료된 서비스 수 업데이트
        if (elements.completedCount) {
            elements.completedCount.textContent = data.completed_services.length;
        }
        
        // 총 서비스 수 업데이트
        if (elements.totalServices) {
            elements.totalServices.textContent = data.total_services || 0;
        }
        
        // 완료된 서비스 목록 업데이트
        if (elements.servicesList) {
            elements.servicesList.innerHTML = '';
            
            // 이미 표시된 서비스 추적
            const displayedServices = new Set();
            
            // 완료된 서비스 배지 추가
            data.completed_services.forEach(service => {
                displayedServices.add(service);
                const badge = document.createElement('span');
                badge.className = 'badge bg-success me-1 mb-1';
                badge.textContent = service;
                elements.servicesList.appendChild(badge);
            });
            
            // 현재 수집 중인 서비스 배지 추가
            if (data.current_service && !displayedServices.has(data.current_service)) {
                displayedServices.add(data.current_service);
                const badge = document.createElement('span');
                badge.className = 'badge bg-primary me-1 mb-1';
                badge.textContent = data.current_service;
                elements.servicesList.appendChild(badge);
            }
            
            // 수집 예정인 서비스 배지 추가
            if (data.selected_services) {
                data.selected_services.forEach(serviceKey => {
                    const serviceName = serviceMapping[serviceKey];
                    if (serviceName && !displayedServices.has(serviceName)) {
                        displayedServices.add(serviceName);
                        const badge = document.createElement('span');
                        badge.className = 'badge bg-secondary me-1 mb-1';
                        badge.textContent = serviceName;
                        elements.servicesList.appendChild(badge);
                    }
                });
            }
        }
    }
    
    /**
     * 수집 완료 UI 업데이트
     * 
     * @param {Object} data - 수집 상태 데이터
     * @param {Object} elements - UI 요소 객체
     * @param {function} onComplete - 완료 시 콜백 함수
     */
    function updateCompletionUI(data, elements, onComplete) {
        if (elements.resultContainer) {
            elements.resultContainer.innerHTML = `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle me-2"></i>
                    <strong>성공:</strong> 데이터 수집이 완료되었습니다!
                </div>`;
        }
        
        if (onComplete) {
            setTimeout(() => {
                onComplete(data);
            }, 2000);
        }
    }
    
    /**
     * 수집 오류 UI 업데이트
     * 
     * @param {string} error - 오류 메시지
     * @param {Object} elements - UI 요소 객체
     * @param {function} onError - 오류 시 콜백 함수
     */
    function updateErrorUI(error, elements, onError) {
        if (elements.resultContainer) {
            elements.resultContainer.innerHTML = `
                <div class="alert alert-danger">
                    <i class="fas fa-exclamation-circle me-2"></i>
                    <strong>오류 발생:</strong> ${error}
                </div>`;
        }
        
        if (onError) {
            setTimeout(() => {
                onError(error);
            }, 3000);
        }
    }
    
    /**
     * 서비스 선택 UI 설정
     * 
     * @param {Object} options - 설정 옵션
     */
    function setupServiceSelectionUI(options) {
        const {
            selectAllBtn,
            deselectAllBtn,
            checkboxSelector,
            startBtn,
            onStart
        } = options;
        
        // 모두 선택 버튼
        if (selectAllBtn) {
            selectAllBtn.addEventListener('click', () => {
                document.querySelectorAll(checkboxSelector).forEach(checkbox => {
                    checkbox.checked = true;
                });
            });
        }
        
        // 모두 선택 해제 버튼
        if (deselectAllBtn) {
            deselectAllBtn.addEventListener('click', () => {
                document.querySelectorAll(checkboxSelector).forEach(checkbox => {
                    checkbox.checked = false;
                });
            });
        }
        
        // 시작 버튼
        if (startBtn) {
            startBtn.addEventListener('click', () => {
                // 선택된 서비스 목록 수집
                const selectedServices = [];
                document.querySelectorAll(checkboxSelector).forEach(checkbox => {
                    if (checkbox.checked) {
                        selectedServices.push(checkbox.value);
                    }
                });
                
                // 선택된 서비스가 없는 경우
                if (selectedServices.length === 0) {
                    alert('최소한 하나 이상의 서비스를 선택해야 합니다.');
                    return;
                }
                
                // 버튼 비활성화
                startBtn.disabled = true;
                startBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 처리 중...';
                
                // 시작 콜백 호출
                if (onStart) {
                    onStart(selectedServices, () => {
                        // 성공 시 버튼 상태 복원
                        startBtn.disabled = false;
                        startBtn.innerHTML = '<i class="fas fa-play"></i> 데이터 수집 시작';
                    }, () => {
                        // 오류 시 버튼 상태 복원
                        startBtn.disabled = false;
                        startBtn.innerHTML = '<i class="fas fa-play"></i> 데이터 수집 시작';
                    });
                }
            });
        }
    }
    
    /**
     * 수집 데이터 카드 생성
     * 
     * @param {Object} collection - 수집 데이터 객체
     * @param {function} onDelete - 삭제 버튼 클릭 시 콜백 함수
     * @returns {HTMLElement} 생성된 카드 요소
     */
    function createCollectionCard(collection, onDelete) {
        const card = document.createElement('div');
        card.className = 'col-md-6 col-lg-4';
        card.innerHTML = `
            <div class="awsui-card collection-card">
                <div class="awsui-card-header">
                    <h5><i class="fas fa-database me-2"></i>수집 데이터</h5>
                </div>
                <div class="awsui-card-body">
                    <p class="collection-timestamp mb-1">
                        <i class="far fa-clock me-1"></i>${formatDate(collection.timestamp)}
                    </p>
                    <p class="collection-id mb-3">
                        <i class="fas fa-fingerprint me-1"></i>ID: ${collection.collection_id}
                    </p>
                    
                    <div class="mb-3">
                        <p class="mb-2"><strong>수집된 서비스:</strong></p>
                        <div>
                            ${collection.selected_services.map(service => 
                                `<span class="service-badge">${service}</span>`
                            ).join('')}
                        </div>
                    </div>
                    
                    <div class="d-flex justify-content-between mt-3">
                        <a href="/service/${collection.collection_id}" class="awsui-button awsui-button-normal">
                            <i class="fas fa-eye me-1"></i>서비스 정보 보기
                        </a>
                        <button class="btn btn-sm btn-danger delete-collection-btn" data-collection-id="${collection.collection_id}">
                            <i class="fas fa-trash me-1"></i>삭제
                        </button>
                    </div>
                </div>
            </div>
        `;
        
        // 삭제 버튼 이벤트 리스너 등록
        const deleteBtn = card.querySelector('.delete-collection-btn');
        if (deleteBtn && onDelete) {
            deleteBtn.addEventListener('click', () => {
                const collectionId = deleteBtn.getAttribute('data-collection-id');
                if (confirm('이 수집 데이터를 삭제하시겠습니까? 이 작업은 되돌릴 수 없습니다.')) {
                    onDelete(collectionId);
                }
            });
        }
        
        return card;
    }
    
    // 공개 API
    return {
        updateProgressUI,
        updateCompletionUI,
        updateErrorUI,
        setupServiceSelectionUI,
        createCollectionCard
    };
})();