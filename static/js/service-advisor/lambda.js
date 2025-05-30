/**
 * Lambda 서비스 어드바이저 기능
 * Lambda 서비스 관련 검사 항목을 처리합니다.
 */
class ServiceAdvisorLambda extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.checkHandlers = {
      'lambda-memory-size': {
        createResultHtml: this.createMemorySizeResultHtml.bind(this),
        createTable: this.createMemorySizeTable.bind(this)
      },
      'lambda-timeout': {
        createResultHtml: this.createTimeoutResultHtml.bind(this),
        createTable: this.createTimeoutTable.bind(this)
      },
      'lambda-runtime': {
        createResultHtml: this.createRuntimeResultHtml.bind(this),
        createTable: this.createRuntimeTable.bind(this)
      },
      'lambda-tags': {
        createResultHtml: this.createTagsResultHtml.bind(this),
        createTable: this.createTagsTable.bind(this)
      },
      'lambda-provisioned-concurrency': {
        createResultHtml: this.createProvisionedConcurrencyResultHtml.bind(this),
        createTable: this.createProvisionedConcurrencyTable.bind(this)
      },
      'lambda-code-signing': {
        createResultHtml: this.createCodeSigningResultHtml.bind(this),
        createTable: this.createCodeSigningTable.bind(this)
      },
      'lambda-least-privilege': {
        createResultHtml: this.createLeastPrivilegeResultHtml.bind(this),
        createTable: this.createLeastPrivilegeTable.bind(this)
      }
    };
  }

  // 검사 실행 (Lambda 서비스 전용)
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
    fetch(`/api/service-advisor/lambda/run-check`, {
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

  // 결과 HTML 생성 (Lambda 서비스 전용)
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

  // 메모리 크기 결과 HTML 생성
  createMemorySizeResultHtml(data) {
    const checkId = 'lambda-memory-size';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createMemorySizeTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createMemorySizeTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>메모리 크기 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="memorySizeTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="memorySizeTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 타임아웃 결과 HTML 생성
  createTimeoutResultHtml(data) {
    const checkId = 'lambda-timeout';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createTimeoutTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createTimeoutTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>타임아웃 설정 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="timeoutTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="timeoutTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 런타임 버전 결과 HTML 생성
  createRuntimeResultHtml(data) {
    const checkId = 'lambda-runtime';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createRuntimeTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createRuntimeTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>런타임 버전 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="runtimeTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="runtimeTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 태그 관리 결과 HTML 생성
  createTagsResultHtml(data) {
    const checkId = 'lambda-tags';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createTagsTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createTagsTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>태그 관리 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="tagsTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="tagsTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 메모리 크기 테이블 생성
  createMemorySizeTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .memory-table th:nth-child(1) { width: 25%; }
        .memory-table th:nth-child(2) { width: 10%; }
        .memory-table th:nth-child(3) { width: 10%; }
        .memory-table th:nth-child(4) { width: 10%; }
        .memory-table th:nth-child(5) { width: 30%; }
        .memory-table th:nth-child(6) { width: 15%; }
        .memory-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table memory-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>메모리 크기</th>
              <th>평균 사용률</th>
              <th>최대 사용률</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.memory_size || ''}MB</td>
                  <td>${func.avg_memory !== undefined && func.avg_memory !== 'N/A' && func.avg_memory !== 'Error' ? `${func.avg_memory}%` : func.avg_memory}</td>
                  <td>${func.max_memory !== undefined && func.max_memory !== 'N/A' && func.max_memory !== 'Error' ? `${func.max_memory}%` : func.max_memory}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 타임아웃 테이블 생성
  createTimeoutTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .timeout-table th:nth-child(1) { width: 25%; }
        .timeout-table th:nth-child(2) { width: 10%; }
        .timeout-table th:nth-child(3) { width: 10%; }
        .timeout-table th:nth-child(4) { width: 10%; }
        .timeout-table th:nth-child(5) { width: 30%; }
        .timeout-table th:nth-child(6) { width: 15%; }
        .timeout-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table timeout-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>타임아웃</th>
              <th>평균 실행 시간</th>
              <th>최대 실행 시간</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.timeout || ''}초</td>
                  <td>${func.avg_duration !== undefined && func.avg_duration !== 'N/A' && func.avg_duration !== 'Error' ? `${func.avg_duration}초` : func.avg_duration}</td>
                  <td>${func.max_duration !== undefined && func.max_duration !== 'N/A' && func.max_duration !== 'Error' ? `${func.max_duration}초` : func.max_duration}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 런타임 테이블 생성
  createRuntimeTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .runtime-table th:nth-child(1) { width: 25%; }
        .runtime-table th:nth-child(2) { width: 15%; }
        .runtime-table th:nth-child(3) { width: 15%; }
        .runtime-table th:nth-child(4) { width: 30%; }
        .runtime-table th:nth-child(5) { width: 15%; }
        .runtime-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table runtime-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>현재 런타임</th>
              <th>권장 런타임</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.runtime || ''}</td>
                  <td>${func.recommended_runtime || '해당 없음'}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 태그 테이블 생성
  createTagsTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .tags-table th:nth-child(1) { width: 25%; }
        .tags-table th:nth-child(2) { width: 20%; }
        .tags-table th:nth-child(3) { width: 20%; }
        .tags-table th:nth-child(4) { width: 20%; }
        .tags-table th:nth-child(5) { width: 15%; }
        .tags-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table tags-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>기존 태그</th>
              <th>누락된 태그</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'warning') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.existing_tags && func.existing_tags.length > 0 ? func.existing_tags.join(', ') : '없음'}</td>
                  <td>${func.missing_tags && func.missing_tags.length > 0 ? func.missing_tags.join(', ') : '없음'}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 프로비저닝된 동시성 결과 HTML 생성
  createProvisionedConcurrencyResultHtml(data) {
    const checkId = 'lambda-provisioned-concurrency';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createProvisionedConcurrencyTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createProvisionedConcurrencyTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>프로비저닝된 동시성 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="provisionedConcurrencyTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="provisionedConcurrencyTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 프로비저닝된 동시성 테이블 생성
  createProvisionedConcurrencyTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .provisioned-concurrency-table th:nth-child(1) { width: 25%; }
        .provisioned-concurrency-table th:nth-child(2) { width: 15%; }
        .provisioned-concurrency-table th:nth-child(3) { width: 15%; }
        .provisioned-concurrency-table th:nth-child(4) { width: 15%; }
        .provisioned-concurrency-table th:nth-child(5) { width: 15%; }
        .provisioned-concurrency-table th:nth-child(6) { width: 15%; }
        .provisioned-concurrency-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table provisioned-concurrency-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>프로비저닝된 동시성</th>
              <th>시간당 평균 호출</th>
              <th>최대 동시 실행</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.provisioned_concurrency !== null && func.provisioned_concurrency !== undefined ? func.provisioned_concurrency : '설정 안됨'}</td>
                  <td>${func.avg_invocations_per_hour !== 'N/A' && func.avg_invocations_per_hour !== 'Error' ? func.avg_invocations_per_hour : func.avg_invocations_per_hour}</td>
                  <td>${func.max_concurrent_executions !== 'N/A' && func.max_concurrent_executions !== 'Error' ? func.max_concurrent_executions : func.max_concurrent_executions}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 코드 서명 결과 HTML 생성
  createCodeSigningResultHtml(data) {
    const checkId = 'lambda-code-signing';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createCodeSigningTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createCodeSigningTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>코드 서명 구성 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="codeSigningTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="codeSigningTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 코드 서명 테이블 생성
  createCodeSigningTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .code-signing-table th:nth-child(1) { width: 25%; }
        .code-signing-table th:nth-child(2) { width: 15%; }
        .code-signing-table th:nth-child(3) { width: 15%; }
        .code-signing-table th:nth-child(4) { width: 30%; }
        .code-signing-table th:nth-child(5) { width: 15%; }
        .code-signing-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table code-signing-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>프로덕션 환경</th>
              <th>코드 서명 구성</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.is_production ? '예' : '아니오'}</td>
                  <td>${func.has_code_signing ? '구성됨' : '구성되지 않음'}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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

  // 최소 권한 원칙 결과 HTML 생성
  createLeastPrivilegeResultHtml(data) {
    const checkId = 'lambda-least-privilege';
    
    // 상태별 그룹화
    const statusGroups = {};
    data.data.functions.forEach(func => {
      const statusText = func.status_text || '기타';
      if (!statusGroups[statusText]) {
        statusGroups[statusText] = [];
      }
      statusGroups[statusText].push(func);
    });
    
    // 탭 HTML 생성
    let tabsHtml = `
      <li class="nav-item" role="presentation">
        <button class="nav-link active" id="all-tab-${checkId}" data-bs-toggle="tab" 
          data-bs-target="#all-content-${checkId}" type="button" role="tab" 
          aria-controls="all-content-${checkId}" aria-selected="true">
          전체 (${data.data.functions.length})
        </button>
      </li>
    `;
    
    // 상태별 탭 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabsHtml += `
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="${safeStatusText}-tab-${checkId}" data-bs-toggle="tab" 
            data-bs-target="#${safeStatusText}-content-${checkId}" type="button" role="tab" 
            aria-controls="${safeStatusText}-content-${checkId}" aria-selected="false">
            ${statusText} (${funcs.length})
          </button>
        </li>
      `;
    });
    
    // 탭 콘텐츠 HTML 생성
    let tabContentHtml = `
      <div class="tab-pane fade show active" id="all-content-${checkId}" role="tabpanel" 
        aria-labelledby="all-tab-${checkId}">
        ${this.createLeastPrivilegeTable(data.data.functions)}
      </div>
    `;
    
    // 상태별 탭 콘텐츠 추가
    Object.keys(statusGroups).forEach((statusText, index) => {
      const funcs = statusGroups[statusText];
      const safeStatusText = statusText.replace(/\s+/g, '-');
      tabContentHtml += `
        <div class="tab-pane fade" id="${safeStatusText}-content-${checkId}" role="tabpanel" 
          aria-labelledby="${safeStatusText}-tab-${checkId}">
          ${this.createLeastPrivilegeTable(funcs)}
        </div>
      `;
    });
    
    return `
      <div class="check-result-data">
        <h4>최소 권한 원칙 분석 (${data.data.total_functions_count}개)</h4>
        <ul class="nav nav-tabs" id="leastPrivilegeTabs-${checkId}" role="tablist">
          ${tabsHtml}
        </ul>
        <div class="tab-content" id="leastPrivilegeTabContent-${checkId}">
          ${tabContentHtml}
        </div>
      </div>
    `;
  }

  // 최소 권한 원칙 테이블 생성
  createLeastPrivilegeTable(functions) {
    if (!functions || functions.length === 0) return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    
    return `
      <style>
        .least-privilege-table th:nth-child(1) { width: 25%; }
        .least-privilege-table th:nth-child(2) { width: 15%; }
        .least-privilege-table th:nth-child(3) { width: 25%; }
        .least-privilege-table th:nth-child(4) { width: 20%; }
        .least-privilege-table th:nth-child(5) { width: 15%; }
        .least-privilege-table td { word-break: break-word; }
      </style>
      <div class="table-responsive">
        <table class="awsui-table least-privilege-table">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>실행 역할</th>
              <th>위험한 정책</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else if (func.status === 'error') {
                statusClass = 'danger';
                statusIcon = 'times-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.function_name || ''}</td>
                  <td>${func.role_name || ''}</td>
                  <td>${func.risky_policies && func.risky_policies.length > 0 ? func.risky_policies.join(', ') : '없음'}</td>
                  <td>${func.advice || ''}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${func.status_text || ''}
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