/**
 * EC2 서비스 어드바이저 기능
 */

class ServiceAdvisorEC2 extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.serviceName = 'ec2';
  }
  
  // 데이터 테이블 생성
  generateDataTable(data, checkId) {
    if (!data) return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    
    if (checkId === 'ec2-security-group') {
      return this.createSecurityGroupTable(data);
    } else if (checkId === 'ec2-instance-type') {
      return this.createInstanceTypeTable(data);
    } else {
      return super.generateDataTable(data, checkId);
    }
  }
  
  // 보안 그룹 테이블 생성
  createSecurityGroupTable(data) {
    if (!data.security_groups || data.security_groups.length === 0) {
      return '<div class="alert alert-info">표시할 보안 그룹이 없습니다.</div>';
    }
    
    const securityGroups = data.security_groups;
    const passedGroups = data.passed_groups || [];
    const failedGroups = data.failed_groups || [];
    
    let resultHtml = `
      <div class="check-result-summary mb-3">
        <h5>보안 그룹 분석 결과</h5>
        <p>총 ${securityGroups.length}개의 보안 그룹 중 ${failedGroups.length}개에 잠재적인 보안 위험이 있습니다.</p>
      </div>
      
      <ul class="nav nav-tabs mb-3" role="tablist">
        <li class="nav-item" role="presentation">
          <button class="nav-link active" id="all-tab" data-bs-toggle="tab" data-bs-target="#all-content" 
            type="button" role="tab" aria-controls="all-content" aria-selected="true">
            전체 (${securityGroups.length})
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="risk-tab" data-bs-toggle="tab" data-bs-target="#risk-content" 
            type="button" role="tab" aria-controls="risk-content" aria-selected="false">
            위험 (${failedGroups.length})
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="safe-tab" data-bs-toggle="tab" data-bs-target="#safe-content" 
            type="button" role="tab" aria-controls="safe-content" aria-selected="false">
            안전 (${passedGroups.length})
          </button>
        </li>
      </ul>
      
      <div class="tab-content">
        <div class="tab-pane fade show active" id="all-content" role="tabpanel" aria-labelledby="all-tab">
          ${this._createSecurityGroupTableContent(securityGroups)}
        </div>
        <div class="tab-pane fade" id="risk-content" role="tabpanel" aria-labelledby="risk-tab">
          ${failedGroups.length > 0 ? this._createSecurityGroupTableContent(failedGroups) : '<div class="alert alert-info">위험한 보안 그룹이 없습니다.</div>'}
        </div>
        <div class="tab-pane fade" id="safe-content" role="tabpanel" aria-labelledby="safe-tab">
          ${passedGroups.length > 0 ? this._createSecurityGroupTableContent(passedGroups) : '<div class="alert alert-info">안전한 보안 그룹이 없습니다.</div>'}
        </div>
      </div>
    `;
    
    return resultHtml;
  }
  
  // 보안 그룹 테이블 내용 생성 (내부 메서드)
  _createSecurityGroupTableContent(securityGroups) {
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>보안 그룹 ID</th>
              <th>이름</th>
              <th>VPC ID</th>
              <th>위험 규칙</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${securityGroups.map(sg => {
              let statusClass = '';
              let statusIcon = '';
              
              if (sg.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (sg.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${sg.id}</td>
                  <td>${sg.sg_name || 'N/A'}</td>
                  <td>${sg.vpc_id || 'N/A'}</td>
                  <td>${sg.risky_rules_count || 0}</td>
                  <td>
                    <span class="resource-status ${statusClass}">
                      <i class="fas fa-${statusIcon}"></i>
                      ${sg.status_text || ''}
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
  createInstanceTypeTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    const instances = data.instances;
    const passedInstances = data.passed_instances || [];
    const failedInstances = data.failed_instances || [];
    const unknownInstances = data.unknown_instances || [];
    
    let resultHtml = `
      <div class="check-result-summary mb-3">
        <h5>인스턴스 타입 분석 결과</h5>
        <p>총 ${instances.length}개의 인스턴스 중 ${failedInstances.length}개가 최적화가 필요합니다.</p>
      </div>
      
      <ul class="nav nav-tabs mb-3" role="tablist">
        <li class="nav-item" role="presentation">
          <button class="nav-link active" id="all-instances-tab" data-bs-toggle="tab" data-bs-target="#all-instances-content" 
            type="button" role="tab" aria-controls="all-instances-content" aria-selected="true">
            전체 (${instances.length})
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="optimize-tab" data-bs-toggle="tab" data-bs-target="#optimize-content" 
            type="button" role="tab" aria-controls="optimize-content" aria-selected="false">
            최적화 필요 (${failedInstances.length})
          </button>
        </li>
        <li class="nav-item" role="presentation">
          <button class="nav-link" id="optimized-tab" data-bs-toggle="tab" data-bs-target="#optimized-content" 
            type="button" role="tab" aria-controls="optimized-content" aria-selected="false">
            최적화됨 (${passedInstances.length})
          </button>
        </li>
      </ul>
      
      <div class="tab-content">
        <div class="tab-pane fade show active" id="all-instances-content" role="tabpanel" aria-labelledby="all-instances-tab">
          ${this._createInstanceTypeTableContent(instances)}
        </div>
        <div class="tab-pane fade" id="optimize-content" role="tabpanel" aria-labelledby="optimize-tab">
          ${failedInstances.length > 0 ? this._createInstanceTypeTableContent(failedInstances) : '<div class="alert alert-info">최적화가 필요한 인스턴스가 없습니다.</div>'}
        </div>
        <div class="tab-pane fade" id="optimized-content" role="tabpanel" aria-labelledby="optimized-tab">
          ${passedInstances.length > 0 ? this._createInstanceTypeTableContent(passedInstances) : '<div class="alert alert-info">최적화된 인스턴스가 없습니다.</div>'}
        </div>
      </div>
    `;
    
    return resultHtml;
  }
  
  // 인스턴스 타입 테이블 내용 생성 (내부 메서드)
  _createInstanceTypeTableContent(instances) {
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 ID</th>
              <th>이름</th>
              <th>타입</th>
              <th>평균 CPU</th>
              <th>최대 CPU</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else if (instance.status === 'unknown') {
                statusClass = 'info';
                statusIcon = 'info-circle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.id}</td>
                  <td>${instance.instance_name || 'N/A'}</td>
                  <td>${instance.instance_type || 'N/A'}</td>
                  <td>${instance.avg_cpu !== 'N/A' ? `${instance.avg_cpu}%` : 'N/A'}</td>
                  <td>${instance.max_cpu !== 'N/A' ? `${instance.max_cpu}%` : 'N/A'}</td>
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

// 페이지 로드 시 실행
document.addEventListener('DOMContentLoaded', function() {
  // EC2 서비스 어드바이저 초기화
  window.serviceAdvisor = new ServiceAdvisorEC2();
});