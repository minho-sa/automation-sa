/**
 * RDS 서비스 어드바이저 기능
 * RDS 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorRDS extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      'rds-backup-retention': {
        createResultHtml: this.createBackupRetentionResultHtml.bind(this),
        createTable: this.createBackupRetentionTable.bind(this)
      },
      'rds-multi-az': {
        createResultHtml: this.createMultiAZResultHtml.bind(this),
        createTable: this.createMultiAZTable.bind(this)
      },
      'rds-encryption': {
        createResultHtml: this.createEncryptionResultHtml.bind(this),
        createTable: this.createEncryptionTable.bind(this)
      },
      'rds-public-access': {
        createResultHtml: this.createPublicAccessResultHtml.bind(this),
        createTable: this.createPublicAccessTable.bind(this)
      },
      'rds-instance-sizing': {
        createResultHtml: this.createInstanceSizingResultHtml.bind(this),
        createTable: this.createInstanceSizingTable.bind(this)
      }
    };
  }

  // 검사 실행 (RDS 서비스 전용)
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
    fetch(`/api/service-advisor/rds/run-check`, {
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
      
      // PDF 다운로드 버튼 표시
      const downloadBtn = document.querySelector(`.download-pdf-btn[data-check-id="${checkId}"]`);
      if (downloadBtn) {
        downloadBtn.style.display = 'inline-block';
      }
      
      // 검사 완료 이벤트 발생
      document.dispatchEvent(new CustomEvent('checkCompleted', {
        detail: { checkId: checkId }
      }));
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

  // 결과 HTML 생성 (RDS 서비스 전용)
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

  // 백업 보존 기간 결과 HTML 생성
  createBackupRetentionResultHtml(data) {
    const checkId = 'rds-backup-retention';
    
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
        ${this.createBackupRetentionTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createBackupRetentionTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>백업 보존 기간 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="backupRetentionTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="backupRetentionTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 다중 AZ 결과 HTML 생성
  createMultiAZResultHtml(data) {
    const checkId = 'rds-multi-az';
    
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
        ${this.createMultiAZTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createMultiAZTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>다중 AZ 구성 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="multiAZTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="multiAZTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 백업 보존 기간 테이블 생성
  createBackupRetentionTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .backup-table th:nth-child(1) { width: 25%; }
        .backup-table th:nth-child(2) { width: 15%; }
        .backup-table th:nth-child(3) { width: 15%; }
        .backup-table th:nth-child(4) { width: 30%; }
        .backup-table th:nth-child(5) { width: 15%; }
        .backup-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table backup-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>엔진</th>
              <th>보존 기간</th>
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
              } else if (instance.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
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
                  <td>${instance.instance_id || ''}</td>
                  <td>${instance.engine || ''}</td>
                  <td>${instance.retention_period}일</td>
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

  // 다중 AZ 테이블 생성
  createMultiAZTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .multi-az-table th:nth-child(1) { width: 25%; }
        .multi-az-table th:nth-child(2) { width: 15%; }
        .multi-az-table th:nth-child(3) { width: 15%; }
        .multi-az-table th:nth-child(4) { width: 30%; }
        .multi-az-table th:nth-child(5) { width: 15%; }
        .multi-az-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table multi-az-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>인스턴스 클래스</th>
              <th>다중 AZ</th>
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
              } else if (instance.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
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
                  <td>${instance.instance_id || ''}</td>
                  <td>${instance.instance_class || ''}</td>
                  <td>${instance.multi_az ? '예' : '아니오'}</td>
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

  // 암호화 설정 결과 HTML 생성
  createEncryptionResultHtml(data) {
    const checkId = 'rds-encryption';
    
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
        ${this.createEncryptionTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createEncryptionTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>암호화 설정 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="encryptionTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="encryptionTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 암호화 설정 테이블 생성
  createEncryptionTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .encryption-table th:nth-child(1) { width: 25%; }
        .encryption-table th:nth-child(2) { width: 15%; }
        .encryption-table th:nth-child(3) { width: 15%; }
        .encryption-table th:nth-child(4) { width: 15%; }
        .encryption-table th:nth-child(5) { width: 15%; }
        .encryption-table th:nth-child(6) { width: 15%; }
        .encryption-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table encryption-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>엔진</th>
              <th>암호화됨</th>
              <th>프로덕션 환경</th>
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
              } else if (instance.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
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
                  <td>${instance.instance_id || ''}</td>
                  <td>${instance.engine || ''}</td>
                  <td>${instance.storage_encrypted ? '예' : '아니오'}</td>
                  <td>${instance.is_production ? '예' : '아니오'}</td>
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

  // 공개 액세스 설정 결과 HTML 생성
  createPublicAccessResultHtml(data) {
    const checkId = 'rds-public-access';
    
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
        ${this.createPublicAccessTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createPublicAccessTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>공개 액세스 설정 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="publicAccessTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="publicAccessTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 공개 액세스 설정 테이블 생성
  createPublicAccessTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .public-access-table th:nth-child(1) { width: 25%; }
        .public-access-table th:nth-child(2) { width: 15%; }
        .public-access-table th:nth-child(3) { width: 15%; }
        .public-access-table th:nth-child(4) { width: 30%; }
        .public-access-table th:nth-child(5) { width: 15%; }
        .public-access-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table public-access-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>엔진</th>
              <th>공개 액세스</th>
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
              } else if (instance.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
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
                  <td>${instance.instance_id || ''}</td>
                  <td>${instance.engine || ''}</td>
                  <td>${instance.publicly_accessible ? '예' : '아니오'}</td>
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

  // 인스턴스 크기 최적화 결과 HTML 생성
  createInstanceSizingResultHtml(data) {
    const checkId = 'rds-instance-sizing';
    
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
        ${this.createInstanceSizingTable(data.data.instances)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const instances = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createInstanceSizingTable(instances)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>인스턴스 크기 최적화 분석 (${data.data.total_instances_count}개)</h4>
        <ul class="nav nav-tabs" id="instanceSizingTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="instanceSizingTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 인스턴스 크기 최적화 테이블 생성
  createInstanceSizingTable(instances) {
    if (!instances || instances.length === 0) return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    
    return `
      <style>
        .instance-sizing-table th:nth-child(1) { width: 15%; }
        .instance-sizing-table th:nth-child(2) { width: 15%; }
        .instance-sizing-table th:nth-child(3) { width: 10%; }
        .instance-sizing-table th:nth-child(4) { width: 10%; }
        .instance-sizing-table th:nth-child(5) { width: 30%; }
        .instance-sizing-table th:nth-child(6) { width: 10%; }
        .instance-sizing-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table instance-sizing-table">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>인스턴스 클래스</th>
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
              } else if (instance.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
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
                  <td>${instance.instance_id || ''}</td>
                  <td>${instance.instance_class || ''}</td>
                  <td>${instance.avg_cpu !== 'N/A' && instance.avg_cpu !== 'Error' ? `${instance.avg_cpu}%` : instance.avg_cpu}</td>
                  <td>${instance.max_cpu !== 'N/A' && instance.max_cpu !== 'Error' ? `${instance.max_cpu}%` : instance.max_cpu}</td>
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