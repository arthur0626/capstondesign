import os
import json
import replicate
from dotenv import load_dotenv

from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth import login, logout

from .forms import CustomUserCreationForm
from .models import GeneratedImage, UserProfile, Preset, User

load_dotenv()

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

def flatten_output(output):
    if isinstance(output, list):
        return ' '.join(str(item).strip() for item in output if item).replace("\n", " ").strip()
    elif isinstance(output, str):
        return output.replace("\n", " ").strip()
    return str(output).strip()

def generate_images(request):
    # -------------------------------------------------------
    # 1. GET 요청 처리 (페이지 처음 접속 시 HTML 렌더링)
    # -------------------------------------------------------
    if request.method == "GET":
        user_presets = []
        if request.user.is_authenticated:
            user_presets = Preset.objects.filter(user=request.user).order_by('-created_at')
        
        return render(request, "main.html", {
            "user_presets": user_presets,
        })

    # -------------------------------------------------------
    # 2. POST 요청 처리 (이미지 생성 및 JSON 반환)
    # -------------------------------------------------------
    if request.method == "POST":
        image_urls = []
        word_urls = []
        
        try:
            uploaded_file = request.FILES.get("image")

            generation_model = request.POST.get("model", "flux")
            # 안전하게 정수 변환
            try:
                generation_number = max(1, min(int(request.POST.get("count", "1")), 10))
            except ValueError:
                generation_number = 1

            # ... (변수 가져오기) ...
            generation_ratio = request.POST.get("aspect_ratio", "16:9")
            generation_style = request.POST.get("style", "")
            generation_mood = request.POST.get("mood", "")

            alcohol_type = request.POST.get("alcohol", "")
            alcohol_status = request.POST.get("alcohol_status", "")
            alcohol_position = request.POST.get("alcohol_position", "")

            glass_type = request.POST.get("glass_type", "")
            glass_status = request.POST.get("glass_status", "")
            glass_position = request.POST.get("glass_position", "")
            glass_garnish = request.POST.get("glass_garnish", "")

            human_clothing = request.POST.get("human_clothing", "")
            human_age = request.POST.get("human_age", "")
            human_type = request.POST.get("human_type", "")
            human_pose = request.POST.get("human_pose", "")
            human_expression = request.POST.get("human_expression", "")
            human_position = request.POST.get("human_position", "")

            background_type = request.POST.get("background_theme", "")
            background_details = request.POST.get("background_details", "")
            background_time = request.POST.get("background_time", "")

            lighting_type = request.POST.get("lighting_type", "")
            lighting_distance = request.POST.get("lighting_distance", "")
            lighting_color = request.POST.get("lighting_color", "")
            lighting_angle = request.POST.get("lighting_angle", "")

            shot_type = request.POST.get("shot_type", "")
            shot_distance = request.POST.get("shot_distance", "")
            shot_angle = request.POST.get("shot_angle", "")        

            base_positive_prompt = "professional product photography, commercial advertisement, hyperrealistic, 8k, UHD, highly detailed, condensation droplets on glass, cold and refreshing, cinematic lighting, rim lighting, sharp focus, depth of field, Hasselblad X1D, 85mm lens"
            
            base_negative_prompt = "text, watermark, logo, signature, copyright, low quality, worst quality, blurry, pixelated, distorted glass, deformed, ugly, cartoon, illustration, painting, drawing, anime"
            
            user_positive_prompt = request.POST.get("user_positive_prompt", "")
            user_negative_prompt = request.POST.get("user_negative_prompt", "")

            # 프롬프트 합성
            full_prompt = f"""
            Translate the following product marketing scene into natural and realistic English, without listing:
            "{generation_mood} 분위기의 {generation_style} 스타일 주류 마케팅 이미지 생성,
            술 종류는 {alcohol_type}, 상태는 {alcohol_status}, 위치는 {alcohol_position},
            잔 종류는 {glass_type}, 상태는 {glass_status}, 위치는 {glass_position}, 가니쉬는 {glass_garnish},
            사람은 {human_type}, 나이는 {human_age}, 복장은 {human_clothing}, 포즈는 {human_pose}, 표정은 {human_expression}, 위치는 {human_position},
            배경은 {background_type}, 디테일은 {background_details}, 시간대는 {background_time},
            조명은 {lighting_type}, 거리감은 {lighting_distance}, 조명 색상은 {lighting_color}, 조명 각도는 {lighting_angle},
            전체 구도는 {shot_type}, 거리감은 {shot_distance}, 각도는 {shot_angle},
            추가 프롬프트는 {base_positive_prompt}, {user_positive_prompt},
            제외 프롬프트는 {base_negative_prompt}, {user_negative_prompt}"
            """.strip()

            word_prompt = f"""
            위 상황을 기반으로, 술 마케팅에 어울리는 간결하고 창의적인 한국어 한 줄 문장을 추천해줘.
            상황: {full_prompt}
            """.strip()

            # 번역 실행
            translated_prompt = client.run(
                "openai/o4-mini",
                input={"prompt": full_prompt}
            )
            full_prompt_english = flatten_output(translated_prompt)

            if uploaded_file:
                file_path = default_storage.save(uploaded_file.name, uploaded_file)
                full_path = default_storage.path(file_path)

                with open(full_path, "rb") as f:
                    # 1. 이미지 생성
                    for _ in range(generation_number):
                        f.seek(0)  # 중요: 파일 포인터 초기화
                        
                        # 모델 실행
                        if generation_model == "flux":
                            output = client.run(
                                "black-forest-labs/flux-kontext-pro",
                                input={
                                    "prompt": full_prompt_english,
                                    "input_image": f,
                                    "aspect_ratio": generation_ratio,
                                }
                            )
                        else: # sdxl 등 다른 모델
                            # (예시 코드 - 필요 시 활성화)
                            output = client.run(
                                "black-forest-labs/flux-kontext-pro", # 임시로 flux 사용
                                input={
                                    "prompt": full_prompt_english,
                                    "input_image": f,
                                    "aspect_ratio": generation_ratio,
                                }
                            )

                        # URL 추출
                        generated_url = None
                        if isinstance(output, list) and output:
                            generated_url = output[0]
                        elif isinstance(output, str):
                            generated_url = output
                        elif output:
                            generated_url = str(output) # FileOutput 객체 처리

                        # 저장
                        if generated_url:
                            image_urls.append(generated_url)
                            if request.user.is_authenticated:
                                GeneratedImage.objects.create(
                                    user=request.user,
                                    image_url=generated_url,
                                    prompt=full_prompt_english
                                )

                    # 2. 추천 문구 생성
                    f.seek(0)
                    output = client.run(
                        "openai/o4-mini",
                        input={
                            "prompt": word_prompt,
                            "input_image": f,
                        }
                    )
                    word_urls.append(flatten_output(output))

            return JsonResponse({
                "status": "success",
                "image_urls": image_urls,
                "word_urls": word_urls,
            })

        except Exception as e:
            print(f"Error: {e}")
            return JsonResponse({
                "status": "error", 
                "image_urls": [],
                "word_urls": ["오류가 발생했습니다. 잠시 후 다시 시도해주세요."]
            })

    # GET도 POST도 아닌 경우 (혹시 모를 대비)
    return JsonResponse({"status": "error", "message": "Invalid method"})


