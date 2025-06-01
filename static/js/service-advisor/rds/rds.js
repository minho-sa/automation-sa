/**
 * RDS 서비스 어드바이저 기능
 */

class ServiceAdvisorRDS extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.serviceName = 'rds';
  }
  
  // 데이터 테이블 생성
  generateDataTable(data, checkId) {
    if (!data) return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    
    switch (checkId) {
      case 'rds-backup-retention':
        return this.createBackupRetentionTable(data);
      case 'rds-multi-az':
        return this.createMultiAzTable(data);
      case 'rds-encryption':
        return this.createEncryptionTable(data);
      case 'rds-public-access':
        return this.createPublicAccessTable(data);
      case 'rds-instance-sizing':
        return this.createInstanceSizingTable(data);
      default:
        return this.createGenericTable(data);
    }
  }
  
  // 백업 보존 기간 테이블 생성
  createBackupRetentionTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>백업 보존 기간</th>
              <th>권장 기간</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.backup_retention_period || 0} 일</td>
                  <td>${instance.recommended_retention || 7} 일</td>
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
  createMultiAzTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>다중 AZ</th>
              <th>환경</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.multi_az ? '활성화됨' : '비활성화됨'}</td>
                  <td>${instance.environment || 'N/A'}</td>
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
  
  // 암호화 테이블 생성
  createEncryptionTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>암호화</th>
              <th>KMS 키</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.storage_encrypted ? '활성화됨' : '비활성화됨'}</td>
                  <td>${instance.kms_key_id || 'N/A'}</td>
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
  
  // 일반 테이블 생성
  createGenericTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>권장 사항</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.advice || 'N/A'}</td>
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
  
  // 인스턴스 크기 테이블 생성
  createInstanceSizingTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>인스턴스 클래스</th>
              <th>평균 CPU</th>
              <th>평균 메모리</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.instance_class || 'N/A'}</td>
                  <td>${instance.avg_cpu !== undefined ? `${instance.avg_cpu}%` : 'N/A'}</td>
                  <td>${instance.avg_memory !== undefined ? `${instance.avg_memory}%` : 'N/A'}</td>
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
  
  // 공개 액세스 테이블 생성
  createPublicAccessTable(data) {
    if (!data.instances || data.instances.length === 0) {
      return '<div class="alert alert-info">표시할 인스턴스가 없습니다.</div>';
    }
    
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              <th>인스턴스 식별자</th>
              <th>공개 액세스</th>
              <th>상태</th>
            </tr>
          </thead>
          <tbody>
            ${data.instances.map(instance => {
              let statusClass = '';
              let statusIcon = '';
              
              if (instance.status === 'pass') {
                statusClass = 'success';
                statusIcon = 'check-circle';
              } else if (instance.status === 'fail') {
                statusClass = 'warning';
                statusIcon = 'exclamation-triangle';
              } else {
                statusClass = 'secondary';
                statusIcon = 'question-circle';
              }
              
              return `
                <tr>
                  <td>${instance.identifier || 'N/A'}</td>
                  <td>${instance.publicly_accessible ? '활성화됨' : '비활성화됨'}</td>
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
  // RDS 서비스 어드바이저 초기화
  window.serviceAdvisor = new ServiceAdvisorRDS();
});