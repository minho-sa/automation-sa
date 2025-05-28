/**
 * 서비스 어드바이저 초기화 스크립트
 * 현재 페이지에 맞는 서비스 어드바이저 클래스를 초기화합니다.
 */
document.addEventListener('DOMContentLoaded', function() {
  // 현재 페이지 URL에서 서비스 타입 확인
  const currentPath = window.location.pathname;
  
  // 서비스 어드바이저 인스턴스 생성
  let advisor;
  
  if (currentPath.includes('/service-advisor/ec2')) {
    advisor = new ServiceAdvisorEC2();
  } else if (currentPath.includes('/service-advisor/lambda')) {
    advisor = new ServiceAdvisorLambda();
  } else if (currentPath.includes('/service-advisor')) {
    // 인덱스 페이지는 별도 초기화 필요 없음 (service-advisor/index.js에서 처리)
    return;
  } else {
    console.warn('알 수 없는 서비스 어드바이저 페이지입니다.');
    return;
  }
  
  // 어드바이저 초기화
  advisor.init();
});