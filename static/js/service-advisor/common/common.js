/**
 * 서비스 어드바이저 공통 JavaScript
 */

// 서비스 어드바이저 공통 클래스
class ServiceAdvisorCommon {
  constructor() {
    this.results = {};
    this.serviceName = this.getServiceNameFromUrl();
    this.initEventListeners();
    this.loadPreviousResults();
  }
  
  // URL에서 서비스 이름 추출
  getServiceNameFromUrl() {
    const pathParts = window.location.pathname.split('/');
    return pathParts[pathParts.length - 1];
  }
  
  // 이벤트 리스너 초기화
  initEventListeners() {
    // 검사 버튼 이벤트 리스너
    document.querySelectorAll('.run-check').forEach(button => {
      button.addEventListener('click', (e) => {
        const checkId = e.currentTarget.getAttribute('data-check-id');
        this.runCheck(checkId);
      });
    });
    
    // 모든 검사 실행 버튼 이벤트 리스너
    const runAllButton = document.getElementById('runAllChecks');
    if (runAllButton) {
      runAllButton.addEventListener('click', () => {
        this.runAllChecks();
      });
    }
  }
  
  // 이전 검사 결과 로드
  loadPreviousResults() {
    const checks = document.querySelectorAll('.check-card');
    checks.forEach(check => {
      const checkId = check.getAttribute('data-check-id');
      if (!checkId) return;
      
      console.log(`로딩 시작: ${this.serviceName}/${checkId}`);
      
      // API를 통해 최근 검사 결과 가져오기
      fetch(`/api/service-advisor/history/${this.serviceName}/${checkId}`)
        .then(response => response.json())
        .then(data => {
          console.log(`로딩 결과: ${this.serviceName}/${checkId}`, data);
          
          if (data.success && data.result) {
            // 결과 저장
            this.results[checkId] = data.result;
            
            // 결과 표시
            this.displayCheckResult(checkId, data.result);
            
            // 마지막 검사 시간 표시
            if (data.timestamp) {
              const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
              if (lastCheckDateElement) {
                const date = new Date(data.timestamp);
                lastCheckDateElement.textContent = `마지막 검사: ${this.formatDate(date)}`;
              }
            }
          }
        })
        .catch(error => {
          console.error(`Error loading previous results for ${checkId}:`, error);
        });
    });
  }
  
