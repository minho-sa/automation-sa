/**
 * 수집 데이터 관리를 위한 JavaScript 모듈
 */

// 모듈 패턴 사용
const CollectionManager = (function() {
    // 비공개 변수
    let statusCheckInterval = null;
    
    /**
     * 수집 데이터 삭제
     * 
     * @param {string} collectionId - 삭제할 수집 데이터 ID
     * @param {function} onSuccess - 성공 시 콜백 함수
     * @param {function} onError - 오류 시 콜백 함수
     */
    function deleteCollection(collectionId, onSuccess, onError) {
        if (!collectionId) {
            if (onError) onError('수집 ID가 제공되지 않았습니다.');
            return;
        }
        
        fetch(`/collections/${collectionId}`, {
            method: 'DELETE',
            headers: {
                'Content-Type': 'application/json',
            },
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (onSuccess) onSuccess(data.message);
            } else {
                if (onError) onError(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (onError) onError('수집 데이터 삭제 중 오류가 발생했습니다.');
        });
    }
    
    /**
     * 수집 시작
     * 
     * @param {Array} selectedServices - 선택된 서비스 목록
     * @param {function} onSuccess - 성공 시 콜백 함수
     * @param {function} onError - 오류 시 콜백 함수
     */
    function startCollection(selectedServices, onSuccess, onError) {
        if (!selectedServices || selectedServices.length === 0) {
            if (onError) onError('최소한 하나 이상의 서비스를 선택해야 합니다.');
            return;
        }
        
        fetch('/start_collection', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ selected_services: selectedServices })
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'success') {
                if (onSuccess) onSuccess(data.message);
            } else {
                if (onError) onError(data.message);
            }
        })
        .catch(error => {
            console.error('Error:', error);
            if (onError) onError('데이터 수집 요청 중 오류가 발생했습니다.');
        });
    }
    
    /**
     * 수집 상태 확인 시작
     * 
     * @param {function} onStatusUpdate - 상태 업데이트 시 콜백 함수
     * @param {function} onComplete - 완료 시 콜백 함수
     * @param {function} onError - 오류 시 콜백 함수
     * @param {number} interval - 확인 간격(ms), 기본값 1000ms
     */
    function startStatusCheck(onStatusUpdate, onComplete, onError, interval = 1000) {
        // 이전 인터벌 제거
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
        }
        
        // 상태 확인 함수
        function checkStatus() {
            fetch('/collection_status')
                .then(response => response.json())
                .then(data => {
                    if (data.is_collecting) {
                        // 수집 중인 경우
                        if (onStatusUpdate) onStatusUpdate(data);
                    } else {
                        // 수집이 완료된 경우
                        clearInterval(statusCheckInterval);
                        
                        if (data.error) {
                            // 오류가 있는 경우
                            if (onError) onError(data.error);
                        } else {
                            // 성공적으로 완료된 경우
                            if (onComplete) onComplete(data);
                        }
                    }
                })
                .catch(error => {
                    console.error('Error:', error);
                    if (onError) onError('상태 확인 중 오류가 발생했습니다.');
                });
        }
        
        // 즉시 한 번 확인
        checkStatus();
        
        // 인터벌 설정
        statusCheckInterval = setInterval(checkStatus, interval);
        
        // 인터벌 ID 반환
        return statusCheckInterval;
    }
    
    /**
     * 수집 상태 확인 중지
     */
    function stopStatusCheck() {
        if (statusCheckInterval) {
            clearInterval(statusCheckInterval);
            statusCheckInterval = null;
        }
    }
    
    // 공개 API
    return {
        deleteCollection,
        startCollection,
        startStatusCheck,
        stopStatusCheck
    };
})();