/**
 * S3 서비스 어드바이저 기능
 * S3 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorS3 extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      's3-public-access': {
        createResultHtml: this.createPublicAccessResultHtml.bind(this),
        createTable: this.createPublicAccessTable.bind(this)
      },
      's3-encryption': {
        createResultHtml: this.createEncryptionResultHtml.bind(this),
        createTable: this.createEncryptionTable.bind(this)
      },
      's3-versioning': {
        createResultHtml: this.createVersioningResultHtml.bind(this),
        createTable: this.createVersioningTable.bind(this)
      },
      's3-lifecycle': {
        createResultHtml: this.createLifecycleResultHtml.bind(this),
        createTable: this.createLifecycleTable.bind(this)
      },
      's3-logging': {
        createResultHtml: this.createLoggingResultHtml.bind(this),
        createTable: this.createLoggingTable.bind(this)
      }
    };
  }

  // 검사 실행 (S3 서비스 전용)
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
    fetch(`/api/service-advisor/s3/run-check`, {
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

  // 결과 HTML 생성 (S3 서비스 전용)
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

  // 퍼블릭 액세스 결과 HTML 생성
  createPublicAccessResultHtml(data) {
    const checkId = 's3-public-access';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.buckets.forEach(bucket => {
      const statusText = bucket.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(bucket);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.buckets.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${buckets.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createPublicAccessTable(data.data.buckets)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createPublicAccessTable(buckets)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>퍼블릭 액세스 설정 분석 (${data.data.total_buckets_count}개)</h4>
        <ul class="nav nav-tabs" id="publicAccessTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="publicAccessTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 암호화 결과 HTML 생성
  createEncryptionResultHtml(data) {
    const checkId = 's3-encryption';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.buckets.forEach(bucket => {
      const statusText = bucket.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(bucket);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.buckets.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${buckets.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createEncryptionTable(data.data.buckets)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createEncryptionTable(buckets)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>암호화 설정 분석 (${data.data.total_buckets_count}개)</h4>
        <ul class="nav nav-tabs" id="encryptionTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="encryptionTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 퍼블릭 액세스 테이블 생성
  createPublicAccessTable(buckets) {
    if (!buckets || buckets.length === 0) return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    
    return `
      <style>
        .public-access-table th:nth-child(1) { width: 30%; }
        .public-access-table th:nth-child(2) { width: 15%; }
        .public-access-table th:nth-child(3) { width: 40%; }
        .public-access-table th:nth-child(4) { width: 15%; }
        .public-access-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table public-access-table">
          <thead>
            <tr>
              <th>버킷 이름</th>
              <th>생성일</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              let statusClass = '';
              let statusIcon = '';
              
              if (bucket.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (bucket.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (bucket.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${bucket.bucket_name || ''}</td>
                  <td>${bucket.creation_date || ''}</td>
                  <td>${bucket.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${bucket.status_text || ''}
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

  // 암호화 테이블 생성
  createEncryptionTable(buckets) {
    if (!buckets || buckets.length === 0) return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    
    return `
      <style>
        .encryption-table th:nth-child(1) { width: 25%; }
        .encryption-table th:nth-child(2) { width: 15%; }
        .encryption-table th:nth-child(3) { width: 15%; }
        .encryption-table th:nth-child(4) { width: 30%; }
        .encryption-table th:nth-child(5) { width: 15%; }
        .encryption-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table encryption-table">
          <thead>
            <tr>
              <th>버킷 이름</th>
              <th>생성일</th>
              <th>암호화 유형</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              let statusClass = '';
              let statusIcon = '';
              
              if (bucket.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (bucket.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (bucket.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${bucket.bucket_name || ''}</td>
                  <td>${bucket.creation_date || ''}</td>
                  <td>${bucket.encryption_type || 'None'}</td>
                  <td>${bucket.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${bucket.status_text || ''}
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

  // 버전 관리 결과 HTML 생성
  createVersioningResultHtml(data) {
    const checkId = 's3-versioning';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.buckets.forEach(bucket => {
      const statusText = bucket.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(bucket);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.buckets.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${buckets.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createVersioningTable(data.data.buckets)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createVersioningTable(buckets)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>버전 관리 설정 분석 (${data.data.total_buckets_count}개)</h4>
        <ul class="nav nav-tabs" id="versioningTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="versioningTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 버전 관리 테이블 생성
  createVersioningTable(buckets) {
    if (!buckets || buckets.length === 0) return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    
    return `
      <style>
        .versioning-table th:nth-child(1) { width: 25%; }
        .versioning-table th:nth-child(2) { width: 15%; }
        .versioning-table th:nth-child(3) { width: 15%; }
        .versioning-table th:nth-child(4) { width: 15%; }
        .versioning-table th:nth-child(5) { width: 15%; }
        .versioning-table th:nth-child(6) { width: 15%; }
        .versioning-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table versioning-table">
          <thead>
            <tr>
              <th>버킷 이름</th>
              <th>생성일</th>
              <th>버전 관리</th>
              <th>프로덕션 환경</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              let statusClass = '';
              let statusIcon = '';
              
              if (bucket.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (bucket.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (bucket.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${bucket.bucket_name || ''}</td>
                  <td>${bucket.creation_date || ''}</td>
                  <td>${bucket.versioning_status || 'Unknown'}</td>
                  <td>${bucket.is_production ? '예' : '아니오'}</td>
                  <td>${bucket.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${bucket.status_text || ''}
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

  // 수명 주기 정책 결과 HTML 생성
  createLifecycleResultHtml(data) {
    const checkId = 's3-lifecycle';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.buckets.forEach(bucket => {
      const statusText = bucket.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(bucket);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.buckets.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${buckets.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createLifecycleTable(data.data.buckets)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createLifecycleTable(buckets)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>수명 주기 정책 분석 (${data.data.total_buckets_count}개)</h4>
        <ul class="nav nav-tabs" id="lifecycleTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="lifecycleTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 수명 주기 정책 테이블 생성
  createLifecycleTable(buckets) {
    if (!buckets || buckets.length === 0) return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    
    return `
      <style>
        .lifecycle-table th:nth-child(1) { width: 25%; }
        .lifecycle-table th:nth-child(2) { width: 15%; }
        .lifecycle-table th:nth-child(3) { width: 15%; }
        .lifecycle-table th:nth-child(4) { width: 15%; }
        .lifecycle-table th:nth-child(5) { width: 15%; }
        .lifecycle-table th:nth-child(6) { width: 15%; }
        .lifecycle-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table lifecycle-table">
          <thead>
            <tr>
              <th>버킷 이름</th>
              <th>생성일</th>
              <th>수명 주기 규칙</th>
              <th>버전 관리</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              let statusClass = '';
              let statusIcon = '';
              
              if (bucket.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (bucket.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (bucket.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${bucket.bucket_name || ''}</td>
                  <td>${bucket.creation_date || ''}</td>
                  <td>${bucket.has_lifecycle_rules ? `${bucket.rule_count}개 규칙` : '없음'}</td>
                  <td>${bucket.versioning_enabled ? '활성화됨' : '비활성화됨'}</td>
                  <td>${bucket.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${bucket.status_text || ''}
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

  // 액세스 로깅 결과 HTML 생성
  createLoggingResultHtml(data) {
    const checkId = 's3-logging';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.buckets.forEach(bucket => {
      const statusText = bucket.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(bucket);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.buckets.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${buckets.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createLoggingTable(data.data.buckets)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const buckets = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createLoggingTable(buckets)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>액세스 로깅 설정 분석 (${data.data.total_buckets_count}개)</h4>
        <ul class="nav nav-tabs" id="loggingTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="loggingTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 액세스 로깅 테이블 생성
  createLoggingTable(buckets) {
    if (!buckets || buckets.length === 0) return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    
    return `
      <style>
        .logging-table th:nth-child(1) { width: 20%; }
        .logging-table th:nth-child(2) { width: 10%; }
        .logging-table th:nth-child(3) { width: 10%; }
        .logging-table th:nth-child(4) { width: 15%; }
        .logging-table th:nth-child(5) { width: 10%; }
        .logging-table th:nth-child(6) { width: 20%; }
        .logging-table th:nth-child(7) { width: 15%; }
        .logging-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table logging-table">
          <thead>
            <tr>
              <th>버킷 이름</th>
              <th>생성일</th>
              <th>로깅</th>
              <th>대상 버킷</th>
              <th>프로덕션</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              let statusClass = '';
              let statusIcon = '';
              
              if (bucket.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (bucket.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (bucket.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (bucket.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${bucket.bucket_name || ''}</td>
                  <td>${bucket.creation_date || ''}</td>
                  <td>${bucket.logging_enabled ? '활성화됨' : '비활성화됨'}</td>
                  <td>${bucket.target_bucket || ''}</td>
                  <td>${bucket.is_production ? '예' : '아니오'}</td>
                  <td>${bucket.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${bucket.status_text || ''}
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