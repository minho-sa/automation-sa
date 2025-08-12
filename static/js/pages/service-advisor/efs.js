/**
 * EFS 서비스 어드바이저 JavaScript
 */

document.addEventListener('DOMContentLoaded', function() {
    // 공통 기능 초기화
    initCheckItems();
    initCheckItemHover();
    initRunCheckButtons();
    initSelectAllChecks();
    initRunSelectedChecks();
    initCheckItemClick();
    
    // 최신 검사 결과 로드
    loadLatestCheckResults();
    
    console.log('EFS 서비스 어드바이저 초기화 완료');
});