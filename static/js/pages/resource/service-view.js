/**
 * 서비스 뷰 페이지 관련 기능
 */

// ServiceView 모듈 정의
const ServiceView = (function() {
    // 비공개 변수 및 함수
    let _allSectionsExpanded = true;
    
    /**
     * 테이블 필터링 기능 초기화
     */
    function _initTableFilters() {
        const filterInputs = document.querySelectorAll('.filter-input');
        
        filterInputs.forEach(input => {
            input.addEventListener('keyup', function() {
                const tableId = this.getAttribute('data-table');
                const table = document.getElementById(tableId);
                const filterValue = this.value.toLowerCase();
                
                if (table) {
                    const rows = table.querySelectorAll('tbody tr:not([id^="instance-detail-"]):not([id^="bucket-detail-"])');
                    
                    rows.forEach(row => {
                        const text = row.textContent.toLowerCase();
                        const detailRowId = row.getAttribute('id');
                        
                        if (text.includes(filterValue)) {
                            row.style.display = '';
                        } else {
                            row.style.display = 'none';
                            
                            // 상세 정보 행이 있으면 숨김
                            if (detailRowId) {
                                const detailRows = document.querySelectorAll(`tr[data-parent="${detailRowId}"]`);
                                detailRows.forEach(dr => {
                                    dr.style.display = 'none';
                                });
                            }
                        }
                    });
                }
            });
        });
    }
    
    /**
     * 서비스 섹션 토글 기능 초기화
     */
    function _initSectionToggles() {
        const sectionHeaders = document.querySelectorAll('.service-section-header');
        const toggleAllBtn = document.getElementById('toggle-sections-btn');
        const toggleBtnText = document.getElementById('toggle-btn-text');
        
        // 개별 섹션 토글
        sectionHeaders.forEach(header => {
            header.addEventListener('click', function() {
                const targetId = this.getAttribute('data-bs-target');
                const targetElement = document.querySelector(targetId);
                const toggleIcon = this.querySelector('.toggle-icon i');
                
                if (targetElement) {
                    if (targetElement.classList.contains('show')) {
                        targetElement.classList.remove('show');
                        this.setAttribute('aria-expanded', 'false');
                        toggleIcon.className = 'fas fa-chevron-down';
                    } else {
                        targetElement.classList.add('show');
                        this.setAttribute('aria-expanded', 'true');
                        toggleIcon.className = 'fas fa-chevron-up';
                    }
                }
            });
        });
        
        // 모든 섹션 토글
        if (toggleAllBtn) {
            toggleAllBtn.addEventListener('click', function() {
                const sections = document.querySelectorAll('.service-section-body');
                const headers = document.querySelectorAll('.service-section-header');
                
                if (_allSectionsExpanded) {
                    // 모든 섹션 접기
                    sections.forEach(section => {
                        section.classList.remove('show');
                    });
                    
                    headers.forEach(header => {
                        header.setAttribute('aria-expanded', 'false');
                        const toggleIcon = header.querySelector('.toggle-icon i');
                        if (toggleIcon) {
                            toggleIcon.className = 'fas fa-chevron-down';
                        }
                    });
                    
                    toggleBtnText.textContent = '모두 펼치기';
                    this.querySelector('i').className = 'fas fa-chevron-right';
                } else {
                    // 모든 섹션 펼치기
                    sections.forEach(section => {
                        section.classList.add('show');
                    });
                    
                    headers.forEach(header => {
                        header.setAttribute('aria-expanded', 'true');
                        const toggleIcon = header.querySelector('.toggle-icon i');
                        if (toggleIcon) {
                            toggleIcon.className = 'fas fa-chevron-up';
                        }
                    });
                    
                    toggleBtnText.textContent = '모두 접기';
                    this.querySelector('i').className = 'fas fa-chevron-down';
                }
                
                _allSectionsExpanded = !_allSectionsExpanded;
            });
        }
    }
    
    /**
     * 상세 정보 토글 기능 초기화
     */
    function _initDetailToggles() {
        const detailButtons = document.querySelectorAll('.detail-toggle');
        
        detailButtons.forEach(button => {
            button.addEventListener('click', function() {
                const targetId = this.getAttribute('data-target');
                const targetRow = document.getElementById(targetId);
                const icon = this.querySelector('i');
                
                if (targetRow) {
                    if (targetRow.style.display === 'none') {
                        targetRow.style.display = '';
                        icon.className = 'fas fa-chevron-up';
                    } else {
                        targetRow.style.display = 'none';
                        icon.className = 'fas fa-chevron-down';
                    }
                }
            });
        });
    }
    
    /**
     * 리소스 탭 기능 초기화
     */
    function _initResourceTabs() {
        const resourceTabs = document.querySelectorAll('.resource-tab');
        
        resourceTabs.forEach(tab => {
            tab.addEventListener('click', function() {
                const tabId = this.getAttribute('data-tab');
                const tabContent = document.getElementById(tabId);
                
                if (tabContent) {
                    // 같은 그룹의 모든 탭 비활성화
                    const parentTabs = this.parentElement;
                    const siblingTabs = parentTabs.querySelectorAll('.resource-tab');
                    siblingTabs.forEach(t => t.classList.remove('active'));
                    
                    // 같은 그룹의 모든 탭 콘텐츠 숨김
                    const tabContents = this.closest('.detail-panel').querySelectorAll('.resource-tab-content');
                    tabContents.forEach(c => c.classList.remove('active'));
                    
                    // 선택한 탭 및 콘텐츠 활성화
                    this.classList.add('active');
                    tabContent.classList.add('active');
                }
            });
        });
    }
    
    /**
     * 테이블 정렬 기능 초기화
     */
    function _initTableSorting() {
        const sortableHeaders = document.querySelectorAll('th[data-sort]');
        
        sortableHeaders.forEach(header => {
            header.addEventListener('click', function() {
                const table = this.closest('table');
                const tbody = table.querySelector('tbody');
                const rows = Array.from(tbody.querySelectorAll('tr:not([id^="instance-detail-"]):not([id^="bucket-detail-"])'));
                const sortKey = this.getAttribute('data-sort');
                const currentDirection = this.getAttribute('data-sort-direction') || 'none';
                
                // 다른 헤더의 정렬 상태 초기화
                table.querySelectorAll('th[data-sort]').forEach(th => {
                    if (th !== this) {
                        th.removeAttribute('data-sort-direction');
                        th.classList.remove('sort-asc', 'sort-desc');
                    }
                });
                
                // 정렬 방향 결정
                let direction = 'asc';
                if (currentDirection === 'asc') {
                    direction = 'desc';
                } else if (currentDirection === 'desc') {
                    direction = 'none';
                }
                
                // 정렬 방향 표시 업데이트
                this.setAttribute('data-sort-direction', direction);
                this.classList.remove('sort-asc', 'sort-desc');
                if (direction === 'asc') {
                    this.classList.add('sort-asc');
                } else if (direction === 'desc') {
                    this.classList.add('sort-desc');
                }
                
                // 행 정렬
                if (direction !== 'none') {
                    rows.sort((a, b) => {
                        const cellA = a.querySelector(`td[data-column="${sortKey}"]`);
                        const cellB = b.querySelector(`td[data-column="${sortKey}"]`);
                        
                        if (!cellA || !cellB) return 0;
                        
                        let valueA = cellA.textContent.trim();
                        let valueB = cellB.textContent.trim();
                        
                        // 숫자 정렬 처리
                        if (!isNaN(valueA) && !isNaN(valueB)) {
                            valueA = parseFloat(valueA);
                            valueB = parseFloat(valueB);
                        }
                        
                        // 날짜 정렬 처리
                        if (sortKey === 'launch_time' || sortKey === 'creation_date') {
                            valueA = new Date(valueA);
                            valueB = new Date(valueB);
                        }
                        
                        if (valueA < valueB) return direction === 'asc' ? -1 : 1;
                        if (valueA > valueB) return direction === 'asc' ? 1 : -1;
                        return 0;
                    });
                    
                    // 정렬된 행을 테이블에 다시 추가
                    rows.forEach(row => {
                        tbody.appendChild(row);
                        
                        // 상세 정보 행이 있으면 함께 이동
                        const rowId = row.getAttribute('id');
                        if (rowId) {
                            const detailRow = tbody.querySelector(`tr[data-parent="${rowId}"]`);
                            if (detailRow) {
                                tbody.appendChild(detailRow);
                            }
                        }
                    });
                }
            });
        });
    }
    
    // 공개 API
    return {
        /**
         * 초기화 함수
         */
        init: function() {
            _initTableFilters();
            _initSectionToggles();
            _initDetailToggles();
            _initResourceTabs();
            _initTableSorting();
        },
        
        /**
         * JSON 데이터 내보내기
         * @param {Object} data - 내보낼 데이터
         * @param {string} filename - 파일 이름
         */
        exportJSON: function(data, filename) {
            const jsonStr = JSON.stringify(data, null, 2);
            const blob = new Blob([jsonStr], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${filename}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        },
        
        /**
         * CSV 데이터 내보내기
         * @param {Array} data - 내보낼 데이터 배열
         * @param {string} filename - 파일 이름
         */
        exportCSV: function(data, filename) {
            if (!data || !data.length) {
                alert('내보낼 데이터가 없습니다.');
                return;
            }
            
            // 헤더 생성
            const headers = Object.keys(data[0]);
            
            // CSV 문자열 생성
            let csvContent = headers.join(',') + '\n';
            
            data.forEach(item => {
                const row = headers.map(header => {
                    let value = item[header];
                    
                    // 객체나 배열인 경우 JSON 문자열로 변환
                    if (typeof value === 'object' && value !== null) {
                        value = JSON.stringify(value);
                    }
                    
                    // 쉼표나 줄바꿈이 포함된 경우 따옴표로 감싸기
                    if (value && (String(value).includes(',') || String(value).includes('\n'))) {
                        value = `"${String(value).replace(/"/g, '""')}"`;
                    }
                    
                    return value === null || value === undefined ? '' : value;
                }).join(',');
                
                csvContent += row + '\n';
            });
            
            // CSV 파일 다운로드
            const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
            const url = URL.createObjectURL(blob);
            
            const a = document.createElement('a');
            a.href = url;
            a.download = `${filename}.csv`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    };
})();