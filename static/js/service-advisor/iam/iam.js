/**
 * IAM 서비스 어드바이저 기능
 */

class ServiceAdvisorIAM extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.serviceName = 'iam';
  }
  
  // 데이터 테이블 생성
  generateDataTable(data, checkId) {
    if (!data) return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    
    switch (checkId) {
      case 'iam-access-key-rotation':
        return this.createAccessKeyTable(data);
      case 'iam-password-policy':
        return this.createPasswordPolicyTable(data);
      case 'iam-mfa':
        return this.createMfaTable(data);
      case 'iam-inactive-users':
        return this.createInactiveUsersTable(data);
      case 'iam-root-account':
        return this.createRootAccountTable(data);
      default:
        return this.createGenericTable(data);
    }
  }
  
  // 액세스 키 테이블 생성
  createAccessKeyTable(data) {
    if (!data.users || data.users.length === 0) {
      return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>액세스 키 ID</th>
              <th>생성일</th>
              <th>마지막 교체일</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.users.map(user => {
              let statusClass = '';
              let statusIcon = '';
              
              if (user.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (user.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${user.username || 'N/A'}</td>
                  <td>${user.access_key_id || 'N/A'}</td>
                  <td>${user.created_date || 'N/A'}</td>
                  <td>${user.last_rotated || 'N/A'}</td>
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
    if (!data.policy) {
      return '<div class="alert alert-info">암호 정책 데이터가 없습니다.</div>';
    }
    
    const policy = data.policy;
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>정책 설정</th>
              <th>현재 값</th>
              <th>권장 값</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>최소 암호 길이</td>
              <td>${policy.minimum_password_length || 'N/A'}</td>
              <td>14자 이상</td>
              <td>
                <span class="resource-status ${policy.minimum_password_length >= 14 ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.minimum_password_length >= 14 ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.minimum_password_length >= 14 ? '충족' : '미충족'}
                </span>
              </td>
            </tr>
            <tr>
              <td>대문자 필요</td>
              <td>${policy.require_uppercase ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.require_uppercase ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.require_uppercase ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.require_uppercase ? '충족' : '미충족'}
                </span>
              </td>
            </tr>
            <tr>
              <td>소문자 필요</td>
              <td>${policy.require_lowercase ? '예' : '아니오'}</td>
              <td>예</td>
              <td>
                <span class="resource-status ${policy.require_lowercase ? 'success' : 'warning'}">
                  <i class="fas fa-${policy.require_lowercase ? 'check-circle' : 'exclamation-triangle'}"></i>
                  ${policy.require_lowercase ? '충족' : '미충족'}
                </span>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }
  
  // MFA 테이블 생성
  createMfaTable(data) {
    if (!data.users || data.users.length === 0) {
      return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>MFA 활성화</th>
              <th>관리자 권한</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.users.map(user => {
              let statusClass = '';
              let statusIcon = '';
              
              if (user.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (user.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${user.username || 'N/A'}</td>
                  <td>${user.mfa_enabled ? '예' : '아니오'}</td>
                  <td>${user.is_admin ? '예' : '아니오'}</td>
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
  
  // 일반 테이블 생성
  createGenericTable(data) {
    if (data.users && data.users.length > 0) {
      return `
        <div class="table-responsive">
          <table class="table table-striped table-hover">
            <thead>
              <tr>
                <th>사용자 이름</th>
                <th>권장 사항</th>
                <th>상태</th>
              </tr>
            </thead>
            <tbody>
              ${data.users.map(user => {
                let statusClass = '';
                let statusIcon = '';
                
                if (user.status === 'pass') {
                  statusClass = 'success';
                  statusIcon = 'check-circle';
                } else if (user.status === 'fail') {
                  statusClass = 'warning';
                  statusIcon = 'exclamation-triangle';
                } else {
                  statusClass = 'secondary';
                  statusIcon = 'question-circle';
                }
                
                return `
                  <tr>
                    <td>${user.username || 'N/A'}</td>
                    <td>${user.advice || 'N/A'}</td>
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
    } else {
      return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    }
  }
  
  // 비활성 사용자 테이블 생성
  createInactiveUsersTable(data) {
    if (!data.users || data.users.length === 0) {
      return '<div class="alert alert-info">표시할 사용자가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>사용자 이름</th>
              <th>생성일</th>
              <th>마지막 활동</th>
              <th>비활성 기간</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.users.map(user => {
              let statusClass = '';
              let statusIcon = '';
              
              if (user.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (user.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${user.username || 'N/A'}</td>
                  <td>${user.created_date || 'N/A'}</td>
                  <td>${user.last_activity || 'N/A'}</td>
                  <td>${user.inactive_days || 'N/A'} 일</td>
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
  
  // 루트 계정 테이블 생성
  createRootAccountTable(data) {
    if (!data.root_account) {
      return '<div class="alert alert-info">루트 계정 데이터가 없습니다.</div>';
    }
    
    const root = data.root_account;
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>보안 설정</th>
              <th>상태</th>
              <th>권장 사항</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>MFA 활성화</td>
              <td>
                <span class="resource-status ${root.mfa_enabled ? 'success' : 'danger'}">
                  <i class="fas fa-${root.mfa_enabled ? 'check-circle' : 'times-circle'}"></i>
                  ${root.mfa_enabled ? '활성화됨' : '비활성화됨'}
                </span>
              </td>
              <td>${root.mfa_enabled ? '적절하게 구성됨' : '루트 계정에 MFA를 활성화하세요'}</td>
            </tr>
          </tbody>
        </table>
      </div>
    `;
  }
}

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
  // IAM 서비스 어드바이저 초기화
  window.serviceAdvisor = new ServiceAdvisorIAM();
});