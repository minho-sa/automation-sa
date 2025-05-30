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
      
      // 결과 내용 복제
      const contentClone = resultContent.cloneNode(true);
      
      // 결과 내용 정리
      this.cleanupContent(contentClone);
      
      // PDF 컨테이너 생성
      const element = document.createElement('div');
      element.innerHTML = `
        <div style="font-family: Arial, sans-serif; padding: 10px; color: #333; font-size: 10px;">
          <div style="text-align: center; margin-bottom: 10px; border-bottom: 2px solid #232f3e; padding-bottom: 10px;">
            <h1 style="color: #232f3e; margin: 0 0 5px 0; font-size: 16px;">AWS 서비스 어드바이저 검사 결과</h1>
            <p style="color: #666; font-size: 9px; margin: 0;">생성일시: ${dateString}</p>
          </div>
          
          <div style="margin-bottom: 10px; background-color: #f9f9f9; padding: 8px; border-radius: 5px;">
            <h2 style="color: #232f3e; margin: 0 0 5px 0; font-size: 14px;">${checkTitle}</h2>
            <p style="color: #444; margin: 0 0 5px 0; font-size: 9px;">${checkDescription}</p>
            <p style="color: #666; font-style: italic; margin: 0; font-size: 8px;">${lastCheckDate}</p>
          </div>
          
          <div style="margin: 0;">
            ${contentClone.innerHTML}
          </div>
          
          <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 8px; color: #666; text-align: center;">
            <p style="margin: 0;">이 보고서는 AWS 서비스 어드바이저에 의해 자동으로 생성되었습니다.</p>
            <p style="margin: 0;">© ${now.getFullYear()} AWS 서비스 어드바이저</p>
          </div>
        </div>
      `;
      
      // 테이블 스타일 정리
      this.styleTablesForPdf(element);
      
      // 텍스트 스타일 정리
      this.styleTextForPdf(element);
      
      // PDF 옵션 설정
      const opt = {
        margin: [5, 5],
        filename: `AWS-서비스-어드바이저-${checkId}-${now.getTime()}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: { 
          scale: 2,
          useCORS: true,
          letterRendering: true
        },
        jsPDF: { 
          unit: 'mm', 
          format: 'a4', 
          orientation: 'portrait',
          compress: true
        }
      };
      
      // PDF 생성 및 다운로드
      html2pdf().from(element).set(opt).save();
      
      console.log('PDF 생성 완료');
    } catch (error) {
      console.error('PDF 생성 중 오류 발생:', error);
      alert('PDF 생성 중 오류가 발생했습니다: ' + error.message);
    }
  }
  
  // 결과 내용 정리
  cleanupContent(contentElement) {
    // 탭 내비게이션 제거
    const tabNavs = contentElement.querySelectorAll('.nav-tabs');
    tabNavs.forEach(nav => nav.remove());
    
    // 탭 콘텐츠 처리
    const tabContents = contentElement.querySelectorAll('.tab-content');
    tabContents.forEach(tabContent => {
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
        tabPanes.forEach((pane, index) => {
          if (index > 0) pane.remove();
        });
      }
    });
    
    // 결과 상태 스타일 정리
    const statusElements = contentElement.querySelectorAll('.check-result-status');
    statusElements.forEach(status => {
      status.style.padding = '5px';
      status.style.marginBottom = '10px';
    });
  }
  
  // 테이블 스타일 정리
  styleTablesForPdf(element) {
    const tables = element.querySelectorAll('table');
    tables.forEach(table => {
      table.style.width = '100%';
      table.style.borderCollapse = 'collapse';
      table.style.marginBottom = '15px';
      table.style.fontSize = '8px';
      
      const ths = table.querySelectorAll('th');
      ths.forEach(th => {
        th.style.backgroundColor = '#f2f2f2';
        th.style.border = '1px solid #ddd';
        th.style.padding = '4px';
        th.style.textAlign = 'left';
        th.style.fontSize = '8px';
        th.style.fontWeight = 'bold';
        th.style.wordBreak = 'break-word';
        th.style.maxWidth = '100px';
      });
      
      const tds = table.querySelectorAll('td');
      tds.forEach(td => {
        td.style.border = '1px solid #ddd';
        td.style.padding = '4px';
        td.style.fontSize = '8px';
        td.style.wordBreak = 'break-word';
        td.style.maxWidth = '100px';
      });
    });
  }
  
  // 텍스트 스타일 정리
  styleTextForPdf(element) {
    // 모든 텍스트 요소의 글자 크기 조정
    const textElements = element.querySelectorAll('p, span, div, li');
    textElements.forEach(el => {
      if (!el.style.fontSize) {
        el.style.fontSize = '8px';
      }
    });
    
    // 상태 아이콘 크기 조정
    const statusIcons = element.querySelectorAll('.resource-status');
    statusIcons.forEach(icon => {
      icon.style.fontSize = '8px';
      icon.style.padding = '2px 4px';
    });
  }
}

// 페이지 로드 시 PDF 내보내기 기능 초기화
document.addEventListener('DOMContentLoaded', () => {
  new ServiceAdvisorPdfExport();
});