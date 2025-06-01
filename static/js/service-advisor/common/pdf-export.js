/**
 * PDF 내보내기 기능
 * 서비스 어드바이저 검사 결과를 PDF로 내보내는 기능을 제공합니다.
 */
class ServiceAdvisorPdfExport {
  constructor() {
    this.initEventListeners();
  }

  // 이벤트 리스너 초기화
  initEventListeners() {
    // 검사 완료 후 PDF 다운로드 버튼 표시
    document.addEventListener('checkCompleted', (event) => {
      const checkId = event.detail.checkId;
      const downloadBtn = document.querySelector(`.download-pdf-btn[data-check-id="${checkId}"]`);
      if (downloadBtn) {
        downloadBtn.style.display = 'inline-block';
      }
    });

    // PDF 다운로드 버튼 클릭 이벤트
    document.addEventListener('click', (e) => {
      if (e.target.closest('.download-pdf-btn')) {
        const checkId = e.target.closest('.download-pdf-btn').dataset.checkId;
        this.generatePdf(checkId);
      }
    });
  }

  // PDF 생성 및 다운로드
  generatePdf(checkId) {
    try {
      console.log('PDF 생성 시작:', checkId);
      
      // 검사 결과 컨테이너
      const resultContainer = document.getElementById(`result-${checkId}`);
      const resultContent = resultContainer.querySelector('.check-result-content');
      
      if (!resultContent) {
        console.error('결과 콘텐츠를 찾을 수 없습니다.');
        return;
      }
      
      // 검사 항목 정보
      const checkItem = resultContainer.closest('.check-item');
      const checkTitle = checkItem.querySelector('h3').textContent;
      const checkDescription = checkItem.querySelector('.check-item-description').textContent;
      const lastCheckDate = checkItem.querySelector('.last-check-date').textContent;
      
      // 현재 날짜 및 시간
      const now = new Date();
      const dateString = now.toLocaleDateString('ko-KR', {
        year: 'numeric', month: '2-digit', day: '2-digit',
        hour: '2-digit', minute: '2-digit'
      });
      
      // 로딩 표시
      const loadingEl = document.createElement('div');
      loadingEl.style.cssText = 'position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(255,255,255,0.8); display: flex; justify-content: center; align-items: center; z-index: 9999;';
      loadingEl.innerHTML = '<div style="background: white; padding: 20px; border-radius: 5px; box-shadow: 0 0 10px rgba(0,0,0,0.2);"><p>PDF 생성 중...</p></div>';
      document.body.appendChild(loadingEl);
      
      // 결과 내용 복제 및 정리
      const contentClone = resultContent.cloneNode(true);
      
      // 탭 내비게이션 제거 (PDF에서는 필요 없음)
      const tabNavs = contentClone.querySelectorAll('.nav-tabs');
      tabNavs.forEach(nav => nav.remove());
      
      // "전체" 탭만 표시하고 나머지 탭 콘텐츠 제거
      const allTabContents = contentClone.querySelectorAll('.tab-content');
      allTabContents.forEach(tabContent => {
        // 모든 탭 패널 가져오기
        const tabPanes = tabContent.querySelectorAll('.tab-pane');
        
        if (tabPanes.length > 0) {
          // 첫 번째 탭만 유지하고 나머지 제거
          const firstPane = tabPanes[0];
          firstPane.classList.add('active', 'show');
          firstPane.style.display = 'block';
          
          // 첫 번째 탭이 비어있는지 확인
          if (firstPane.innerHTML.trim() === '') {
            // 비어있다면 다음 탭 사용
            if (tabPanes.length > 1) {
              const secondPane = tabPanes[1];
              secondPane.classList.add('active', 'show');
              secondPane.style.display = 'block';
              tabContent.appendChild(secondPane);
            }
          }
          
          // 나머지 탭 제거
          tabPanes.forEach((pane, i) => {
            if (i > 0) pane.remove();
          });
        }
      });
      
      // 테이블 데이터 추출
      const tables = contentClone.querySelectorAll('table');
      const tableData = [];
      
      tables.forEach(table => {
        const headers = [];
        const rows = [];
        
        // 헤더 추출
        const headerCells = table.querySelectorAll('th');
        headerCells.forEach(cell => {
          headers.push(cell.textContent.trim());
        });
        
        // 행 데이터 추출
        const tableRows = table.querySelectorAll('tbody tr');
        tableRows.forEach(row => {
          const rowData = [];
          const cells = row.querySelectorAll('td');
          cells.forEach(cell => {
            // 상태 아이콘 처리
            const statusIcon = cell.querySelector('.resource-status');
            if (statusIcon) {
              rowData.push({
                text: statusIcon.textContent.trim(),
                style: this.getStatusStyle(statusIcon.className)
              });
            } else {
              rowData.push(cell.textContent.trim());
            }
          });
          rows.push(rowData);
        });
        
        tableData.push({ headers, rows });
      });
      
      // 권장 사항 추출
      const recommendations = [];
      const recElements = contentClone.querySelectorAll('.check-result-recommendations li');
      recElements.forEach(rec => {
        recommendations.push(rec.textContent.trim());
      });
      
      // 상태 메시지 추출
      let statusMessage = '';
      let statusStyle = '';
      const statusElement = contentClone.querySelector('.check-result-status');
      if (statusElement) {
        statusMessage = statusElement.textContent.trim();
        statusStyle = this.getStatusStyle(statusElement.className);
      }
      
      // PDF 문서 정의
      const docDefinition = {
        pageSize: 'A4',
        pageMargins: [20, 20, 20, 20],
        footer: (currentPage, pageCount) => {
          return {
            text: `${currentPage} / ${pageCount}`,
            alignment: 'right',
            margin: [0, 0, 20, 0],
            fontSize: 8,
            color: '#666666'
          };
        },
        content: [
          // 헤더
          {
            text: 'AWS 서비스 어드바이저 검사 결과',
            style: 'header',
            alignment: 'center'
          },
          {
            text: `생성일시: ${dateString}`,
            style: 'subheader',
            alignment: 'center',
            margin: [0, 0, 0, 10]
          },
          // 구분선
          {
            canvas: [
              {
                type: 'line',
                x1: 0, y1: 0,
                x2: 515, y2: 0,
                lineWidth: 1,
                lineColor: '#232f3e'
              }
            ],
            margin: [0, 0, 0, 10]
          },
          // 검사 정보
          {
            style: 'infoBox',
            table: {
              widths: ['*'],
              body: [
                [
                  {
                    stack: [
                      { text: checkTitle, style: 'title' },
                      { text: checkDescription, style: 'description' },
                      { text: lastCheckDate, style: 'date' }
                    ]
                  }
                ]
              ]
            },
            layout: 'noBorders'
          },
          // 상태 메시지
          statusMessage ? {
            text: statusMessage,
            style: statusStyle,
            margin: [0, 10, 0, 10]
          } : {},
          // 권장 사항
          recommendations.length > 0 ? {
            stack: [
              { text: '권장 사항', style: 'sectionHeader', margin: [0, 10, 0, 5] },
              {
                ul: recommendations.map(rec => ({
                  text: rec,
                  style: 'recommendation'
                })),
                margin: [0, 0, 0, 10]
              }
            ]
          } : {},
        ],
        styles: {
          header: {
            fontSize: 18,
            bold: true,
            color: '#232f3e',
            margin: [0, 0, 0, 5]
          },
          subheader: {
            fontSize: 10,
            color: '#666666',
            margin: [0, 0, 0, 10]
          },
          infoBox: {
            margin: [0, 0, 0, 10],
            fillColor: '#f9f9f9'
          },
          title: {
            fontSize: 14,
            bold: true,
            color: '#232f3e',
            margin: [0, 5, 0, 5]
          },
          description: {
            fontSize: 10,
            color: '#444444',
            margin: [0, 0, 0, 5]
          },
          date: {
            fontSize: 9,
            italics: true,
            color: '#666666',
            margin: [0, 0, 0, 5]
          },
          sectionHeader: {
            fontSize: 12,
            bold: true,
            color: '#232f3e',
            margin: [0, 10, 0, 5]
          },
          recommendation: {
            fontSize: 10,
            color: '#444444',
            margin: [0, 2, 0, 2]
          },
          tableHeader: {
            fontSize: 10,
            bold: true,
            color: '#232f3e',
            fillColor: '#f2f2f2',
            alignment: 'left'
          },
          tableCell: {
            fontSize: 9,
            color: '#333333'
          },
          success: {
            color: '#037f0c'
          },
          warning: {
            color: '#d09118'
          },
          danger: {
            color: '#d91515'
          },
          info: {
            color: '#0972d3'
          },
          secondary: {
            color: '#5f6b7a'
          },
          footer: {
            fontSize: 8,
            color: '#666666',
            margin: [0, 10, 0, 0],
            alignment: 'center'
          }
        }
      };
      
      // 테이블 추가
      tableData.forEach((table, index) => {
        if (table.headers.length > 0 && table.rows.length > 0) {
          // 테이블 헤더 스타일 설정
          const headerRow = table.headers.map(header => ({
            text: header,
            style: 'tableHeader'
          }));
          
          // 테이블 행 스타일 설정
          const bodyRows = table.rows.map(row => {
            return row.map(cell => {
              if (typeof cell === 'object' && cell.text && cell.style) {
                return {
                  text: cell.text,
                  style: ['tableCell', cell.style]
                };
              }
              return {
                text: cell,
                style: 'tableCell'
              };
            });
          });
          
          // 테이블 너비 계산 (헤더 개수에 따라)
          const widths = Array(table.headers.length).fill('*');
          
          // 테이블 추가
          docDefinition.content.push({
            margin: [0, 10, 0, 15],
            table: {
              headerRows: 1,
              widths: widths,
              body: [headerRow, ...bodyRows]
            },
            layout: {
              hLineWidth: function(i, node) { return 1; },
              vLineWidth: function(i, node) { return 1; },
              hLineColor: function(i, node) { return '#dddddd'; },
              vLineColor: function(i, node) { return '#dddddd'; },
              paddingLeft: function(i, node) { return 4; },
              paddingRight: function(i, node) { return 4; },
              paddingTop: function(i, node) { return 4; },
              paddingBottom: function(i, node) { return 4; },
              fillColor: function(rowIndex, node, columnIndex) {
                return (rowIndex % 2 === 0) ? '#ffffff' : '#f9f9f9';
              }
            }
          });
        }
      });
      
      // 푸터 추가
      docDefinition.content.push({
        stack: [
          {
            canvas: [
              {
                type: 'line',
                x1: 0, y1: 0,
                x2: 515, y2: 0,
                lineWidth: 1,
                lineColor: '#dddddd'
              }
            ],
            margin: [0, 10, 0, 10]
          },
          {
            text: '이 보고서는 AWS 서비스 어드바이저에 의해 자동으로 생성되었습니다.',
            style: 'footer'
          },
          {
            text: `© ${now.getFullYear()} AWS 서비스 어드바이저`,
            style: 'footer'
          }
        ]
      });
      
      // PDF 생성 및 다운로드
      pdfMake.createPdf(docDefinition).download(`AWS-서비스-어드바이저-${checkId}-${now.getTime()}.pdf`);
      
      // 로딩 제거
      document.body.removeChild(loadingEl);
      
      console.log('PDF 생성 완료');
    } catch (error) {
      console.error('PDF 생성 중 오류 발생:', error);
      
      // 로딩 제거
      const loadingEl = document.querySelector('div[style*="position: fixed"]');
      if (loadingEl) {
        document.body.removeChild(loadingEl);
      }
      
      alert('PDF 생성 중 오류가 발생했습니다: ' + error.message);
    }
  }
  
  // 상태 클래스에 따른 스타일 반환
  getStatusStyle(className) {
    if (className.includes('success')) return 'success';
    if (className.includes('warning')) return 'warning';
    if (className.includes('danger')) return 'danger';
    if (className.includes('info')) return 'info';
    return 'secondary';
  }
}

// 페이지 로드 시 PDF 내보내기 기능 초기화
document.addEventListener('DOMContentLoaded', () => {
  new ServiceAdvisorPdfExport();
});