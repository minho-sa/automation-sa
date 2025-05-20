document.addEventListener('DOMContentLoaded', function() {
    // EC2 섹션 헤더에 수동 토글 기능 추가
    const ec2Header = document.querySelector('#ec2-section .awsui-card-header');
    const ec2Content = document.querySelector('#ec2-content');
    const toggleIcon = ec2Header.querySelector('.toggle-icon i');
    
    ec2Header.addEventListener('click', function() {
        // 콘텐츠 토글
        if (ec2Content.classList.contains('show')) {
            ec2Content.classList.remove('show');
            this.setAttribute('aria-expanded', 'false');
            toggleIcon.style.transform = 'rotate(0deg)';
        } else {
            ec2Content.classList.add('show');
            this.setAttribute('aria-expanded', 'true');
            toggleIcon.style.transform = 'rotate(180deg)';
        }
    });
});