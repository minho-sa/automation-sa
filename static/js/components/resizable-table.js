/**
 * 간단한 테이블 열 크기 조절
 */

let isResizing = false;
let currentColumn = null;
let startX = 0;
let startWidth = 0;

function initTableResize() {
    const tables = document.querySelectorAll('.aws-table table');
    
    tables.forEach(table => {
        table.style.tableLayout = 'fixed';
        
        const headers = table.querySelectorAll('thead th');
        headers.forEach((th, index) => {
            th.style.position = 'relative';
            th.style.cursor = 'default';
            
            // 마우스 이동 시 커서 변경
            th.addEventListener('mousemove', function(e) {
                const rect = th.getBoundingClientRect();
                const isNearRightEdge = e.clientX > rect.right - 8;
                
                if (isNearRightEdge) {
                    th.style.cursor = 'col-resize';
                } else {
                    th.style.cursor = 'default';
                }
            });
            
            // 마우스 다운
            th.addEventListener('mousedown', function(e) {
                const rect = th.getBoundingClientRect();
                const isNearRightEdge = e.clientX > rect.right - 8;
                
                if (isNearRightEdge) {
                    isResizing = true;
                    currentColumn = index;
                    startX = e.clientX;
                    startWidth = th.offsetWidth;
                    
                    document.body.style.cursor = 'col-resize';
                    document.body.style.userSelect = 'none';
                    
                    e.preventDefault();
                }
            });
        });
    });
}

// 전역 마우스 이벤트
document.addEventListener('mousemove', function(e) {
    if (!isResizing) return;
    
    const table = document.querySelector('.aws-table table');
    if (!table) return;
    
    const diff = e.clientX - startX;
    const newWidth = Math.max(50, startWidth + diff);
    
    // 헤더 너비 설정
    const header = table.querySelectorAll('thead th')[currentColumn];
    if (header) {
        header.style.width = newWidth + 'px';
    }
    
    // 모든 행의 해당 열 너비 설정
    const rows = table.querySelectorAll('tbody tr');
    rows.forEach(row => {
        const cell = row.cells[currentColumn];
        if (cell) {
            cell.style.width = newWidth + 'px';
        }
    });
});

document.addEventListener('mouseup', function() {
    if (isResizing) {
        isResizing = false;
        currentColumn = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }
});

// 페이지 로드 시 초기화
document.addEventListener('DOMContentLoaded', initTableResize);

// 동적 테이블을 위한 함수
function initResizableTable() {
    setTimeout(initTableResize, 100);
}

window.initResizableTable = initResizableTable;