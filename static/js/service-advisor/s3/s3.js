/**
 * S3 서비스 어드바이저 기능
 */

class ServiceAdvisorS3 extends ServiceAdvisorCommon {
  constructor() {
    super();
    this.serviceName = 's3';
  }
  
  // 데이터 테이블 생성
  generateDataTable(data, checkId) {
    if (!data) return '<div class="alert alert-info">표시할 데이터가 없습니다.</div>';
    
    switch (checkId) {
      case 's3-public-access':
        return this.createPublicAccessTable(data);
      case 's3-encryption':
        return this.createEncryptionTable(data);
      case 's3-versioning':
        return this.createVersioningTable(data);
      case 's3-lifecycle':
        return this.createLifecycleTable(data);
      case 's3-logging':
        return this.createLoggingTable(data);
      default:
        return this.createGenericTable(data);
    }
  }
  
  // 퍼블릭 액세스 테이블 생성
  createPublicAccessTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '퍼블릭 액세스 차단', key: 'public_access_blocked', formatter: value => value ? '활성화됨' : '비활성화됨' },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 암호화 테이블 생성
  createEncryptionTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '기본 암호화', key: 'encryption_enabled', formatter: value => value ? '활성화됨' : '비활성화됨' },
      { header: '암호화 유형', key: 'encryption_type', formatter: value => value || 'N/A' },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 버전 관리 테이블 생성
  createVersioningTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '버전 관리', key: 'versioning_enabled', formatter: value => value ? '활성화됨' : '비활성화됨' },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 수명 주기 정책 테이블 생성
  createLifecycleTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '수명 주기 정책', key: 'lifecycle_configured', formatter: value => value ? '구성됨' : '구성되지 않음' },
      { header: '규칙 수', key: 'lifecycle_rules_count', formatter: value => value || 0 },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 로깅 테이블 생성
  createLoggingTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '액세스 로깅', key: 'logging_enabled', formatter: value => value ? '활성화됨' : '비활성화됨' },
      { header: '대상 버킷', key: 'target_bucket', formatter: value => value || 'N/A' },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 일반 테이블 생성
  createGenericTable(data) {
    if (!data.buckets || data.buckets.length === 0) {
      return '<div class="alert alert-info">표시할 버킷이 없습니다.</div>';
    }
    
    return this._createBucketTable(data.buckets, [
      { header: '버킷 이름', key: 'name' },
      { header: '권장 사항', key: 'advice', formatter: value => value || 'N/A' },
      { header: '상태', key: 'status', isStatus: true }
    ]);
  }
  
  // 버킷 테이블 생성 (내부 메서드)
  _createBucketTable(buckets, columns) {
    return `
      <div class="table-responsive">
        <table class="table table-striped table-hover">
          <thead>
            <tr>
              ${columns.map(col => `<th>${col.header}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${buckets.map(bucket => {
              return `
                <tr>
                  ${columns.map(col => {
                    if (col.isStatus) {
                      let statusClass = '';
                      let statusIcon = '';
                      
                      if (bucket.status === 'pass') {
                        statusClass = 'success';
                        statusIcon = 'check-circle';
                      } else if (bucket.status === 'fail') {
                        statusClass = 'warning';
                        statusIcon = 'exclamation-triangle';
                      } else {
                        statusClass = 'secondary';
                        statusIcon = 'question-circle';
                      }
                      
                      return `
                        <td>
                          <span class="resource-status ${statusClass}">
                            <i class="fas fa-${statusIcon}"></i>
                            ${bucket.status_text || ''}
                          </span>
                        </td>
                      `;
                    } else {
                      const value = bucket[col.key];
                      const displayValue = col.formatter ? col.formatter(value) : (value || 'N/A');
                      return `<td>${displayValue}</td>`;
                    }
                  }).join('')}
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
  // S3 서비스 어드바이저 초기화
  window.serviceAdvisor = new ServiceAdvisorS3();
});