// 데이터 수집 진행 상황 관련 JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // 메인 템플릿에서 비활성화 플래그를 확인
    if (window.preventCollectionProgressLoad) {
        console.log('collection-progress.js 비활성화됨');
        return; // 스크립트 실행 중단
    }
    
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