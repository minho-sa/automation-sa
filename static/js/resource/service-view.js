/**
 * 서비스 정보 보기 페이지 JavaScript
 */

// 서비스 뷰 모듈
const ServiceView = {
    // 모든 섹션 토글 기능 설정
    setupSectionsToggle: function(toggleBtnId) {
        const toggleBtn = document.getElementById(toggleBtnId);
        if (!toggleBtn) return;
        
        const toggleBtnText = document.getElementById('toggle-btn-text');
        
        // 초기 상태 확인 - 모든 섹션이 펼쳐져 있는지 확인
        const allSections = document.querySelectorAll('.service-section-header[data-bs-target]');
        let allExpanded = true;
        allSections.forEach(section => {
            const targetId = section.getAttribute('data-bs-target');
            const target = document.querySelector(targetId);
            if (target && !target.classList.contains('show')) {
                allExpanded = false;
            }
        });
        
        // 초기 상태 설정
        let isExpanded = allExpanded;
        if (isExpanded) {
            toggleBtnText.textContent = '모두 접기';
            toggleBtn.querySelector('i').className = 'fas fa-chevron-up';
        }
        
        toggleBtn.addEventListener('click', function() {
            const icon = this.querySelector('i');
            
            if (isExpanded) {
                // 모두 접기
                allSections.forEach(section => {
                    const targetId = section.getAttribute('data-bs-target');
                    const target = document.querySelector(targetId);
                    if (target && target.classList.contains('show')) {
                        target.classList.remove('show');
                        section.setAttribute('aria-expanded', 'false');
                        const toggleIcon = section.querySelector('.toggle-icon i');
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(0deg)';
                    }
                });
                
                // 버튼 상태 변경
                icon.className = 'fas fa-chevron-down';
                toggleBtnText.textContent = '모두 펼치기';
                isExpanded = false;
            } else {
                // 모두 펼치기
                allSections.forEach(section => {
                    const targetId = section.getAttribute('data-bs-target');
                    const target = document.querySelector(targetId);
                    if (target && !target.classList.contains('show')) {
                        target.classList.add('show');
                        section.setAttribute('aria-expanded', 'true');
                        const toggleIcon = section.querySelector('.toggle-icon i');
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(180deg)';
                    }
                });
                
                // 버튼 상태 변경
                icon.className = 'fas fa-chevron-up';
                toggleBtnText.textContent = '모두 접기';
                isExpanded = true;
            }
        });
    },
    
    // 개별 섹션 토글 기능 설정
    setupSectionToggle: function(selectorOrElements) {
        const sectionHeaders = typeof selectorOrElements === 'string' 
            ? document.querySelectorAll(selectorOrElements) 
            : selectorOrElements;
        
        sectionHeaders.forEach(header => {
            const targetId = header.getAttribute('data-bs-target');
            const target = document.querySelector(targetId);
            const toggleIcon = header.querySelector('.toggle-icon i');
            
            if (target) {
                // 초기 상태 설정
                const isExpanded = target.classList.contains('show');
                header.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
                
                if (toggleIcon) {
                    toggleIcon.style.transform = isExpanded ? 'rotate(180deg)' : 'rotate(0deg)';
                }
                
                // 클릭 이벤트 설정
                header.addEventListener('click', () => {
                    const isCurrentlyExpanded = target.classList.contains('show');
                    
                    if (isCurrentlyExpanded) {
                        target.classList.remove('show');
                        header.setAttribute('aria-expanded', 'false');
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(0deg)';
                    } else {
                        target.classList.add('show');
                        header.setAttribute('aria-expanded', 'true');
                        if (toggleIcon) toggleIcon.style.transform = 'rotate(180deg)';
                    }
                });
            }
        });
    },
    
    // 테이블 정렬 기능 설정
    setupTableSort: function(selectorOrElements) {
        const tables = typeof selectorOrElements === 'string' 
            ? document.querySelectorAll(selectorOrElements) 
            : selectorOrElements;
        
        tables.forEach(table => {
            const headers = table.querySelectorAll('th[data-sort]');
            
            headers.forEach(header => {
                header.addEventListener('click', function() {
                    const sortKey = this.getAttribute('data-sort');
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    
                    // 정렬 방향 결정
                    let sortDirection = 'asc';
                    if (this.classList.contains('sort-asc')) {
                        sortDirection = 'desc';
                        this.classList.remove('sort-asc');
                        this.classList.add('sort-desc');
                    } else if (this.classList.contains('sort-desc')) {
                        sortDirection = 'asc';
                        this.classList.remove('sort-desc');
                        this.classList.add('sort-asc');
                    } else {
                        this.classList.add('sort-asc');
                        
                        // 다른 헤더의 정렬 클래스 제거
                        headers.forEach(h => {
                            if (h !== this) {
                                h.classList.remove('sort-asc', 'sort-desc');
                            }
                        });
                    }
                    
                    // 행 정렬
                    rows.sort((a, b) => {
                        const cellA = a.querySelector(`td[data-column="${sortKey}"]`);
                        const cellB = b.querySelector(`td[data-column="${sortKey}"]`);
                        
                        if (!cellA || !cellB) return 0;
                        
                        let valueA = cellA.textContent.trim();
                        let valueB = cellB.textContent.trim();
                        
                        // 숫자 값인 경우 숫자로 변환
                        if (!isNaN(valueA) && !isNaN(valueB)) {
                            valueA = parseFloat(valueA);
                            valueB = parseFloat(valueB);
                        }
                        
                        // 정렬 방향에 따라 비교
                        if (sortDirection === 'asc') {
                            return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
                        } else {
                            return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
                        }
                    });
                    
                    // 정렬된 행을 테이블에 다시 추가
                    rows.forEach(row => tbody.appendChild(row));
                });
            });
        });
    },
    
    // 테이블 필터링 기능 설정
    setupTableFilter: function(inputId, tableId) {
        const filterInput = document.getElementById(inputId);
        const table = document.getElementById(tableId);
        
        if (!filterInput || !table) return;
        
        filterInput.addEventListener('keyup', function() {
            const filter = this.value.toLowerCase();
            const rows = table.querySelectorAll('tbody tr');
            
            rows.forEach(row => {
                const text = row.textContent.toLowerCase();
                row.style.display = text.includes(filter) ? '' : 'none';
            });
        });
    },
    
    // 상세 정보 패널 토글 기능 설정
    setupDetailPanelToggle: function() {
        const toggleButtons = document.querySelectorAll('.detail-toggle');
        
        toggleButtons.forEach(button => {
            const targetId = button.getAttribute('data-target');
            const target = document.getElementById(targetId);
            
            if (target) {
                button.addEventListener('click', function(e) {
                    e.preventDefault();
                    e.stopPropagation();
                    
                    if (target.style.display === 'none' || !target.style.display) {
                        target.style.display = 'table-row';
                        this.querySelector('i').className = 'fas fa-chevron-up';
                    } else {
                        target.style.display = 'none';
                        this.querySelector('i').className = 'fas fa-chevron-down';
                    }
                });
            }
        });
    },
    
    // 탭 기능 설정
    setupTabs: function() {
        const tabs = document.querySelectorAll('.resource-tab');
        
        tabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                const tabContent = document.getElementById(tabId);
                
                if (!tabContent) return;
                
                // 같은 탭 그룹 내의 모든 탭 비활성화
                const tabGroup = this.parentElement;
                const siblingTabs = tabGroup.querySelectorAll('.resource-tab');
                siblingTabs.forEach(t => t.classList.remove('active'));
                
                // 같은 탭 그룹 내의 모든 콘텐츠 숨기기
                const tabContents = tabGroup.parentElement.querySelectorAll('.resource-tab-content');
                tabContents.forEach(c => c.classList.remove('active'));
                
                // 선택한 탭 활성화
                this.classList.add('active');
                
                // 선택한 콘텐츠 표시
                tabContent.classList.add('active');
            });
        });
    },
    
    // 메트릭 게이지 설정
    setupMetricGauge: function(selector, value, max = 100) {
        const gauges = document.querySelectorAll(selector);
        
        gauges.forEach(gauge => {
            const fill = gauge.querySelector('.metric-gauge-fill');
            if (fill) {
                const percentage = Math.min(Math.max(value, 0), max) / max * 100;
                fill.style.width = `${percentage}%`;
                
                // 값에 따라 색상 설정
                if (percentage < 30) {
                    fill.classList.add('low');
                } else if (percentage < 70) {
                    fill.classList.add('medium');
                } else {
                    fill.classList.add('high');
                }
            }
        });
    },
    
    // 데이터 내보내기 기능 설정
    setupDataExport: function(selector, data, filename) {
        const exportButtons = document.querySelectorAll(selector);
        
        exportButtons.forEach(button => {
            const format = button.getAttribute('data-format');
            
            button.addEventListener('click', function() {
                if (format === 'json') {
                    ServiceView.exportJSON(data, filename);
                } else if (format === 'csv') {
                    ServiceView.exportCSV(data, filename);
                }
            });
        });
    },
    
    // JSON 형식으로 데이터 내보내기
    exportJSON: function(data, filename) {
        const jsonString = JSON.stringify(data, null, 2);
        const blob = new Blob([jsonString], { type: 'application/json' });
        
        ServiceView.downloadFile(blob, `${filename}.json`);
    },
    
    // CSV 형식으로 데이터 내보내기
    exportCSV: function(data, filename) {
        if (!Array.isArray(data) || data.length === 0) {
            console.error('CSV 내보내기를 위해서는 배열 형태의 데이터가 필요합니다.');
            return;
        }
        
        // 헤더 생성
        const headers = Object.keys(data[0]);
        let csvContent = headers.join(',') + '\n';
        
        // 데이터 행 생성
        data.forEach(item => {
            const row = headers.map(header => {
                const value = item[header];
                // 문자열에 쉼표가 포함된 경우 따옴표로 묶기
                return typeof value === 'string' && value.includes(',') 
                    ? `"${value}"` 
                    : value;
            });
            csvContent += row.join(',') + '\n';
        });
        
        const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
        ServiceView.downloadFile(blob, `${filename}.csv`);
    },
    
    // 파일 다운로드
    downloadFile: function(blob, filename) {
        const link = document.createElement('a');
        link.href = URL.createObjectURL(blob);
        link.download = filename;
        link.style.display = 'none';
        
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    },
    
    // 바이트 단위 변환 (B -> KB, MB, GB, TB)
    formatBytes: function(bytes, decimals = 2) {
        if (bytes === 0) return '0 Bytes';
        
        const k = 1024;
        const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB', 'PB', 'EB', 'ZB', 'YB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(decimals)) + ' ' + sizes[i];
    },
    
    // 날짜 포맷팅
    formatDate: function(dateString) {
        if (!dateString) return '';
        
        const date = new Date(dateString);
        return date.toLocaleString();
    },
    
    // 초기화 함수
    init: function() {
        // 모든 섹션 토글 기능 설정
        this.setupSectionsToggle('toggle-sections-btn');
        
        // 개별 섹션 토글 기능 설정
        this.setupSectionToggle('.service-section-header');
        
        // 테이블 정렬 기능 설정
        this.setupTableSort('.resource-table');
        
        // 테이블 필터링 기능 설정
        const filterInputs = document.querySelectorAll('.filter-input');
        filterInputs.forEach(input => {
            const tableId = input.getAttribute('data-table');
            if (tableId) {
                this.setupTableFilter(input.id, tableId);
            }
        });
        
        // 상세 정보 패널 토글 기능 설정
        this.setupDetailPanelToggle();
        
        // 탭 기능 설정
        this.setupTabs();
    }
};

// 문서 로드 완료 시 초기화
document.addEventListener('DOMContentLoaded', function() {
    ServiceView.init();
});