/**
 * ALB 서비스 어드바이저 기능
 */

// ALB 어드바이저 네임스페이스
AWSConsoleCheck.pages.serviceAdvisor.alb = {};

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
    
    // 검사 항목 호버 효과
    initCheckItemHover();
    
    // 검사 항목 클릭으로 체크박스 토글
    initCheckItemClick();
});