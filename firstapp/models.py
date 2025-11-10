from django.db import models
from django.contrib.auth.models import User  # 1. Django의 기본 User 모델을 가져옵니다.
from django.db.models.signals import post_save
from django.dispatch import receiver

# 2. 유저의 추가 정보(직위)를 관리할 UserProfile 모델
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # 요청하신 '관리자 여부' 필드를 UserProfile에 저장합니다.
    is_admin = models.BooleanField(default=False) 

    def __str__(self):
        return self.user.username

# 3. 생성된 이미지를 저장할 모델
class GeneratedImage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    image_url = models.URLField(max_length=500)
    prompt = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.user.username} - {self.id}'

# 4. User가 생성될 때 UserProfile도 자동으로 생성/저장하는 신호(Signal)
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.userprofile.save()