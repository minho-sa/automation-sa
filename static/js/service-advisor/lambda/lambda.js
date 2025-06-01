/**
 * Lambda 서비스 어드바이저 기능
 */

class ServiceAdvisorLambda extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.serviceName = 'lambda';
  }
  
  // 데이터 테이블 생성
  generateDataTable(data, checkId) {
    if (!data) return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    
    switch (checkId) {
      case 'lambda-memory-size':
        return this.createMemorySizeTable(data);
      case 'lambda-timeout':
        return this.createTimeoutTable(data);
      case 'lambda-runtime':
        return this.createRuntimeTable(data);
      case 'lambda-tags':
        return this.createTagsTable(data);
      default:
        return this.createGenericTable(data);
    }
  }
  
  // 메모리 크기 테이블 생성
  createMemorySizeTable(data) {
    if (!data.functions || data.functions.length === 0) {
      return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>메모리 크기</th>
              <th>평균 사용량</th>
              <th>최대 사용량</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.name || 'N/A'}</td>
                  <td>${func.memory_size || 'N/A'} MB</td>
                  <td>${func.avg_memory_used || 'N/A'} MB</td>
                  <td>${func.max_memory_used || 'N/A'} MB</td>
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
  createTimeoutTable(data) {
    if (!data.functions || data.functions.length === 0) {
      return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>타임아웃</th>
              <th>평균 실행 시간</th>
              <th>최대 실행 시간</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.name || 'N/A'}</td>
                  <td>${func.timeout || 'N/A'} 초</td>
                  <td>${func.avg_duration || 'N/A'} ms</td>
                  <td>${func.max_duration || 'N/A'} ms</td>
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
  createRuntimeTable(data) {
    if (!data.functions || data.functions.length === 0) {
      return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>현재 런타임</th>
              <th>권장 런타임</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.name || 'N/A'}</td>
                  <td>${func.runtime || 'N/A'}</td>
                  <td>${func.recommended_runtime || 'N/A'}</td>
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
  createTagsTable(data) {
    if (!data.functions || data.functions.length === 0) {
      return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>태그 수</th>
              <th>필수 태그</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.name || 'N/A'}</td>
                  <td>${func.tag_count || 0}</td>
                  <td>${func.missing_tags ? func.missing_tags.join(', ') : '없음'}</td>
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
  
  // 일반 테이블 생성
  createGenericTable(data) {
    if (!data.functions || data.functions.length === 0) {
      return '<div class="alert alert-info">표시할 함수가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>함수 이름</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.functions.map(func => {
              let statusClass = '';
              let statusIcon = '';
              
              if (func.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (func.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${func.name || 'N/A'}</td>
                  <td>${func.advice || 'N/A'}</td>
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

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
  // Lambda 서비스 어드바이저 초기화
  window.serviceAdvisor = new ServiceAdvisorLambda();
});