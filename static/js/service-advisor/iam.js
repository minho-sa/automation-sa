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
      },
      'iam-mfa': {
        createResultHtml: this.createMfaResultHtml.bind(this),
        createTable: this.createMfaTable.bind(this)
      },
      'iam-inactive-users': {
        createResultHtml: this.createInactiveUsersResultHtml.bind(this),
        createTable: this.createInactiveUsersTable.bind(this)
      },
      'iam-root-account': {
        createResultHtml: this.createRootAccountResultHtml.bind(this),
        createTable: this.createRootAccountTable.bind(this)
      },
      'iam-policy-analyzer': {
        createResultHtml: this.createPolicyAnalyzerResultHtml.bind(this),
        createTable: this.createPolicyAnalyzerTable.bind(this)
      },
      'iam-credential-report': {
        createResultHtml: this.createCredentialReportResultHtml.bind(this),
        createTable: this.createCredentialReportTable.bind(this)
      },
      'iam-service-control-policy': {
        createResultHtml: this.createServiceControlPolicyResultHtml.bind(this),
        createTable: this.createServiceControlPolicyTable.bind(this)
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
          <div class="table-responsive">
            <table class="awsui-table policy-table">
              <thead>
                <tr>
                  <th>검사 항목</th>
                  <th>현재 값</th>
                  <th>권장 사항</th>
                  <th>상태</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td>암호 정책</td>
                  <td>설정되지 않음</td>
                  <td>설정 필요</td>
                  <td>
                    <span class="resource-status warning">
                      <i class="fas fa-exclamation-triangle"></i>
                      설정 필요
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      `;
    }
    return `
      <div class="check-result-data">
        <h4>암호 정책 분석</h4>
        ${this.createPasswordPolicyTable(data.data)}
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
        .policy-table th:nth-child(1) { width: 30%; }
        .policy-table th:nth-child(2) { width: 25%; }
        .policy-table th:nth-child(3) { width: 25%; }
        .policy-table th:nth-child(4) { width: 20%; }
        .policy-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table policy-table">
          <thead>
            <tr>
              <th>정책 설정</th>
              <th>현재 값</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>최소 암호 길이</td>
              <td>${policy.MinimumPasswordLength || 'N/A'}</td>
              <td>14 이상</td>
              <td>
                <span class="resource-status ${policy.MinimumPasswordLength >= 14 ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.MinimumPasswordLength >= 14 ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.MinimumPasswordLength >= 14 ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>대문자 요구</td>
              <td>${policy.RequireUppercaseCharacters ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.RequireUppercaseCharacters ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.RequireUppercaseCharacters ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.RequireUppercaseCharacters ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>소문자 요구</td>
              <td>${policy.RequireLowercaseCharacters ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.RequireLowercaseCharacters ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.RequireLowercaseCharacters ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.RequireLowercaseCharacters ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>숫자 요구</td>
              <td>${policy.RequireNumbers ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.RequireNumbers ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.RequireNumbers ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.RequireNumbers ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>특수 문자 요구</td>
              <td>${policy.RequireSymbols ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.RequireSymbols ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.RequireSymbols ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.RequireSymbols ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>암호 만료 활성화</td>
              <td>${policy.ExpirePasswords ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.ExpirePasswords ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.ExpirePasswords ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.ExpirePasswords ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>최대 암호 사용 기간</td>
              <td>${policy.MaxPasswordAge || 'N/A'}</td>
              <td>90일 이하</td>
              <td>
                <span class="resource-status ${policy.MaxPasswordAge && policy.MaxPasswordAge <= 90 ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.MaxPasswordAge && policy.MaxPasswordAge <= 90 ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.MaxPasswordAge && policy.MaxPasswordAge <= 90 ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
            <tr>
              <td>암호 재사용 방지</td>
              <td>${policy.PasswordReusePrevention || 'N/A'}</td>
              <td>24 이상</td>
              <td>
                <span class="resource-status ${policy.PasswordReusePrevention && policy.PasswordReusePrevention >= 24 ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.PasswordReusePrevention && policy.PasswordReusePrevention >= 24 ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.PasswordReusePrevention && policy.PasswordReusePrevention >= 24 ? '적합' : '개선 필요'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }

  // MFA 설정 결과 HTML 생성
  createMfaResultHtml(data) {
    const checkId = 'iam-mfa';
    
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
        ${this.createMfaTable(data.data.users)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const users = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createMfaTable(users)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>MFA 설정 분석 (${data.data.total_users_count}명)</h4>
        <ul class="nav nav-tabs" id="mfaTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="mfaTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // MFA 설정 테이블 생성
  createMfaTable(users) {
    if (!users || users.length === 0) return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    
    return `
      <style>
        .mfa-table th:nth-child(1) { width: 20%; }
        .mfa-table th:nth-child(2) { width: 15%; }
        .mfa-table th:nth-child(3) { width: 15%; }
        .mfa-table th:nth-child(4) { width: 15%; }
        .mfa-table th:nth-child(5) { width: 20%; }
        .mfa-table th:nth-child(6) { width: 15%; }
        .mfa-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table mfa-table">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>콘솔 액세스</th>
              <th>MFA 설정</th>
              <th>관리자 권한</th>
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
              
              return `
                <tr>
                  <td>${user.user_name || ''}</td>
                  <td>${user.has_console_access === true ? '예' : user.has_console_access === false ? '아니오' : user.has_console_access}</td>
                  <td>${user.has_mfa === true ? '예' : user.has_mfa === false ? '아니오' : user.has_mfa}</td>
                  <td>${user.is_admin === true ? '예' : user.is_admin === false ? '아니오' : user.is_admin}</td>
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

  // 비활성 사용자 결과 HTML 생성
  createInactiveUsersResultHtml(data) {
    const checkId = 'iam-inactive-users';
    
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
        ${this.createInactiveUsersTable(data.data.users)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const users = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createInactiveUsersTable(users)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>비활성 사용자 분석 (${data.data.total_users_count}명)</h4>
        <ul class="nav nav-tabs" id="inactiveUsersTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="inactiveUsersTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 비활성 사용자 테이블 생성
  createInactiveUsersTable(users) {
    if (!users || users.length === 0) return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    
    return `
      <style>
        .inactive-users-table th:nth-child(1) { width: 20%; }
        .inactive-users-table th:nth-child(2) { width: 15%; }
        .inactive-users-table th:nth-child(3) { width: 15%; }
        .inactive-users-table th:nth-child(4) { width: 15%; }
        .inactive-users-table th:nth-child(5) { width: 20%; }
        .inactive-users-table th:nth-child(6) { width: 15%; }
        .inactive-users-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table inactive-users-table">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>생성 날짜</th>
              <th>마지막 활동</th>
              <th>비활성 기간</th>
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
              
              return `
                <tr>
                  <td>${user.user_name || ''}</td>
                  <td>${user.create_date || ''}</td>
                  <td>${user.last_activity || ''}</td>
                  <td>${user.inactive_days !== 'N/A' ? `${user.inactive_days}일` : user.inactive_days}</td>
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

  // 루트 계정 보안 결과 HTML 생성
  createRootAccountResultHtml(data) {
    const checkId = 'iam-root-account';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.items.forEach(item => {
      const statusText = item.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(item);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.items.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const items = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${items.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createRootAccountTable(data.data.items)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const items = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createRootAccountTable(items)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>루트 계정 보안 분석 (${data.data.items.length}개 항목)</h4>
        <ul class="nav nav-tabs" id="rootAccountTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="rootAccountTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 루트 계정 보안 테이블 생성
  createRootAccountTable(items) {
    if (!items || items.length === 0) return '<div class="alert alert-info">표시할 항목이 없습니다.</div>';
    
    return `
      <style>
        .root-account-table th:nth-child(1) { width: 30%; }
        .root-account-table th:nth-child(2) { width: 20%; }
        .root-account-table th:nth-child(3) { width: 35%; }
        .root-account-table th:nth-child(4) { width: 15%; }
        .root-account-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table root-account-table">
          <thead>
            <tr>
              <th>검사 항목</th>
              <th>현재 값</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${items.map(item => {
              let statusClass = '';
              let statusIcon = '';
              
              if (item.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (item.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (item.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (item.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (item.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${item.check_name || ''}</td>
                  <td>${item.value || ''}</td>
                  <td>${item.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${item.status_text || ''}
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

  // 정책 분석 결과 HTML 생성
  createPolicyAnalyzerResultHtml(data) {
    const checkId = 'iam-policy-analyzer';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.policies.forEach(policy => {
      const statusText = policy.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(policy);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.policies.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const policies = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${policies.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createPolicyAnalyzerTable(data.data.policies)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const policies = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createPolicyAnalyzerTable(policies)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>정책 분석 (${data.data.total_policies_count}개)</h4>
        <ul class="nav nav-tabs" id="policyAnalyzerTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="policyAnalyzerTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 정책 분석 테이블 생성
  createPolicyAnalyzerTable(policies) {
    if (!policies || policies.length === 0) return '<div class="alert alert-info">표시할 정책이 없습니다.</div>';
    
    return `
      <style>
        .policy-analyzer-table th:nth-child(1) { width: 25%; }
        .policy-analyzer-table th:nth-child(2) { width: 35%; }
        .policy-analyzer-table th:nth-child(3) { width: 25%; }
        .policy-analyzer-table th:nth-child(4) { width: 15%; }
        .policy-analyzer-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table policy-analyzer-table">
          <thead>
            <tr>
              <th>정책 이름</th>
              <th>위험한 설정</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${policies.map(policy => {
              let statusClass = '';
              let statusIcon = '';
              
              if (policy.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (policy.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (policy.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (policy.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (policy.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              // 위험한 설정 정보 생성
              let riskyStatementsHtml = '';
              if (policy.risky_statements && policy.risky_statements.length > 0) {
                riskyStatementsHtml = policy.risky_statements.map(statement => {
                  return `<div class="text-danger">${statement}</div>`;
                }).join('');
              } else {
                riskyStatementsHtml = '없음';
              }
              
              return `
                <tr>
                  <td>${policy.policy_name || ''}</td>
                  <td>${riskyStatementsHtml}</td>
                  <td>${policy.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${policy.status_text || ''}
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

  // 자격 증명 보고서 결과 HTML 생성
  createCredentialReportResultHtml(data) {
    const checkId = 'iam-credential-report';
    
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
        ${this.createCredentialReportTable(data.data.users)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const users = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createCredentialReportTable(users)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>자격 증명 보고서 분석 (${data.data.total_users_count}명)</h4>
        <ul class="nav nav-tabs" id="credentialReportTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="credentialReportTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 자격 증명 보고서 테이블 생성
  createCredentialReportTable(users) {
    if (!users || users.length === 0) return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    
    return `
      <style>
        .credential-report-table th:nth-child(1) { width: 15%; }
        .credential-report-table th:nth-child(2) { width: 10%; }
        .credential-report-table th:nth-child(3) { width: 10%; }
        .credential-report-table th:nth-child(4) { width: 10%; }
        .credential-report-table th:nth-child(5) { width: 15%; }
        .credential-report-table th:nth-child(6) { width: 25%; }
        .credential-report-table th:nth-child(7) { width: 15%; }
        .credential-report-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table credential-report-table">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>콘솔 액세스</th>
              <th>MFA</th>
              <th>액세스 키</th>
              <th>마지막 활동</th>
              <th>문제점</th>
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
              
              // 문제점 정보 생성
              let issuesHtml = '';
              if (user.issues && user.issues.length > 0) {
                issuesHtml = user.issues.map(issue => {
                  return `<div class="text-danger">${issue}</div>`;
                }).join('');
              } else {
                issuesHtml = '없음';
              }
              
              return `
                <tr>
                  <td>${user.user_name || ''}</td>
                  <td>${user.has_console_access ? '예' : '아니오'}</td>
                  <td>${user.has_mfa ? '예' : '아니오'}</td>
                  <td>${user.has_access_key_1 || user.has_access_key_2 ? '있음' : '없음'}</td>
                  <td>${user.last_activity || 'N/A'}</td>
                  <td>${issuesHtml}</td>
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

  // 서비스 제어 정책 결과 HTML 생성
  createServiceControlPolicyResultHtml(data) {
    const checkId = 'iam-service-control-policy';
    
    // Organizations가 활성화되어 있지 않은 경우
    if (!data.data.org_enabled) {
      return `
        <div class="check-result-data">
          <h4>서비스 제어 정책 분석</h4>
          <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <span>AWS Organizations가 활성화되어 있지 않습니다.</span>
          </div>
        </div>
      `;
    }
    
    // SCP가 활성화되어 있지 않은 경우
    if (!data.data.scp_enabled) {
      return `
        <div class="check-result-data">
          <h4>서비스 제어 정책 분석</h4>
          <div class="alert alert-warning">
            <i class="fas fa-exclamation-triangle"></i>
            <span>서비스 제어 정책(SCP)이 활성화되어 있지 않습니다.</span>
          </div>
        </div>
      `;
    }
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.scp_implementation_results.forEach(scp => {
      const statusText = scp.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(scp);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.scp_implementation_results.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const scps = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${scps.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createServiceControlPolicyTable(data.data.scp_implementation_results)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const scps = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createServiceControlPolicyTable(scps)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>서비스 제어 정책 분석 (${data.data.total_scps_count}개)</h4>
        <ul class="nav nav-tabs" id="scpTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="scpTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 서비스 제어 정책 테이블 생성
  createServiceControlPolicyTable(scps) {
    if (!scps || scps.length === 0) return '<div class="alert alert-info">표시할 SCP가 없습니다.</div>';
    
    return `
      <style>
        .scp-table th:nth-child(1) { width: 30%; }
        .scp-table th:nth-child(2) { width: 15%; }
        .scp-table th:nth-child(3) { width: 40%; }
        .scp-table th:nth-child(4) { width: 15%; }
        .scp-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table scp-table">
          <thead>
            <tr>
              <th>SCP 이름</th>
              <th>구현 상태</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${scps.map(scp => {
              let statusClass = '';
              let statusIcon = '';
              
              if (scp.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (scp.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (scp.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (scp.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (scp.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${scp.scp_name || ''}</td>
                  <td>${scp.implemented ? '구현됨' : '미구현'}</td>
                  <td>${scp.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${scp.status_text || ''}
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
}