/**
 * 서비스 어드바이저 공통 기능
 */

// 서비스 어드바이저 네임스페이스
if (!AWSConsoleCheck.pages.serviceAdvisor) {
    AWSConsoleCheck.pages.serviceAdvisor = {};
}

document.addEventListener('DOMContentLoaded', function() {
    // 권장 사항 카드 토글 기능
    initRecommendationCards();
    
    // 검사 시작 버튼 이벤트 처리
    initScanButtons();
    
    // PDF 내보내기 기능
    initExportButtons();
});

/**
 * 권장 사항 카드 토글 기능 초기화
 */
function initRecommendationCards() {
    const recommendationHeaders = document.querySelectorAll('.recommendation-header');
    
    recommendationHeaders.forEach(header => {
        header.addEventListener('click', function() {
            const card = this.closest('.recommendation-card');
            const body = card.querySelector('.recommendation-body');
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
 * 검사 시작 버튼 이벤트 처리 초기화
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
                    showAlert('error', '검사 실패', data.message || '서비스 검사 중 오류가 발생했습니다.');
                    
                    // 버튼 상태 복원
                    this.disabled = false;
                    this.innerHTML = originalText;
                }
            })
            .catch(error => {
                console.error('Error during scan:', error);
                showAlert('error', '검사 실패', '서비스 검사 중 오류가 발생했습니다.');
                
                // 버튼 상태 복원
                this.disabled = false;
                this.innerHTML = originalText;
            });
        });
    });
}

/**
 * PDF 내보내기 버튼 초기화
 */
function initExportButtons() {
    const exportButtons = document.querySelectorAll('.export-pdf-button');
    
    exportButtons.forEach(button => {
        button.addEventListener('click', function() {
            const reportId = this.getAttribute('data-report-id');
            const exportUrl = this.getAttribute('data-export-url');
            
            if (!reportId || !exportUrl) {
                console.error('Missing report ID or export URL');
                return;
            }
            
            // 버튼 상태 업데이트
            this.disabled = true;
            const originalText = this.innerHTML;
            this.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 생성 중...';
            
            // AJAX 요청으로 PDF 생성
            fetch(exportUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCsrfToken()
                },
                body: JSON.stringify({ report_id: reportId })
            })
            .then(response => {
                if (response.ok) {
                    return response.blob();
                }
                throw new Error('PDF 생성 실패');
            })
            .then(blob => {
                // PDF 다운로드
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.style.display = 'none';
                a.href = url;
                a.download = `aws-advisor-report-${reportId}.pdf`;
                document.body.appendChild(a);
                a.click();
                window.URL.revokeObjectURL(url);
                
                // 버튼 상태 복원
                this.disabled = false;
                this.innerHTML = originalText;
            })
            .catch(error => {
                console.error('Error exporting PDF:', error);
                showAlert('error', 'PDF 생성 실패', 'PDF 생성 중 오류가 발생했습니다.');
                
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
 * 알림 메시지 표시
 * @param {string} type - 알림 유형 (info, success, warning, error)
 * @param {string} title - 알림 제목
 * @param {string} message - 알림 메시지
 */
function showAlert(type, title, message) {
    // 기존 알림 컨테이너 확인
    let alertContainer = document.querySelector('.alert-container');
    
    // 없으면 생성
    if (!alertContainer) {
        alertContainer = document.createElement('div');
        alertContainer.className = 'alert-container';
        document.body.appendChild(alertContainer);
    }
    
    // 알림 요소 생성
    const alertElement = document.createElement('div');
    alertElement.className = `awsui-alert awsui-alert-${type}`;
    alertElement.innerHTML = `
        <div class="awsui-alert-icon">
            <i class="fas fa-${type === 'info' ? 'info-circle' : type === 'success' ? 'check-circle' : type === 'warning' ? 'exclamation-triangle' : 'exclamation-circle'}"></i>
        </div>
        <div class="awsui-alert-content">
            <div class="awsui-alert-header">
                <h3>${title}</h3>
            </div>
            <div class="awsui-alert-message">
                ${message}
            </div>
        </div>
        <button type="button" class="awsui-alert-close">
            <i class="fas fa-times"></i>
        </button>
    `;
    
    // 알림 컨테이너에 추가
    alertContainer.appendChild(alertElement);
    
    // 닫기 버튼 이벤트 처리
    const closeButton = alertElement.querySelector('.awsui-alert-close');
    closeButton.addEventListener('click', function() {
        alertElement.style.opacity = '0';
        setTimeout(() => {
            alertElement.remove();
        }, 300);
    });
    
    // 자동 닫힘 설정
    setTimeout(() => {
        alertElement.style.opacity = '0';
        setTimeout(() => {
            alertElement.remove();
        }, 300);
    }, 5000);
    
    // 페이드 인 효과
    setTimeout(() => {
        alertElement.style.opacity = '1';
    }, 10);
}