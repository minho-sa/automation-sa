/**
 * 서비스 어드바이저 메인 스크립트
 * 서비스 어드바이저 페이지의 공통 기능을 처리합니다.
 */
document.addEventListener('DOMContentLoaded', () => {
  // 서비스 어드바이저 객체 초기화
  initServiceAdvisor();
  
  // 검사 버튼 이벤트 리스너 등록
  initCheckButtons();
  
  // 전체 선택 기능 초기화
  initSelectAllChecks();
});

// 서비스 어드바이저 객체 초기화
function initServiceAdvisor() {
  // 현재 페이지 URL에서 서비스 타입 확인
  const currentPath = window.location.pathname;
  let serviceType = '';
  
  if (currentPath.includes('/ec2')) {
    serviceType = 'ec2';
    window.serviceAdvisor = new ServiceAdvisorEC2();
  } else if (currentPath.includes('/s3')) {
    serviceType = 's3';
    window.serviceAdvisor = new ServiceAdvisorS3();
  } else if (currentPath.includes('/rds')) {
    serviceType = 'rds';
    window.serviceAdvisor = new ServiceAdvisorRDS();
  } else if (currentPath.includes('/lambda')) {
    serviceType = 'lambda';
    window.serviceAdvisor = new ServiceAdvisorLambda();
  } else if (currentPath.includes('/iam')) {
    serviceType = 'iam';
    window.serviceAdvisor = new ServiceAdvisorIAM();
  } else {
    console.error('지원되지 않는 서비스 타입입니다.');
    return;
  }
  
  console.log(`서비스 어드바이저 초기화: ${serviceType}`);
}

// 검사 버튼 이벤트 리스너 등록
function initCheckButtons() {
  // 개별 검사 버튼
  document.querySelectorAll('.run-check-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
      const checkId = e.target.closest('.run-check-btn').dataset.checkId;
      if (window.serviceAdvisor) {
        window.serviceAdvisor.runCheck(checkId);
      }
    });
  });
  
  // 선택한 항목 검사 버튼
  const runSelectedBtn = document.getElementById('run-selected-checks');
  if (runSelectedBtn) {
    runSelectedBtn.addEventListener('click', () => {
      const selectedCheckIds = getSelectedCheckIds();
      if (selectedCheckIds.length === 0) {
        alert('검사할 항목을 선택해주세요.');
        return;
      }
      
      if (window.serviceAdvisor) {
        // 선택한 항목 순차적으로 검사
        selectedCheckIds.forEach(checkId => {
          window.serviceAdvisor.runCheck(checkId);
        });
      }
    });
  }
  
  // 선택한 항목 PDF 내려받기 버튼
  const downloadSelectedBtn = document.getElementById('download-selected-checks-pdf');
  if (downloadSelectedBtn) {
    downloadSelectedBtn.addEventListener('click', () => {
      const selectedCheckIds = getSelectedCheckIds();
      if (selectedCheckIds.length === 0) {
        alert('PDF로 내려받을 항목을 선택해주세요.');
        return;
      }
      
      // 선택한 항목 중 검사가 완료된 항목만 필터링
      const completedCheckIds = selectedCheckIds.filter(checkId => {
        const downloadBtn = document.querySelector(`.download-pdf-btn[data-check-id="${checkId}"]`);
        return downloadBtn && downloadBtn.style.display !== 'none';
      });
      
      if (completedCheckIds.length === 0) {
        alert('선택한 항목 중 검사가 완료된 항목이 없습니다. 먼저 검사를 실행해주세요.');
        return;
      }
      
      // 선택한 항목 PDF 생성 및 다운로드
      generateCombinedPdf(completedCheckIds);
    });
  }
}

// 전체 선택 기능 초기화
function initSelectAllChecks() {
  const selectAllCheckbox = document.getElementById('select-all-checks');
  if (!selectAllCheckbox) return;
  
  // 전체 선택 체크박스 이벤트
  selectAllCheckbox.addEventListener('change', (e) => {
    const isChecked = e.target.checked;
    document.querySelectorAll('.check-select').forEach(checkbox => {
      checkbox.checked = isChecked;
    });
    
    // PDF 내려받기 버튼 표시 여부 업데이트
    updateDownloadButtonVisibility();
  });
  
  // 개별 체크박스 이벤트
  document.querySelectorAll('.check-select').forEach(checkbox => {
    checkbox.addEventListener('change', () => {
      // 모든 체크박스가 선택되었는지 확인
      const allChecked = Array.from(document.querySelectorAll('.check-select')).every(cb => cb.checked);
      selectAllCheckbox.checked = allChecked;
      
      // PDF 내려받기 버튼 표시 여부 업데이트
      updateDownloadButtonVisibility();
    });
  });
  
  // 검사 완료 이벤트 리스너 추가
  document.addEventListener('checkCompleted', () => {
    updateDownloadButtonVisibility();
  });
}

