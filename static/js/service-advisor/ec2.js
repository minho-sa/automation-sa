/**
 * EC2 서비스 어드바이저 기능
 * EC2 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorEC2 extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      'ec2-security-group': {
        createResultHtml: this.createSecurityGroupResultHtml.bind(this),
        createTable: this.createSecurityGroupTable.bind(this)
      },
      'ec2-instance-type': {
        createResultHtml: this.createInstanceTypeResultHtml.bind(this),
        createTable: this.createInstanceTypeTable.bind(this)
      }
    };
  }

  // 검사 실행 (EC2 서비스 전용)
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
    fetch(`/api/service-advisor/ec2/run-check`, {
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

  // 결과 HTML 생성 (EC2 서비스 전용)
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

  // 보안 그룹 결과 HTML 생성
  createSecurityGroupResultHtml(data) {
    const checkId = 'ec2-security-group';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.security_groups.forEach(group => {
      const statusText = group.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(group);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.security_groups.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const groups = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${groups.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createSecurityGroupTable(data.data.security_groups)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const groups = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createSecurityGroupTable(groups)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>보안 그룹 분석 (${data.data.total_groups_count}개)</h4>
        <ul class="nav nav-tabs" id="securityGroupTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="securityGroupTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 인스턴스 타입 결과 HTML 생성
  createInstanceTypeResultHtml(data) {
    const checkId = 'ec2-instance-type';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.instances.forEach(instance => {
      const statusText = instance.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(instance);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.instances.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${instances.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createInstanceTypeTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createInstanceTypeTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>인스턴스 타입 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="instanceTypeTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="instanceTypeTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 보안 그룹 테이블 생성
  createSecurityGroupTable(securityGroups) {
    if (!securityGroups || securityGroups.length === 0) return '<div class="alert alert-info">표시할 보안 그룹이 없습니다.</div>';
    
    return `
      <style>
        .sg-table th:nth-child(1) { width: 15%; }
        .sg-table th:nth-child(2) { width: 20%; }
        .sg-table th:nth-child(3) { width: 50%; }
        .sg-table th:nth-child(4) { width: 15%; }
        .sg-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table sg-table">
          <thead>
            <tr>
              <th>보안 그룹 ID</th>
              <th>보안 그룹 이름</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${securityGroups.map(group => {
              let statusClass = '';
              let statusIcon = '';
              
              if (group.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (group.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${group.id || ''}</td>
                  <td>${group.sg_name || ''}</td>
                  <td>${group.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${group.status_text || ''}
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

  // 인스턴스 타입 테이블 생성
  createInstanceTypeTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .instance-table th:nth-child(1) { width: 12%; }
        .instance-table th:nth-child(2) { width: 15%; }
        .instance-table th:nth-child(3) { width: 10%; }
        .instance-table th:nth-child(4) { width: 10%; }
        .instance-table th:nth-child(5) { width: 10%; }
        .instance-table th:nth-child(6) { width: 30%; }
        .instance-table th:nth-child(7) { width: 13%; }
        .instance-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table instance-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>인스턴스 이름</th>
              <th>인스턴스 타입</th>
              <th>평균 CPU</th>
              <th>최대 CPU</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (instance.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.id || ''}</td>
                  <td>${instance.instance_name || 'N/A'}</td>
                  <td>${instance.instance_type || ''}</td>
                  <td>${instance.avg_cpu !== undefined ? `${instance.avg_cpu}%` : 'N/A'}</td>
                  <td>${instance.max_cpu !== undefined ? `${instance.max_cpu}%` : 'N/A'}</td>
                  <td>${instance.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${instance.status_text || ''}
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