/**
 * S3 서비스 어드바이저 페이지 스크립트
 */

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    // 공통 기능 초기화
    initCheckItems();
    initCheckItemHover();
    initRunCheckButtons();
    initSelectAllChecks();
    initRunSelectedChecks();
    
    // 최신 검사 결과 로드
    loadLatestCheckResults();
});