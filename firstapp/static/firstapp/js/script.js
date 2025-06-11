document.addEventListener('DOMContentLoaded', () => {
    const sidebar = document.getElementById('sidebar');
    const sidebarToggleBtn = document.getElementById('sidebarToggleBtn');

    const uploadSection = document.getElementById('uploadSection');
    const optionsSection = document.getElementById('optionsSection');
    const triggerImageUpload = document.getElementById('triggerImageUpload');
    const imageUploadInput = document.getElementById('imageUploadInput');
    const uploadedFileName = document.getElementById('uploadedFileName');

    // 이미지 첨부 버튼 (옵션 화면)은 options-left-panel에 있으므로 트리거 버튼 변경
    const triggerImageUploadAfter = document.getElementById('triggerImageUploadAfter');
    const imageUploadInputAfter = document.getElementById('imageUploadInputAfter');
    const uploadedFileNameAfter = document.getElementById('uploadedFileNameAfter');
    const imagePreviewAfter = document.getElementById('imagePreviewAfter');

    const addRequirementBtn = document.getElementById('addRequirementBtn');
    const additionalReqFields = document.getElementById('additionalReqFields');
    const generateImageBtn = document.getElementById('generateImageBtn');

    let uploadedImageFile = null; // 업로드된 이미지 파일 객체 저장

    // 사이드바 토글 기능
    sidebarToggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('active');
    });

    // 이미지 첨부 버튼 (초기 화면) 클릭 시 파일 입력 열기
    triggerImageUpload.addEventListener('click', () => {
        imageUploadInput.click();
    });

    // 이미지 첨부 버튼 (옵션 화면) 클릭 시 파일 입력 열기
    triggerImageUploadAfter.addEventListener('click', () => {
        imageUploadInputAfter.click();
    });

    // 파일 선택 시 처리 (초기 화면)
    imageUploadInput.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadedImageFile = file; // 파일 객체 저장
            uploadedFileName.textContent = file.name;

            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreviewAfter.style.backgroundImage = `url(${e.target.result})`;
                imagePreviewAfter.classList.add('has-image');
            };
            reader.readAsDataURL(file);

            // 이미지 첨부 후 화면으로 전환
            uploadSection.classList.remove('active');
            optionsSection.classList.add('active');
            // 옵션 화면의 파일 이름 업데이트
            uploadedFileNameAfter.textContent = file.name;

        } else {
            uploadedFileName.textContent = '';
            uploadedImageFile = null;
        }
    });

    // 파일 선택 시 처리 (옵션 화면) - 재업로드 시 동일하게 처리
    imageUploadInputAfter.addEventListener('change', (event) => {
        const file = event.target.files[0];
        if (file) {
            uploadedImageFile = file; // 파일 객체 업데이트
            uploadedFileNameAfter.textContent = file.name;

            const reader = new FileReader();
            reader.onload = (e) => {
                imagePreviewAfter.style.backgroundImage = `url(${e.target.result})`;
                imagePreviewAfter.classList.add('has-image');
            };
            reader.readAsDataURL(file);
        } else {
            uploadedFileNameAfter.textContent = uploadedImageFile ? uploadedImageFile.name : '';
        }
    });


    // 추가 요구사항 텍스트 필드 동적 생성
    addRequirementBtn.addEventListener('click', () => {
        const newFieldGroup = document.createElement('div');
        newFieldGroup.classList.add('req-field-group');

        const newInputField = document.createElement('input');
        newInputField.type = 'text';
        newInputField.placeholder = '추가 요구사항을 입력하세요';

        const deleteButton = document.createElement('button');
        deleteButton.classList.add('delete-req-btn');
        deleteButton.textContent = 'X';
        deleteButton.addEventListener('click', () => {
            newFieldGroup.remove(); // 해당 필드 그룹 삭제
        });

        newFieldGroup.appendChild(newInputField);
        newFieldGroup.appendChild(deleteButton);
        additionalReqFields.appendChild(newFieldGroup);
    });

    // 이미지 생성 버튼 클릭 시 정보 수집 및 전송 (가상)
    generateImageBtn.addEventListener('click', () => {
        if (!uploadedImageFile) {
            alert('이미지를 첨부해주세요.');
            return;
        }

        const formData = new FormData();
        formData.append('image', uploadedImageFile);

        const selectedTheme = document.querySelector('input[name="theme"]:checked');
        if (selectedTheme) {
            formData.append('theme', selectedTheme.value);
        } else {
            alert('테마를 선택해주세요.');
            return;
        }

        const selectedMood = document.querySelector('input[name="mood"]:checked');
        if (selectedMood) {
            formData.append('mood', selectedMood.value);
        } else {
            alert('분위기를 선택해주세요.');
            return;
        }

        const additionalRequirements = [];
        document.querySelectorAll('#additionalReqFields input[type="text"]').forEach(input => {
            if (input.value.trim() !== '') {
                additionalRequirements.push(input.value.trim());
            }
        });
        if (additionalRequirements.length > 0) {
            formData.append('additionalRequirements', JSON.stringify(additionalRequirements));
        }

        const selectedProductLocation = document.querySelector('input[name="productLocation"]:checked');
        if (selectedProductLocation) {
            formData.append('productLocation', selectedProductLocation.value);
        } else {
            alert('제품 위치를 선택해주세요.');
            return;
        }

        const imageSizeSelect = document.getElementById('imageSizeSelect');
        formData.append('imageSize', imageSizeSelect.value);

        console.log('--- 이미지 생성 요청 데이터 ---');
        for (let pair of formData.entries()) {
            console.log(pair[0] + ': ' + pair[1]);
        }
        alert('이미지 생성 요청이 콘솔에 출력되었습니다.');

        /*
        fetch('/api/generate-image', {
            method: 'POST',
            body: formData,
        })
        .then(response => response.json())
        .then(data => {
            console.log('이미지 생성 결과:', data);
        })
        .catch(error => {
            console.error('이미지 생성 오류:', error);
            alert('이미지 생성 중 오류가 발생했습니다.');
        });
        */
    });
});