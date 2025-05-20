/**
 * AWS 서비스 선택 체크박스 관련 기능
 */
document.addEventListener('DOMContentLoaded', function() {
    // 체크박스 상태 변경 시 시각적 피드백 제공
    const serviceCheckboxes = document.querySelectorAll('.service-checkbox');
    
    serviceCheckboxes.forEach(checkbox => {
        // 초기 상태 설정
        updateCheckboxState(checkbox);
        
        // 변경 이벤트 리스너 추가
        checkbox.addEventListener('change', function() {
            updateCheckboxState(this);
        });
    });
    
    // 체크박스 상태에 따른 시각적 업데이트
    function updateCheckboxState(checkbox) {
        const container = checkbox.closest('.awsui-checkbox-container');
        if (container) {
            if (checkbox.checked) {
                container.classList.add('checked');
            } else {
                container.classList.remove('checked');
            }
        }
    }
    
    // 모두 선택 버튼
    const selectAllBtn = document.getElementById('select-all-services');
    if (selectAllBtn) {
        selectAllBtn.addEventListener('click', function() {
            serviceCheckboxes.forEach(checkbox => {
                checkbox.checked = true;
                updateCheckboxState(checkbox);
            });
        });
    }
    
    // 모두 선택 해제 버튼
    const deselectAllBtn = document.getElementById('deselect-all-services');
    if (deselectAllBtn) {
        deselectAllBtn.addEventListener('click', function() {
            serviceCheckboxes.forEach(checkbox => {
                checkbox.checked = false;
                updateCheckboxState(checkbox);
            });
        });
    }
});