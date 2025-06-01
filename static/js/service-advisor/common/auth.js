/**
 * 서비스 어드바이저 인증 관련 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 페이지 로드 시 자격증명 검증
    validateCredentials();
    
    // 자격증명 검증 버튼 이벤트 리스너 등록
    const validateButton = document.getElementById('validate-credentials');
    if (validateButton) {
        validateButton.addEventListener('click', function() {
            validateCredentials();
        });
    }
});

/**
 * AWS 자격증명 유효성 검증
 */
function validateCredentials() {
    // 상태 표시 요소
    const statusElement = document.getElementById('credentials-status');
    if (!statusElement) return;
    
    // 로딩 상태 표시
    statusElement.innerHTML = '<span class="text-warning"><i class="fas fa-spinner fa-spin"></i> 자격증명 검증 중...</span>';
    
    // API 호출
    fetch('/api/validate-credentials')
        .then(response => response.json())
        .then(data => {
            if (data.valid) {
                // 유효한 자격증명
                statusElement.innerHTML = `
                    <span class="text-success">
                        <i class="fas fa-check-circle"></i> 자격증명 유효함
                    </span>
                    <small class="d-block text-muted">
                        계정: ${data.identity.account_id} | 역할: ${data.identity.role_name}
                    </small>
                `;
                
                // 서비스 어드바이저 기능 활성화
                enableServiceAdvisor();
            } else {
                // 유효하지 않은 자격증명
                statusElement.innerHTML = `
                    <span class="text-danger">
                        <i class="fas fa-exclamation-circle"></i> ${data.message}
                    </span>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="window.location.href='/logout'">
                        다시 로그인
                    </button>
                `;
                
                // 서비스 어드바이저 기능 비활성화
                disableServiceAdvisor();
            }
        })
        .catch(error => {
            console.error('자격증명 검증 중 오류 발생:', error);
            statusElement.innerHTML = `
                <span class="text-danger">
                    <i class="fas fa-exclamation-triangle"></i> 자격증명 검증 중 오류가 발생했습니다.
                </span>
                <button class="btn btn-sm btn-outline-primary mt-2" onclick="validateCredentials()">
                    다시 시도
                </button>
            `;
            
            // 서비스 어드바이저 기능 비활성화
            disableServiceAdvisor();
        });
}

/**
 * 서비스 어드바이저 기능 활성화
 */
function enableServiceAdvisor() {
    // 서비스 어드바이저 관련 UI 요소 활성화
    const advisorElements = document.querySelectorAll('.service-advisor-feature');
    advisorElements.forEach(element => {
        element.classList.remove('disabled');
        element.removeAttribute('disabled');
    });
    
    // 서비스 어드바이저 버튼 활성화
    const advisorButtons = document.querySelectorAll('.service-advisor-button');
    advisorButtons.forEach(button => {
        button.classList.remove('disabled');
        button.removeAttribute('disabled');
    });
}

/**
 * 서비스 어드바이저 기능 비활성화
 */
function disableServiceAdvisor() {
    // 서비스 어드바이저 관련 UI 요소 비활성화
    const advisorElements = document.querySelectorAll('.service-advisor-feature');
    advisorElements.forEach(element => {
        element.classList.add('disabled');
        element.setAttribute('disabled', 'disabled');
    });
    
    // 서비스 어드바이저 버튼 비활성화
    const advisorButtons = document.querySelectorAll('.service-advisor-button');
    advisorButtons.forEach(button => {
        button.classList.add('disabled');
        button.setAttribute('disabled', 'disabled');
    });
}