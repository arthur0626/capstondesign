/**
 * 1. DOM이 로드되면 setupMarquees 함수를 실행합니다.
 * 2. setupMarquees 함수는 'track1', 'track2'를 설정합니다.
 */
document.addEventListener('DOMContentLoaded', function() {
    
    // 콘솔에 이 메시지가 보이면 home.js 파일이 '실행'된 것입니다.
    console.log("home.js (v2)가 성공적으로 로드되었습니다.");

    /**
     * 개별 트랙을 설정하는 함수
     */
    function setupMarquee(trackId) {
        const track = document.getElementById(trackId);
        
        // 트랙을 찾지 못하면 오류를 출력하고 중단합니다.
        if (!track) {
            console.error(`오류: ID '${trackId}'를 가진 트랙을 찾을 수 없습니다.`);
            return;
        }

        const originalItems = Array.from(track.children);
        
        if (originalItems.length === 0) {
            console.warn(`경고: '${trackId}' 트랙에 원본 아이템이 없습니다.`);
            return;
        }

        console.log(`[${trackId}] 원본 아이템 ${originalItems.length}개 감지.`);

        // 1. 원본 아이템 세트의 총 너비 계산
        let originalWidth = 0;
        originalItems.forEach(item => {
            const style = window.getComputedStyle(item);
            originalWidth += item.offsetWidth + parseFloat(style.marginLeft) + parseFloat(style.marginRight);
        });

        // 2. 현재 브라우저 화면 너비 확인
        const viewportWidth = document.documentElement.clientWidth;

        // 3. 화면 너비를 채울 때까지 아이템 자동 복제
        let currentWidth = originalWidth;
        let clonesAdded = 0;

        // 최소 (화면 너비 * 2.5)를 채울 때까지, 
        // 또는 최소 10번 복제할 때까지 (안전장치)
        while (currentWidth < (viewportWidth * 2.5) || clonesAdded < 10) {
            originalItems.forEach(item => {
                const clone = item.cloneNode(true);
                track.appendChild(clone);
            });
            currentWidth += originalWidth;
            clonesAdded++;
            
            // 너무 많은 복제를 방지 (최대 30회)
            if (clonesAdded > 30) break;
        }
        
        console.log(`[${trackId}] 아이템을 ${clonesAdded}회 복제했습니다. 총 너비: ${currentWidth}px`);

        // 4. 동적 애니메이션 속도 설정
        // 애니메이션은 트랙 너비의 절반(-50%)만큼 이동합니다.
        const animationDistance = currentWidth / 2;
        const pixelsPerSecond = 60; // 1초에 60px 이동
        const duration = animationDistance / pixelsPerSecond;

        // CSS에 계산된 시간을 적용합니다.
        track.style.animationDuration = `${duration}s`;
        
        console.log(`[${trackId}] 애니메이션 시간 ${duration.toFixed(2)}초로 설정 완료.`);
    }

    // --- 실행 ---
    // 페이지의 모든 리소스(이미지 등)가 로드되어야
    // 너비 계산(offsetWidth)이 정확하므로 'load' 이벤트를 사용합니다.
    window.addEventListener('load', () => {
        console.log("페이지 'load' 이벤트 발생. 마퀴 설정을 시작합니다.");
        setupMarquee('track1');
        setupMarquee('track2');
    });

});