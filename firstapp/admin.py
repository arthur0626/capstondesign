from django.contrib import admin
from .models import Preset, GeneratedImage

# 프리셋 모델 등록
@admin.register(Preset)
class PresetAdmin(admin.ModelAdmin):
    list_display = ('name', 'user', 'created_at') # 목록에 보일 항목

# (이미지 모델도 등록해두면 좋습니다)
admin.site.register(GeneratedImage)