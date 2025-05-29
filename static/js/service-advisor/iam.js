/**
 * IAM 서비스 어드바이저 기능
 * IAM 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorIAM extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      'iam-access-key-rotation': {
        createResultHtml: this.createAccessKeyRotationResultHtml.bind(this),
        createTable: this.createAccessKeyRotationTable.bind(this)
      },
      'iam-password-policy': {
        createResultHtml: this.createPasswordPolicyResultHtml.bind(this),
        createTable: this.createPasswordPolicyTable.bind(this)
      }
    };
  }

  // 검사 실행 (IAM 서비스 전용)
  runCheck(checkId) {
    const resultContainer = document.getElementById(`result-${checkId}`);
    const loadingElement = resultContainer.querySelector('.check-result-loading');
    const contentElement = resultContainer.querySelector('.check-result-content');
    const lastCheckDateElement = document.getElementById(`last-check-date-${checkId}`);
    
    // 현재 날짜와 시간 설정
    const now = new Date();
    const dateString = this.formatDate(now);
    
    // 마지막 검사 날짜 업데이트
    if (lastCheckDateElement) {
      lastCheckDateElement.textContent = `마지막 검사: ${dateString}`;
    }
    
    // 결과 컨테이너 표시 및 로딩 표시
    resultContainer.style.display = 'block';
    loadingElement.style.display = 'flex';
    contentElement.style.display = 'none';
    
    // API 호출
    fetch(`/api/service-advisor/iam/run-check`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ check_id: checkId })
    })
    .then(response => response.json())
    .then(data => {
      // 결과 저장
      this.results[checkId] = data;
      
      // 로딩 숨기기
      loadingElement.style.display = 'none';
      
      // 결과 표시
      contentElement.style.display = 'block';
      
      // 결과 HTML 생성
      const resultHtml = this.generateResultHtml(checkId);
      contentElement.innerHTML = resultHtml;
    })
    .catch(error => {
      // 로딩 숨기기
      loadingElement.style.display = 'none';
      
      // 오류 표시
      contentElement.style.display = 'block';
      contentElement.innerHTML = `
        <div class="check-result-status danger">
          <i class="fas fa-times-circle"></i>
          <span>검사 실행 중 오류가 발생했습니다: ${error.message}</span>
        </div>
      `;
    });
  }

  // 결과 HTML 생성 (IAM 서비스 전용)
  generateResultHtml(checkId) {
    // 기본 결과 HTML 생성
    let resultHtml = super.generateResultHtml(checkId);
    
    // 데이터가 있는 경우 결과 테이블 생성
    const data = this.results[checkId];
    if (data && data.data && this.checkHandlers[checkId]) {
      resultHtml += this.checkHandlers[checkId].createResultHtml(data);
    }
    
    return resultHtml;
  }

  // 액세스 키 교체 결과 HTML 생성
  createAccessKeyRotationResultHtml(data) {
    const checkId = 'iam-access-key-rotation';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.users.forEach(user => {
      const statusText = user.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(user);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.users.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const users = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${users.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createAccessKeyRotationTable(data.data.users)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const users = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createAccessKeyRotationTable(users)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>액세스 키 교체 분석 (${data.data.total_users_count}명)</h4>
        <ul class="nav nav-tabs" id="accessKeyTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="accessKeyTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 암호 정책 결과 HTML 생성
  createPasswordPolicyResultHtml(data) {
    const checkId = 'iam-password-policy';
    
    // 정책이 없는 경우
    if (!data.data.policy) {
      return `
        <div class="check-result-data">
          <h4>암호 정책 분석</h4>
          <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <span>계정 암호 정책이 설정되지 않았습니다.</span>
          </div>
          <div class="mt-3">
            <h5>권장 사항</h5>
            <ul>
              ${data.data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
            </ul>
          </div>
        </div>
      `;
    }
    
    return `
      <div class="check-result-data">
        <h4>암호 정책 분석</h4>
        ${this.createPasswordPolicyTable(data.data)}
        ${data.data.issues.length > 0 ? `
          <div class="mt-3">
            <h5>발견된 문제점</h5>
            <ul>
              ${data.data.issues.map(issue => `<li>${issue}</li>`).join('')}
            </ul>
          </div>
        ` : ''}
        <div class="mt-3">
          <h5>권장 사항</h5>
          <ul>
            ${data.data.recommendations.map(rec => `<li>${rec}</li>`).join('')}
          </ul>
        </div>
      </div>
    `;
  }

  // 액세스 키 교체 테이블 생성
  createAccessKeyRotationTable(users) {
    if (!users || users.length === 0) return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    
    return `
      <style>
        .access-key-table th:nth-child(1) { width: 20%; }
        .access-key-table th:nth-child(2) { width: 40%; }
        .access-key-table th:nth-child(3) { width: 25%; }
        .access-key-table th:nth-child(4) { width: 15%; }
        .access-key-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table access-key-table">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>액세스 키 정보</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${users.map(user => {
              let statusClass = '';
              let statusIcon = '';
              
              if (user.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (user.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (user.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (user.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (user.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              // 액세스 키 정보 생성
              let keyInfo = '';
              if (user.access_keys && user.access_keys.length > 0) {
                keyInfo = user.access_keys.map(key => {
                  let keyStatusClass = '';
                  if (key.rotation_status === 'fail') keyStatusClass = 'text-danger';
                  else if (key.rotation_status === 'warning') keyStatusClass = 'text-warning';
                  
                  return `<div class="${keyStatusClass}">
                    ${key.id} (${key.days_old}일 전 생성, ${key.status})
                  </div>`;
                }).join('');
              } else {
                keyInfo = '액세스 키 없음';
              }
              
              return `
                <tr>
                  <td>${user.user_name || ''}</td>
                  <td>${keyInfo}</td>
                  <td>${user.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${user.status_text || ''}
                    </span>
                  </td>
                </tr>
              `;
            }).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  // 암호 정책 테이블 생성
  createPasswordPolicyTable(data) {
    if (!data.policy) return '';
    
    const policy = data.policy;
    
    return `
      <style>
        .policy-table th:nth-child(1) { width: 40%; }
        .policy-table th:nth-child(2) { width: 30%; }
        .policy-table th:nth-child(3) { width: 30%; }
        .policy-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table policy-table">
          <thead>
            <tr>
              <th>정책 설정</th>
              <th>현재 값</th>
              <th>권장 값</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>최소 암호 길이</td>
              <td>${policy.MinimumPasswordLength || 'N/A'}</td>
              <td>14 이상</td>
            </tr>
            <tr>
              <td>대문자 요구</td>
              <td>${policy.RequireUppercaseCharacters ? '예' : '아니오'}</td>
              <td>예</td>
            </tr>
            <tr>
              <td>소문자 요구</td>
              <td>${policy.RequireLowercaseCharacters ? '예' : '아니오'}</td>
              <td>예</td>
            </tr>
            <tr>
              <td>숫자 요구</td>
              <td>${policy.RequireNumbers ? '예' : '아니오'}</td>
              <td>예</td>
            </tr>
            <tr>
              <td>특수 문자 요구</td>
              <td>${policy.RequireSymbols ? '예' : '아니오'}</td>
              <td>예</td>
            </tr>
            <tr>
              <td>암호 만료 활성화</td>
              <td>${policy.ExpirePasswords ? '예' : '아니오'}</td>
              <td>예</td>
            </tr>
            <tr>
              <td>최대 암호 사용 기간</td>
              <td>${policy.MaxPasswordAge || 'N/A'}</td>
              <td>90일 이하</td>
            </tr>
            <tr>
              <td>암호 재사용 방지</td>
              <td>${policy.PasswordReusePrevention || 'N/A'}</td>
              <td>24 이상</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }
}