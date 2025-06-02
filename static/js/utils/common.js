/**
 * 공통 유틸리티 함수
 */

// 전역 네임스페이스 생성
const AWSConsoleCheck = {
    utils: {},
    components: {},
    pages: {}
};

/**
 * 툴팁 초기화 함수
 */
AWSConsoleCheck.utils.initTooltips = function() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    if (tooltipTriggerList.length > 0) {
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }
};

/**
 * 날짜 포맷팅 함수
 * @param {Date|string} date - 포맷팅할 날짜 객체 또는 문자열
 * @param {string} format - 포맷 형식 (기본값: 'YYYY-MM-DD')
 * @returns {string} 포맷팅된 날짜 문자열
 */
AWSConsoleCheck.utils.formatDate = function(date, format = 'YYYY-MM-DD') {
    if (!date) return '';
    
    const d = typeof date === 'string' ? new Date(date) : date;
    
    if (isNaN(d.getTime())) return '';
    
    const year = d.getFullYear();
    const month = String(d.getMonth() + 1).padStart(2, '0');
    const day = String(d.getDate()).padStart(2, '0');
    const hours = String(d.getHours()).padStart(2, '0');
    const minutes = String(d.getMinutes()).padStart(2, '0');
    const seconds = String(d.getSeconds()).padStart(2, '0');
    
    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
};

/**
 * 숫자 포맷팅 함수
 * @param {number} number - 포맷팅할 숫자
 * @param {number} decimals - 소수점 자릿수 (기본값: 0)
 * @param {string} decimalPoint - 소수점 구분자 (기본값: '.')
 * @param {string} thousandsSep - 천 단위 구분자 (기본값: ',')
 * @returns {string} 포맷팅된 숫자 문자열
 */
AWSConsoleCheck.utils.formatNumber = function(number, decimals = 0, decimalPoint = '.', thousandsSep = ',') {
    if (number === null || number === undefined) return '';
    
    const n = Number(number);
    if (isNaN(n)) return '';
    
    const fixedNumber = n.toFixed(decimals);
    const parts = fixedNumber.split('.');
    
    parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, thousandsSep);
    
    return parts.join(decimalPoint);
};

/**
 * 문자열 자르기 함수
 * @param {string} str - 원본 문자열
 * @param {number} maxLength - 최대 길이
 * @param {string} suffix - 생략 부호 (기본값: '...')
 * @returns {string} 잘린 문자열
 */
AWSConsoleCheck.utils.truncateString = function(str, maxLength, suffix = '...') {
    if (!str) return '';
    if (str.length <= maxLength) return str;
    
    return str.substring(0, maxLength) + suffix;
};

/**
 * 페이지 로드 시 공통 초기화
 */
document.addEventListener('DOMContentLoaded', function() {
    // 툴팁 초기화
    AWSConsoleCheck.utils.initTooltips();
    
    // 비밀번호 토글 버튼 기능
    const togglePasswordButtons = document.querySelectorAll('.toggle-password');
    if (togglePasswordButtons) {
        togglePasswordButtons.forEach(button => {
            button.addEventListener('click', function() {
                const passwordInput = document.querySelector(this.getAttribute('data-target'));
                if (passwordInput.type === 'password') {
                    passwordInput.type = 'text';
                    this.textContent = '숨기기';
                } else {
                    passwordInput.type = 'password';
                    this.textContent = '보기';
                }
            });
        });
    }
    
    // 로그아웃 확인
    const logoutLink = document.querySelector('a[href*="logout"]');
    if (logoutLink) {
        logoutLink.addEventListener('click', function(e) {
            if (!confirm('로그아웃 하시겠습니까?')) {
                e.preventDefault();
            }
        });
    }
});