# --- [나머지 뷰 함수들] ---

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('main')
    else:
        form = CustomUserCreationForm()
    return render(request, 'signup.html', {'form': form})

@login_required
def profile(request):
    user_profile = get_object_or_404(UserProfile, user=request.user)
    is_admin = user_profile.is_admin
    
    context = {'is_admin': is_admin}

    if is_admin:
        all_other_users = User.objects.exclude(id=request.user.id)
        context['all_users'] = all_other_users
    else:
        images = GeneratedImage.objects.filter(user=request.user).order_by('-created_at')
        context['images'] = images
        
    return render(request, 'profile.html', context)

@login_required
def view_user_profile(request, user_id):
    if not request.user.userprofile.is_admin:
        return redirect('main')

    target_user = get_object_or_404(User, id=user_id)
    images = GeneratedImage.objects.filter(user=target_user).order_by('-created_at')
    
    return render(request, 'view_user_profile.html', {
        'target_user': target_user,
        'images': images
    })

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)
        user.delete()
        return redirect('main')
    return render(request, 'delete_account.html')

# ---------------------------------------------------------
# 프리셋 관련 뷰 (필드명: settings로 통일)
# ---------------------------------------------------------

@require_POST
@login_required
def preset_save(request):
    try:
        data = json.loads(request.body)
        name = data.get('name')
        form_data = data.get('formData')

        Preset.objects.create(
            user=request.user,
            name=name,
            data=json.dumps(form_data) # data -> settings (필드명 확인 필요!)
        )
        return JsonResponse({'status': 'success', 'message': '프리셋이 저장되었습니다.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def preset_load(request, preset_id):
    try:
        preset = Preset.objects.get(id=preset_id, user=request.user)
        # data -> settings
        return JsonResponse({'status': 'success', 'data': json.loads(preset.data)})
    except Preset.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '프리셋을 찾을 수 없습니다.'})

@login_required
def preset_delete(request, preset_id):
    Preset.objects.filter(id=preset_id, user=request.user).delete()
    return redirect('main')