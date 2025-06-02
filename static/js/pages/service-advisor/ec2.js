/**
 * EC2 서비스 어드바이저 기능
 */

// EC2 어드바이저 네임스페이스
AWSConsoleCheck.pages.serviceAdvisor.ec2 = {};

document.addEventListener('DOMContentLoaded', function() {
    // EC2 인스턴스 카드 토글 기능
    initEc2InstanceCards();
    
    // EC2 사용량 차트 초기화
    initEc2UsageCharts();
    
    // EC2 권장 사항 필터링
    initEc2RecommendationFilters();
    
    // 스캔 버튼 이벤트 처리
    initScanButtons();
});

/**
 * 스캔 버튼 초기화
 */
function initScanButtons() {
    const scanButtons = document.querySelectorAll('.scan-button');
    
    scanButtons.forEach(button => {
        button.addEventListener('click', function() {
            const serviceType = this.getAttribute('data-service-type');
            const scanUrl = this.getAttribute('data-scan-url');
            
            if (!serviceType || !scanUrl) {
                console.error('Missing service type or scan URL');
                return;
            }
            
            // 버튼 상태 업데이트
            this.disabled = true;
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 검사 중...';
            
            // AJAX 요청으로 검사 시작
            fetch(scanUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ service_type: serviceType })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    // 검사 결과 페이지로 이동
                    window.location.href = data.redirect_url;
                } else {
                    // 오류 메시지 표시
                    alert(data.message || '서비스 검사 중 오류가 발생했습니다.');
                    
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error('Error during scan:', error);
                alert('서비스 검사 중 오류가 발생했습니다.');
                
                // 버튼 상태 복원
                this.disabled = false;
                this.innerHTML = originalText;
            });
        });
    });
}

/**
 * CSRF 토큰 가져오기
 */
function getCsrfToken() {
    const csrfInput = document.querySelector('input[name="csrf_token"]');
    return csrfInput ? csrfInput.value : '';
}

/**
 * EC2 인스턴스 카드 토글 기능 초기화
 */
function initEc2InstanceCards() {
    const instanceHeaders = document.querySelectorAll('.ec2-instance-header');
    
    instanceHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const card = this.closest('.ec2-instance-card');
            const body = card.querySelector('.ec2-instance-body');
            const icon = this.querySelector('.toggle-icon i');
            
            if (body.style.display === 'none') {
                body.style.display = 'block';
                if (icon) {
                    icon.className = 'fas fa-chevron-up';
                }
            } else {
                body.style.display = 'none';
                if (icon) {
                    icon.className = 'fas fa-chevron-down';
                }
            }
        });
    });
}

/**
 * EC2 사용량 차트 초기화
 */
function initEc2UsageCharts() {
    const chartContainers = document.querySelectorAll('.ec2-usage-chart');
    
    chartContainers.forEach(container => {
        const instanceId = container.getAttribute('data-instance-id');
        const chartType = container.getAttribute('data-chart-type') || 'cpu';
        
        if (!instanceId) {
            console.error('Missing instance ID for chart');
            return;
        }
        
        // 차트 데이터 가져오기
        fetchEc2ChartData(instanceId, chartType)
            .then(data => {
                if (data && data.labels && data.datasets) {
                    renderEc2Chart(container, data);
                }
            })
            .catch(error => {
                console.error('Error fetching chart data:', error);
                container.innerHTML = '<div class="text-center text-muted py-4">차트 데이터를 불러올 수 없습니다.</div>';
            });
    });
}

/**
 * EC2 차트 데이터 가져오기
 * @param {string} instanceId - EC2 인스턴스 ID
 * @param {string} chartType - 차트 유형 (cpu, memory, network, disk)
 * @returns {Promise} - 차트 데이터 Promise
 */
function fetchEc2ChartData(instanceId, chartType) {
    const url = `/api/service-advisor/ec2/${instanceId}/metrics?type=${chartType}`;
    
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        });
}

/**
 * EC2 차트 렌더링
 * @param {HTMLElement} container - 차트 컨테이너 요소
 * @param {Object} data - 차트 데이터
 */
function renderEc2Chart(container, data) {
    // Chart.js가 로드되어 있는지 확인
    if (typeof Chart === 'undefined') {
        console.error('Chart.js is not loaded');
        container.innerHTML = '<div class="text-center text-muted py-4">차트 라이브러리를 불러올 수 없습니다.</div>';
        return;
    }
    
    // 캔버스 요소 생성
    const canvas = document.createElement('canvas');
    container.appendChild(canvas);
    
    // 차트 생성
    new Chart(canvas, {
        type: 'line',
        data: data,
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    grid: {
                        display: false
                    }
                },
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value + '%';
                        }
                    }
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    mode: 'index',
                    intersect: false
                }
            }
        }
    });
}

/**
 * EC2 권장 사항 필터링 초기화
 */
function initEc2RecommendationFilters() {
    const filterButtons = document.querySelectorAll('.ec2-filter-button');
    const recommendationCards = document.querySelectorAll('.recommendation-card');
    
    filterButtons.forEach(button => {
        button.addEventListener('click', function() {
            const filterValue = this.getAttribute('data-filter');
            
            // 버튼 활성화 상태 업데이트
            filterButtons.forEach(btn => {
                btn.classList.remove('selected');
            });
            this.classList.add('selected');
            
            // 권장 사항 필터링
            recommendationCards.forEach(card => {
                if (filterValue === 'all') {
                    card.style.display = 'block';
                } else {
                    const cardSeverity = card.getAttribute('data-severity');
                    card.style.display = (cardSeverity === filterValue) ? 'block' : 'none';
                }
            });
        });
    });
}