  // 검사 실행
  runCheck(checkId) {
    // 결과 컨테이너 가져오기
    const resultContainer = document.getElementById(`result-${checkId}`);
    if (!resultContainer) return;
    
    // 로딩 표시
    resultContainer.style.display = 'block';
    
    // 검사 버튼 비활성화
    const checkButton = document.querySelector(`.run-check[data-check-id="${checkId}"]`);
    if (checkButton) {
      checkButton.disabled = true;
      checkButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i> 검사 중...';
    }
    
    // 로딩 메시지 표시
    const contentElement = resultContainer.querySelector('.check-result-content');
    if (contentElement) {
      contentElement.innerHTML = `
        <div class="alert alert-info">
          <i class="fas fa-spinner fa-spin"></i> ${checkId} 검사를 실행 중입니다. 잠시만 기다려주세요...
        </div>
      `;
    }
    
    // API 호출
    fetch(`/api/service-advisor/${this.serviceName}/run-check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ check_id: checkId })
    })
    .then(response => response.json())
    .then(data => {
      // 결과 저장
      this.results[checkId] = data;
      
      // 결과 표시
      this.displayCheckResult(checkId, data);
      
      // 마지막 검사 시간 업데이트
      const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
      if (lastCheckDateElement) {
        const now = new Date();
        lastCheckDateElement.textContent = `마지막 검사: ${this.formatDate(now)}`;
      }
      
      // 검사 버튼 활성화
      if (checkButton) {
        checkButton.disabled = false;
        checkButton.innerHTML = '<i class="fas fa-play"></i> 실행';
      }
    })
    .catch(error => {
      console.error('Error:', error);
      
      // 오류 표시
      if (contentElement) {
        contentElement.innerHTML = `
          <div class="alert alert-danger">
            <i class="fas fa-exclamation-circle"></i> 검사 실행 중 오류가 발생했습니다: ${error.message || '알 수 없는 오류'}
          </div>
        `;
      }
      
      // 검사 버튼 활성화
      if (checkButton) {
        checkButton.disabled = false;
        checkButton.innerHTML = '<i class="fas fa-play"></i> 실행';
      }
    });
  }
  
  // 모든 검사 실행
  runAllChecks() {
    const checks = document.querySelectorAll('.check-card');
    const checkIds = Array.from(checks).map(check => check.getAttribute('data-check-id'));
    
    if (checkIds.length === 0) {
      alert('실행할 검사 항목이 없습니다.');
      return;
    }
    
    // 모든 검사 동시에 실행 (병렬 처리)
    checkIds.forEach(checkId => {
      this.runCheck(checkId);
    });
  }
  
  // 검사 결과 표시
  displayCheckResult(checkId, data) {
    const resultContainer = document.getElementById(`result-${checkId}`);
    if (!resultContainer) return;
    
    // 결과 HTML 생성
    const resultHtml = this.generateResultHtml(checkId, data);
    
    // 결과 표시
    resultContainer.style.display = 'block';
    const contentElement = resultContainer.querySelector('.check-result-content');
    if (contentElement) {
      contentElement.innerHTML = resultHtml;
    }
    
    // 상태 표시
    const statusElement = resultContainer.querySelector('.check-result-status');
    if (statusElement && data.status) {
      statusElement.className = 'check-result-status';
      
      if (data.status === 'ok') {
        statusElement.classList.add('pass');
        statusElement.textContent = '정상';
      } else if (data.status === 'warning') {
        statusElement.classList.add('warning');
        statusElement.textContent = '경고';
      } else if (data.status === 'error') {
        statusElement.classList.add('fail');
        statusElement.textContent = '오류';
      } else {
        statusElement.classList.add('unknown');
        statusElement.textContent = data.status;
      }
    }
  }
  
  // 기본 결과 HTML 생성
  generateResultHtml(checkId, data) {
    if (!data) data = this.results[checkId];
    if (!data) return '<div class="alert alert-warning">검사 결과가 없습니다.</div>';
    
    // 상태에 따른 스타일 설정
    let statusClass = '';
    
    if (data.status === 'ok') {
      statusClass = 'success';
    } else if (data.status === 'warning') {
      statusClass = 'warning';
    } else if (data.status === 'error') {
      statusClass = 'danger';
    } else {
      statusClass = 'info';
    }
    
    // 기본 결과 HTML
    let resultHtml = `
      <div class="alert alert-${statusClass}">
        ${data.message || '검사가 완료되었습니다.'}
      </div>
    `;
    
    // 권장사항이 있는 경우 추가
    if (data.recommendations && data.recommendations.length > 0) {
      resultHtml += `
        <div class="check-result-recommendations">
          <h5>권장사항</h5>
          <ul>
            ${data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
          </ul>
        </div>
      `;
    }
    
    // 데이터가 있는 경우 추가
    if (data.data) {
      resultHtml += `
        <div class="check-result-data">
          <h5>상세 데이터</h5>
          <div class="table-responsive">
            ${this.generateDataTable(data.data, checkId)}
          </div>
        </div>
      `;
    }
    
    return resultHtml;
  }
  
  // 데이터 테이블 생성 (서비스별로 오버라이드)
  generateDataTable(data, checkId) {
    return '<div class="alert alert-info">상세 데이터를 표시할 수 없습니다.</div>';
  }
  
  // 날짜 포맷팅
  formatDate(date) {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}`;
  }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
  // 서비스 어드바이저 초기화
  if (!window.serviceAdvisor) {
    window.serviceAdvisor = new ServiceAdvisorCommon();
  }
});