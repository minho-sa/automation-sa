/**
 * 서비스 어드바이저 공통 기능
 * 모든 서비스에서 공통으로 사용하는 기능을 정의합니다.
 */
class ServiceAdvisorCommon {
  constructor() {
    this.results = {};
  }

  // 초기화 함수
  init() {
    this.setupEventListeners();
  }

  // 이벤트 리스너 설정
  setupEventListeners() {
    const selectAllCheckbox = document.getElementById('select-all-checks');
    if (selectAllCheckbox) {
      selectAllCheckbox.addEventListener('change', (e) => this.handleSelectAll(e));
    }
    
    const runSelectedChecksBtn = document.getElementById('run-selected-checks');
    if (runSelectedChecksBtn) {
      runSelectedChecksBtn.addEventListener('click', () => this.runSelectedChecks());
    }
    
    document.querySelectorAll('.run-check-btn').forEach(button => {
      button.addEventListener('click', (e) => {
        const checkId = e.currentTarget.getAttribute('data-check-id');
        this.runCheck(checkId);
      });
    });
  }

  // 전체 선택 처리
  handleSelectAll(event) {
    const isChecked = event.target.checked;
    document.querySelectorAll('.check-select').forEach(checkbox => {
      checkbox.checked = isChecked;
    });
  }

  // 선택된 검사 항목 실행
  runSelectedChecks() {
    const selectedChecks = Array.from(document.querySelectorAll('.check-select:checked'))
      .map(checkbox => checkbox.getAttribute('data-check-id'));
    
    if (selectedChecks.length === 0) {
      alert('검사할 항목을 선택해주세요.');
      return;
    }
    
    selectedChecks.forEach(checkId => {
      this.runCheck(checkId);
    });
  }

  // 검사 실행 (서비스별로 오버라이드 필요)
  runCheck(checkId) {
    console.error('runCheck 메서드는 서비스별 클래스에서 구현해야 합니다.');
  }

  // 결과 HTML 생성 (기본 구현)
  generateResultHtml(checkId) {
    const data = this.results[checkId];
    if (!data) return '';
    
    // 결과 상태에 따른 스타일 설정
    let statusClass = '';
    let statusIcon = '';
    
    switch(data.status) {
      case 'ok':
        statusClass = 'success';
        statusIcon = 'check-circle';
        break;
      case 'warning':
        statusClass = 'warning';
        statusIcon = 'exclamation-triangle';
        break;
      case 'error':
        statusClass = 'danger';
        statusIcon = 'times-circle';
        break;
      case 'info':
        statusClass = 'info';
        statusIcon = 'info-circle';
        break;
      default:
        statusClass = 'secondary';
        statusIcon = 'question-circle';
    }
    
    // 결과 HTML 생성
    let resultHtml = `
      <div class="check-result-status ${statusClass}">
        <i class="fas fa-${statusIcon}"></i>
        <span>${data.message}</span>
      </div>
    `;
    
    // 권장 사항이 있는 경우
    if (data.recommendations && data.recommendations.length > 0) {
      resultHtml += `
        <div class="check-result-recommendations">
          <h4>권장 사항</h4>
          <ul>
            ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
          </ul>
        </div>
      `;
    }
    
    return resultHtml;
  }

  // 날짜 포맷팅 유틸리티 함수
  formatDate(date) {
    return date.toLocaleDateString('ko-KR', { 
      year: 'numeric', 
      month: '2-digit', 
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  }
}