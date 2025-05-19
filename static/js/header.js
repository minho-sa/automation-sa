document.addEventListener('DOMContentLoaded', function() {
    // 모바일 메뉴 토글 버튼 기능 구현
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const headerNav = document.getElementById('headerNav');
    
    if (mobileMenuToggle && headerNav) {
        mobileMenuToggle.addEventListener('click', function() {
            headerNav.classList.toggle('show');
        });
    }
    
    // 화면 크기가 변경될 때 모바일 메뉴 상태 조정
    window.addEventListener('resize', function() {
        if (window.innerWidth > 768 && headerNav && headerNav.classList.contains('show')) {
            headerNav.classList.remove('show');
        }
    });
});