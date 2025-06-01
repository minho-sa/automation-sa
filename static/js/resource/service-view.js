/**
 * 서비스 정보 보기를 위한 JavaScript 모듈
 */

// 모듈 패턴 사용
const ServiceView = (function() {
    /**
     * 모든 섹션 토글 기능 설정
     * 
     * @param {string} toggleBtnId - 토글 버튼 ID
     */
    function setupSectionsToggle(toggleBtnId) {
        const toggleBtn = document.getElementById(toggleBtnId);
        if (!toggleBtn) return;
        
        const toggleBtnText = toggleBtn.querySelector('span');
        const toggleIcon = toggleBtn.querySelector('i');
        
        // 초기 상태 확인 - 모든 섹션이 펼쳐져 있는지 확인
        const allSections = document.querySelectorAll('.service-section-header[data-bs-target], .awsui-card-header[data-bs-target]');
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
            toggleIcon.className = 'fas fa-chevron-up';
        } else {
            toggleBtnText.textContent = '모두 펼치기';
            toggleIcon.className = 'fas fa-chevron-down';
        }
        
        // 토글 버튼 클릭 이벤트
        toggleBtn.addEventListener('click', function() {
            if (isExpanded) {
                // 모두 접기
                allSections.forEach(section => {
                    const targetId = section.getAttribute('data-bs-target');
                    const target = document.querySelector(targetId);
                    
                    if (target && target.classList.contains('show')) {
                        if (section.hasAttribute('data-bs-toggle')) {
                            // Bootstrap 접기 사용
                            section.click();
                        } else {
                            // 수동 접기
                            target.classList.remove('show');
                            section.setAttribute('aria-expanded', 'false');
                            
                            const sectionIcon = section.querySelector('.toggle-icon i');
                            if (sectionIcon) sectionIcon.style.transform = 'rotate(0deg)';
                        }
                    }
                });
                
                // 버튼 상태 변경
                toggleIcon.className = 'fas fa-chevron-down';
                toggleBtnText.textContent = '모두 펼치기';
                isExpanded = false;
            } else {
                // 모두 펼치기
                allSections.forEach(section => {
                    const targetId = section.getAttribute('data-bs-target');
                    const target = document.querySelector(targetId);
                    
                    if (target && !target.classList.contains('show')) {
                        if (section.hasAttribute('data-bs-toggle')) {
                            // Bootstrap 펼치기 사용
                            section.click();
                        } else {
                            // 수동 펼치기
                            target.classList.add('show');
                            section.setAttribute('aria-expanded', 'true');
                            
                            const sectionIcon = section.querySelector('.toggle-icon i');
                            if (sectionIcon) sectionIcon.style.transform = 'rotate(180deg)';
                        }
                    }
                });
                
                // 버튼 상태 변경
                toggleIcon.className = 'fas fa-chevron-up';
                toggleBtnText.textContent = '모두 접기';
                isExpanded = true;
            }
        });
    }
    
    /**
     * 개별 섹션 토글 기능 설정
     * 
     * @param {string} sectionHeaderSelector - 섹션 헤더 선택자
     */
    function setupSectionToggle(sectionHeaderSelector) {
        const sectionHeaders = document.querySelectorAll(sectionHeaderSelector);
        
        sectionHeaders.forEach(header => {
            if (!header.hasAttribute('data-bs-toggle')) {
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
            }
        });
    }
    
    /**
     * 테이블 정렬 기능 설정
     * 
     * @param {string} tableSelector - 테이블 선택자
     */
    function setupTableSort(tableSelector) {
        const tables = document.querySelectorAll(tableSelector);
        
        tables.forEach(table => {
            const headers = table.querySelectorAll('th[data-sort]');
            
            headers.forEach(header => {
                header.addEventListener('click', () => {
                    const column = header.dataset.sort;
                    const direction = header.dataset.direction === 'asc' ? 'desc' : 'asc';
                    
                    // 모든 헤더의 정렬 방향 초기화
                    headers.forEach(h => {
                        h.dataset.direction = '';
                        h.querySelector('i')?.remove();
                    });
                    
                    // 현재 헤더의 정렬 방향 설정
                    header.dataset.direction = direction;
                    
                    // 정렬 아이콘 추가
                    const icon = document.createElement('i');
                    icon.className = `fas fa-sort-${direction === 'asc' ? 'up' : 'down'} ms-1`;
                    header.appendChild(icon);
                    
                    // 테이블 정렬
                    const tbody = table.querySelector('tbody');
                    const rows = Array.from(tbody.querySelectorAll('tr'));
                    
                    rows.sort((a, b) => {
                        const aValue = a.querySelector(`td[data-column="${column}"]`)?.textContent.trim() || '';
                        const bValue = b.querySelector(`td[data-column="${column}"]`)?.textContent.trim() || '';
                        
                        // 숫자 정렬
                        if (!isNaN(aValue) && !isNaN(bValue)) {
                            return direction === 'asc' 
                                ? parseFloat(aValue) - parseFloat(bValue)
                                : parseFloat(bValue) - parseFloat(aValue);
                        }
                        
                        // 문자열 정렬
                        return direction === 'asc'
                            ? aValue.localeCompare(bValue)
                            : bValue.localeCompare(aValue);
                    });
                    
                    // 정렬된 행을 테이블에 다시 추가
                    rows.forEach(row => tbody.appendChild(row));
                });
            });
        });
    }
    
    /**
     * 테이블 필터링 기능 설정
     * 
     * @param {string} inputSelector - 입력 필드 선택자
     * @param {string} tableSelector - 테이블 선택자
     */
    function setupTableFilter(inputSelector, tableSelector) {
        const inputs = document.querySelectorAll(inputSelector);
        
        inputs.forEach(input => {
            const tableId = input.dataset.target;
            const table = document.getElementById(tableId);
            
            if (table) {
                input.addEventListener('keyup', () => {
                    const filter = input.value.toLowerCase();
                    const rows = table.querySelectorAll('tbody tr');
                    
                    rows.forEach(row => {
                        const text = row.textContent.toLowerCase();
                        row.style.display = text.includes(filter) ? '' : 'none';
                    });
                });
            }
        });
    }
    
    /**
     * 차트 초기화
     * 
     * @param {string} chartId - 차트 캔버스 ID
     * @param {Object} options - 차트 옵션
     * @returns {Chart} 생성된 차트 객체
     */
    function initChart(chartId, options) {
        const ctx = document.getElementById(chartId);
        if (!ctx) return null;
        
        return new Chart(ctx, {
            type: options.type || 'line',
            data: options.data || { labels: [], datasets: [] },
            options: options.chartOptions || {}
        });
    }
    
    // 공개 API
    return {
        setupSectionsToggle,
        setupSectionToggle,
        setupTableSort,
        setupTableFilter,
        initChart
    };
})();