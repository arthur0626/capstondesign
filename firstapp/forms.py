from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import User # UserProfile 모델이 정의되어 있다고 가정

class CustomUserCreationForm(UserCreationForm):
    """
    Django 기본 회원가입 폼(아이디, 비번1, 비번2)에
    '관리자 여부' 필드만 추가한 커스텀 폼
    """
    
    # 1. '관리자 여부' 체크박스 필드 추가
    # required=False: 체크하지 않아도(일반 회원) 가입이 가능하도록 설정
    is_admin = forms.BooleanField(label='관리자(Admin) 계정으로 생성', required=False)

    class Meta(UserCreationForm.Meta):
        model = User
        # UserCreationForm이 아이디(username)와 
        # 비밀번호(password), 비밀번호 확인(password2) 필드는 
        # 자동으로 처리해줍니다.
        fields = ('username',) # 기본 필드인 아이디만 명시

    def save(self, commit=True):
        # 1. 기본 User 모델 저장 (아이디, 암호화된 비밀번호)
        user = super().save(commit=True) # User는 여기서 바로 저장

        # 2. UserProfile 모델에 '관리자 여부' 저장
        if commit:
            # (models.py의 post_save 시그널이 UserProfile을 자동 생성한다고 가정)
            # 폼에서 입력받은 is_admin 값을 userprofile에 저장
            user.userprofile.is_admin = self.cleaned_data['is_admin']
            user.userprofile.save()
            
        return user