// 선택된 검사 항목 ID 배열 반환
function getSelectedCheckIds() {
  const selectedCheckboxes = document.querySelectorAll('.check-select:checked');
  return Array.from(selectedCheckboxes).map(checkbox => checkbox.dataset.checkId);
}

// PDF 내려받기 버튼 표시 여부 업데이트
function updateDownloadButtonVisibility() {
  const downloadBtn = document.getElementById('download-selected-checks-pdf');
  if (!downloadBtn) return;
  
  // 선택된 항목 중 검사가 완료된 항목이 있는지 확인
  const selectedCheckIds = getSelectedCheckIds();
  const hasCompletedChecks = selectedCheckIds.some(checkId => {
    const downloadBtn = document.querySelector(`.download-pdf-btn[data-check-id="${checkId}"]`);
    return downloadBtn && downloadBtn.style.display !== 'none';
  });
  
  // 버튼 표시 여부 설정
  downloadBtn.style.display = hasCompletedChecks ? 'inline-block' : 'none';
}

// 여러 검사 항목을 하나의 PDF로 생성
function generateCombinedPdf(checkIds) {
  if (!checkIds || checkIds.length === 0) return;
  
  try {
    console.log('통합 PDF 생성 시작:', checkIds);
    
    // 현재 날짜 및 시간
    const now = new Date();
    const dateString = now.toLocaleDateString('ko-KR', {
      year: 'numeric', month: '2-digit', day: '2-digit',
      hour: '2-digit', minute: '2-digit'
    });
    
    // PDF 컨테이너 생성
    const element = document.createElement('div');
    element.innerHTML = `
      <div style="font-family: Arial, sans-serif; padding: 10px; color: #333; font-size: 10px;">
        <div style="text-align: center; margin-bottom: 10px; border-bottom: 2px solid #232f3e; padding-bottom: 10px;">
          <h1 style="color: #232f3e; margin: 0 0 5px 0; font-size: 16px;">AWS 서비스 어드바이저 검사 결과</h1>
          <p style="color: #666; font-size: 9px; margin: 0;">생성일시: ${dateString}</p>
        </div>
    `;
    
    // 각 검사 항목 결과 추가
    checkIds.forEach((checkId, index) => {
      const resultContainer = document.getElementById(`result-${checkId}`);
      if (!resultContainer) return;
      
      const resultContent = resultContainer.querySelector('.check-result-content');
      if (!resultContent) return;
      
      const checkItem = resultContainer.closest('.check-item');
      const checkTitle = checkItem.querySelector('h3').textContent;
      const checkDescription = checkItem.querySelector('.check-item-description').textContent;
      const lastCheckDate = checkItem.querySelector('.last-check-date').textContent;
      
      // 결과 내용 복제 및 정리
      const contentClone = resultContent.cloneNode(true);
      
      // 탭 내비게이션 제거
      const tabNavs = contentClone.querySelectorAll('.nav-tabs');
      tabNavs.forEach(nav => nav.remove());
      
      // 탭 콘텐츠 처리
      const tabContents = contentClone.querySelectorAll('.tab-content');
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
          tabPanes.forEach((pane, i) => {
            if (i > 0) pane.remove();
          });
        }
      });
      
      // 페이지 구분선 추가 (첫 번째 항목 제외)
      const pageBreak = index > 0 ? 'page-break-before: always;' : '';
      
      // 검사 항목 결과 추가
      element.innerHTML += `
        <div style="margin-bottom: 20px; ${pageBreak}">
          <div style="margin-bottom: 10px; background-color: #f9f9f9; padding: 8px; border-radius: 5px;">
            <h2 style="color: #232f3e; margin: 0 0 5px 0; font-size: 14px;">${checkTitle}</h2>
            <p style="color: #444; margin: 0 0 5px 0; font-size: 9px;">${checkDescription}</p>
            <p style="color: #666; font-style: italic; margin: 0; font-size: 8px;">${lastCheckDate}</p>
          </div>
          
          <div style="margin: 0;">
            ${contentClone.innerHTML}
          </div>
        </div>
      `;
    });
    
    // 푸터 추가
    element.innerHTML += `
        <div style="margin-top: 15px; padding-top: 10px; border-top: 1px solid #ddd; font-size: 8px; color: #666; text-align: center;">
          <p style="margin: 0;">이 보고서는 AWS 서비스 어드바이저에 의해 자동으로 생성되었습니다.</p>
          <p style="margin: 0;">© ${now.getFullYear()} AWS 서비스 어드바이저</p>
        </div>
      </div>
    `;
    
    // 테이블 스타일 정리
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
    
    // PDF 옵션 설정
    const opt = {
      margin: [5, 5],
      filename: `AWS-서비스-어드바이저-통합-${now.getTime()}.pdf`,
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
    
    console.log('통합 PDF 생성 완료');
  } catch (error) {
    console.error('통합 PDF 생성 중 오류 발생:', error);
    alert('통합 PDF 생성 중 오류가 발생했습니다: ' + error.message);
  }
}