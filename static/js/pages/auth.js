/**
 * 인증 페이지 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 비밀번호 표시/숨기기 토글 기능
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    
    togglePasswordButtons.forEach(button => {
        button.addEventListener('click', function() {
            const passwordInput = document.querySelector(this.getAttribute('data-target'));
            
            if (passwordInput) {
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.textContent = '숨기기';
                } else {
                    passwordInput.type = 'password';
                    this.textContent = '보기';
                }
            }
        });
    });
    
    // 로그인 폼 유효성 검사
    const loginForm = document.querySelector('#login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', function(event) {
            const username = document.getElementById('username').value.trim();
            const password = document.getElementById('password').value;
            
            if (!username || !password) {
                event.preventDefault();
                alert('사용자 ID와 비밀번호를 모두 입력해주세요.');
            }
        });
        
        // 자동 포커스
        document.getElementById('username').focus();
    }
    
    // 회원가입 폼 유효성 검사
    const registerForm = document.querySelector('#register-form');
    if (registerForm) {
        const passwordInput = document.getElementById('password');
        const confirmPasswordInput = document.getElementById('confirm_password');
        
        // 비밀번호 일치 여부 확인
        registerForm.addEventListener('submit', function(event) {
            if (passwordInput.value !== confirmPasswordInput.value) {
                event.preventDefault();
                alert('비밀번호와 비밀번호 확인이 일치하지 않습니다.');
            }
        });
        
        // 비밀번호 복잡성 실시간 검증
        if (passwordInput) {
            passwordInput.addEventListener('input', function() {
                const password = passwordInput.value;
                const hasUpperCase = /[A-Z]/.test(password);
                const hasLowerCase = /[a-z]/.test(password);
                const hasNumbers = /\d/.test(password);
                const hasSpecialChars = /[^A-Za-z0-9]/.test(password);
                const isLongEnough = password.length >= 8;
                
                let message = '';
                if (!isLongEnough) message += '• 최소 8자 이상이어야 합니다.<br>';
                if (!hasUpperCase) message += '• 대문자를 포함해야 합니다.<br>';
                if (!hasLowerCase) message += '• 소문자를 포함해야 합니다.<br>';
                if (!hasNumbers) message += '• 숫자를 포함해야 합니다.<br>';
                if (!hasSpecialChars) message += '• 특수문자를 포함해야 합니다.<br>';
                
                const formText = passwordInput.nextElementSibling;
                if (formText) {
                    if (message) {
                        formText.innerHTML = message;
                        formText.classList.add('text-danger');
                        formText.classList.remove('text-muted');
                    } else {
                        formText.innerHTML = '비밀번호가 요구사항을 충족합니다.';
                        formText.classList.add('text-success');
                        formText.classList.remove('text-danger', 'text-muted');
                    }
                }
            });
        }
    }
});