import os
import json
import replicate
import base64
import requests
import re
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from dotenv import load_dotenv

from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth import login, logout
from django.core.files import File

from django.conf import settings
from .forms import CustomUserCreationForm
from .models import GeneratedImage, UserProfile, Preset, User

load_dotenv()

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

import re # <-- 이 import는 views.py 상단에 있어야 합니다.

def flatten_output(output):
    if not output:
        return ""
        
    # 1. 토큰들을 하나의 문자열로 합침 (list -> str)
    if isinstance(output, list):
        raw_text = ''.join(str(item) for item in output if item)
    else:
        raw_text = str(output)

    # 7. 최종 출력 시, 텍스트가 시작/끝 부분에서 붙지 않도록 공백 추가
    return raw_text.strip()

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
        file_obj = None # 파일을 열어서 담을 변수
        
        try:
            # [이미지 파일 처리 로직]
            uploaded_file = request.FILES.get("image")
            cached_image_path = request.POST.get("cached_image_path") # 프리셋 이미지 경로

            print(f"Uploaded file: {uploaded_file}")
            print("Cached image path:", cached_image_path)
            print("Request files:", request.FILES)

            if uploaded_file:
                # 1. 새로 업로드한 파일이 있으면 저장하고 엽니다.
                file_path = default_storage.save(uploaded_file.name, uploaded_file)
                full_path = default_storage.path(file_path)
                file_obj = open(full_path, "rb")
            
            elif cached_image_path:
                # 2. 업로드 파일은 없지만, 프리셋 이미지가 있다면 그걸 엽니다.
                # (주의: cached_image_path는 'presets/이미지.jpg' 같은 상대 경로여야 함)
                # MEDIA_ROOT와 결합하여 절대 경로 생성
                full_path = os.path.join(settings.MEDIA_ROOT, cached_image_path)
                if os.path.exists(full_path):
                    file_obj = open(full_path, "rb")
            
            # 파일이 없으면 에러 처리
            if not file_obj:
                return JsonResponse({"status": "error", "message": "이미지를 선택하거나 프리셋을 불러와주세요."})

            # [변수 가져오기]
            generation_model = request.POST.get("model", "flux")
            try:
                generation_number = max(1, min(int(request.POST.get("count", "1")), 10))
            except ValueError:
                generation_number = 1

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
            user_positive_prompt = request.POST.get("user_positive_prompt", "")
            user_negative_prompt = request.POST.get("user_negative_prompt", "")

            base_positive_prompt = "professional product photography, commercial advertisement, hyperrealistic, 8k, UHD, highly detailed, condensation droplets on glass, cold and refreshing, cinematic lighting, rim lighting, sharp focus, depth of field, Hasselblad X1D, 85mm lens"
            base_negative_prompt = "text, watermark, logo, signature, copyright, low quality, worst quality, blurry, pixelated, distorted glass, deformed, ugly, cartoon, illustration, painting, drawing, anime"
            
            # [프롬프트 합성]
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

            # [번역 실행]
            translated_prompt = client.run(
                "openai/o4-mini",
                input={"prompt": full_prompt}
            )
            full_prompt_english = flatten_output(translated_prompt)


            # [이미지 생성 루프]
            # file_obj(업로드 파일 또는 프리셋 파일)를 사용합니다.
            for _ in range(generation_number):
                file_obj.seek(0)  # 파일 포인터 초기화 (중요!)

                print("file_obj:", file_obj)
                
                if generation_model == "flux":
                    output = client.run(
                        "black-forest-labs/flux-kontext-pro",
                        input={
                            "prompt": full_prompt_english,
                            "input_image": file_obj, # f 대신 file_obj 사용
                            "aspect_ratio": generation_ratio,
                        }
                    )
                elif generation_model == "custom_beach":
                    output = replicate.run(
                        "clipnpaper/alcohol_beach:5c3ef136e48fd434e8fa47c9deaad6d12527a61757305ca01169e58fc5b19ef5",
                        input={
                            "model": "dev",
                            "prompt": full_prompt_english  + " alcohol_beach background,\n Place the referenced beer mask image on the table",
                            "mask" : file_obj,
                            "aspect_ratio": generation_ratio,
                        }
                    )
                elif generation_model == "custom_bar":
                    output = replicate.run(
                        "clipnpaper/alcohol_cozy_bar:8f3dff77476698778b50f4d7a1112e10f03496d0f19ce38c583ab16cecec6fba",
                        input={
                            "model": "dev",
                            "prompt": full_prompt_english + " cozy_bar background \nPlace the referenced beer mask image on the table",
                            "mask" : file_obj,
                            "aspect_ratio": generation_ratio,
                        }
                    )
                else: # sdxl 등
                     output = client.run(
                        "black-forest-labs/flux-kontext-pro", # 임시
                        input={
                            "prompt": full_prompt_english,
                            "input_image": file_obj,
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
                    generated_url = str(output)

                if generated_url:
                    image_urls.append(generated_url)
                    if request.user.is_authenticated:
                        GeneratedImage.objects.create(
                            user=request.user,
                            image_url=generated_url,
                            prompt=full_prompt_english
                        )

            # [추천 문구 생성]
            file_obj.seek(0)
            output = client.run(
                "openai/o4-mini",
                input={
                    "prompt": word_prompt,
                    "input_image": file_obj,
                }
            )
            word_urls.append(flatten_output(output))
            
            # 파일을 열었으니 닫아줍니다 (try-finally 블록이 더 좋지만 간단하게 여기서 처리)
            file_obj.close()

            return JsonResponse({
                "status": "success",
                "image_urls": image_urls,
                "word_urls": word_urls,
            })

        except Exception as e:
            print(f"Error: {e}")
            if file_obj: file_obj.close() # 에러 발생 시에도 파일 닫기
            return JsonResponse({
                "status": "error", 
                "image_urls": [],
                "word_urls": ["오류가 발생했습니다: " + str(e)]
            })

    return JsonResponse({"status": "error", "message": "Invalid method"})


# --- [나머지 뷰 함수들] ---

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)

        if form.is_valid():
            admin_key = form.cleaned_data.get('admin_key')
            is_admin = form.cleaned_data.get('is_admin')

            if is_admin and admin_key != settings.ADMIN_CREATION_KEY:
                form.add_error('admin_key', '관리자 생성 키가 올바르지 않습니다.')
                return render(request, 'signup.html', {'form': form})
            
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

@require_POST
@login_required
def preset_save(request):
    try:
        name = request.POST.get('name')
        data = request.POST.get('data')

        image_file = request.FILES.get('image')

        cached_path = request.POST.get('cached_image_path')

        new_preset = Preset(
            user=request.user,
            name=name,
            data=data,
        )

        if image_file:
            new_preset.image = image_file
        elif cached_path:
            full_path = os.path.join(settings.MEDIA_ROOT, cached_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    new_preset.image.save(os.path.basename(full_path), File(f), save=False)
        new_preset.save()

        return JsonResponse({
            'status': 'success', 
            'message': '프리셋이 저장되었습니다.',
            'preset_id': new_preset.id,
            'preset_name': new_preset.name
        })
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def preset_load(request, preset_id):
    try:
        preset = Preset.objects.get(id=preset_id, user=request.user)

        response = {
            'status': 'success',
            'data': json.loads(preset.data),
            'image_url': preset.image.url if preset.image else None,
            'image_path': preset.image.path if preset.image else None,
        }
        return JsonResponse(response)
    except Preset.DoesNotExist:
        return JsonResponse({'status': 'error', 'message': '프리셋을 찾을 수 없습니다.'})

@login_required
def preset_delete(request, preset_id):
    try:
        preset = get_object_or_404(Preset, id=preset_id, user=request.user)
        if preset.image:
            preset.image.delete(save=False)
        preset.delete()

        return JsonResponse({'status': 'success', 'message': '삭제되었습니다.'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required
def image_analyze(request):
    if request.method == "POST":
        file_obj = None

        try:
            uploaded_file = request.FILES.get('target_image')

            if not uploaded_file:
                 return JsonResponse({'status': 'error', 'message': '이미지가 유효하지 않습니다.'})
            
            file_path = default_storage.save(uploaded_file.name, uploaded_file)
            full_path = default_storage.path(file_path)
            file_obj = open(full_path, "rb")


            # 주류 세부 정보
            liquor_type = request.POST.get('liquor_type', '')
            main_ingredient = request.POST.get('main_ingredient', '')
            liquor_taste = request.POST.get('liquor_taste', '')
            liquor_aroma = request.POST.get('liquor_aroma', '')
            liquor_texture = request.POST.get('liquor_texture', '')
            pairing_food = request.POST.get('pairing_food', '')

            # 마케팅 및 타겟 정보
            target_age = request.POST.get('target_age', '')
            target_gender = request.POST.get('target_gender', '')
            target_job = request.POST.get('target_job', '')
            brand_value = request.POST.get('brand_value', '')
            preferred_style = request.POST.get('preferred_style', '')

            # 모델 정보
            model = request.POST.get('model', 'openai/gpt-5')
            reasoning_effort = request.POST.get('reasoning_effort', 'minimal')
            verbosity = request.POST.get('verbosity', 'medium')

            # 2. [PROMPT] GPT-4o-mini에게 보낼 프롬프트 구성 (JSON 반환 강제)
            system_prompt = "You are a professional liquor marketing expert and photographer. Your task is to analyze the provided image and generate a complete marketing brief and AI image generation prompts"
            user_message = f"""
            Analyze the image of the liquor bottle/drink based on the following context and generate an advertisement concept.
            
            CONTEXT:
            - 주류 타입/재료: {liquor_type} ({main_ingredient})
            - 맛/향/질감: {liquor_taste} / {liquor_aroma} / {liquor_texture}
            - 핵심 브랜드 가치: {brand_value}
            - 타겟: {target_gender} {target_age} ({target_job})
            - 페어링 음식: {pairing_food}
            - 선호 스타일: {preferred_style}

            Based on the analysis, make an output. The output must be in korean except for the positive and negative prompts, and do not include '"' marks, '*' marks, '#' marks.
            ●주류의 이미지:
            ●추천 색상:
            ●추천 폰트: 
            ●추천 모델: 
            ●추천 포즈: 
            ●추천 배경: 
            ●추천 조명: 
            ●추천 구도: 
            ●핵심 아이디어: 
            ●긍정 프롬프트: A comprehensive positive AI prompt (including lighting, camera, and style) to generate a perfect advertisement image.
            ●부정 프롬프트: A list of crucial negative keywords (e.g., text, blurry, watermark).
            ●추천 광고 문구: A list of 10 creative advertising slogans/taglines (vaired by length of sentence).
            """

            # 3. API 호출 (Replicate client 사용)
            response = client.run( 
                "openai/gpt-5",
                input={"prompt": user_message, 
                       "image_input": [file_obj], 
                       "system_prompt": system_prompt,
                       "reasoning_effort": reasoning_effort,
                        "verbosity": verbosity}
            )
            
            raw_text = flatten_output(response)
            parts = raw_text.split('●')
            analysis_image = parts[1].strip()
            analysis_color = parts[2].strip()
            analysis_font = parts[3].strip()
            analysis_model = parts[4].strip()
            analysis_pose = parts[5].strip()
            analysis_background = parts[6].strip()
            analysis_lighting = parts[7].strip()
            analysis_composition = parts[8].strip()
            analysis_idea = parts[9].strip()
            analysis_positive = parts[10].strip()
            analysis_negative = parts[11].strip()
            analysis_slogans = parts[12].strip()

            return JsonResponse({
                'status': 'success',
                'analysis_image': analysis_image,
                'analysis_color': analysis_color,
                'analysis_font': analysis_font,
                'analysis_model': analysis_model,
                'analysis_pose': analysis_pose,
                'analysis_background': analysis_background,
                'analysis_lighting': analysis_lighting,
                'analysis_composition': analysis_composition,
                'analysis_idea': analysis_idea,
                'analysis_positive': analysis_positive,
                'analysis_negative': analysis_negative,
                'analysis_slogans': analysis_slogans,
            })

        except json.JSONDecodeError:
             return JsonResponse({'status': 'error', 'message': 'AI가 반환한 JSON 구조에 오류가 있습니다. 다시 분석을 시도해 보세요.'})
        except Exception as e:
            # 이 외의 모든 오류 (API 통신, 파일 읽기 등)
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid method'})

@login_required
def image_edit(request):
    if request.method == "POST":
        file_obj = None
        full_path = None

        try:
            # 1. 파일 저장
            uploaded_file = request.FILES.get('edit_image')

            if not uploaded_file:
                 return JsonResponse({'status': 'error', 'message': '이미지가 유효하지 않습니다.'})
            
            file_path = default_storage.save(uploaded_file.name, uploaded_file)
            full_path = default_storage.path(file_path)
            file_obj = open(full_path, "rb")

            print ("file_obj:", file_obj)

            # 2. 사용자 입력 받기
            edit_positive_prompt = request.POST.get('edit_positive_prompt', '')
            
            output = client.run(
                "bytedance/seedream-4",
                    input={
                        "image_input": [file_obj],
                        "prompt": edit_positive_prompt,
                    }
                )

            image_url = None
            if isinstance(output, list): image_url = output[0]
            elif isinstance(output, str): image_url = output
            else: image_url = str(output)
                
            
            if not image_url:
                raise ValueError("API가 유효한 URL을 반환하지 않았습니다.")
            

            image_url = str(image_url).strip()
            print ("!!!!!!!!!!!!!!!!!!!!!!!!!!image_url:", image_url)

            # 3. JsonResponse에는 추출된 문자열만 담아 보냅니다.
            return JsonResponse({
                'status': 'success', 
                "image_url": image_url, # 👈 이제 순수한 문자열(str)만 담깁니다.
                'message': '편집이 완료되었습니다.'
            })

        except Exception as e:
            print(f"Edit Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
        
        finally:
            # 6. [핵심] 파일을 열었으면 오류 유무와 관계없이 반드시 닫고 삭제
            if file_obj:
                file_obj.close()
            if full_path and os.path.exists(full_path):
                # 임시 저장된 파일 삭제
                default_storage.delete(file_path)
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})

@login_required
def image_to_video(request):
    if request.method == "POST":
        file_obj = None

        try:
            uploaded_file = request.FILES.get('video_image')

            if not uploaded_file:
                 return JsonResponse({'status': 'error', 'message': '시작 이미지가 유효하지 않습니다.'})
            
            file_path = default_storage.save(uploaded_file.name, uploaded_file)
            full_path = default_storage.path(file_path)
            file_obj = open(full_path, "rb")

            if uploaded_file:
                # 파일을 MEDIA_ROOT에 저장
                file_path = default_storage.save(uploaded_file.name, uploaded_file)
                # 저장된 파일 경로를 기반으로 웹 접근 가능한 절대 URL 생성 (API에 전달할 형식)
                public_file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)
            
            print ("public_file_url:", public_file_url)

            # 사용자 옵션
            video_model = request.POST.get('video_model', 'google/veo-3.1')
            video_positive_prompt = request.POST.get('video_positive_prompt', '')
            video_ratio = request.POST.get('video_ratio', '16:9')
            video_duration = int(request.POST.get('video_duration', '4'))
            video_resolution = request.POST.get('video_resolution', '720p')
            video_generate_audio = bool(request.POST.get('video_generate_audio', 'False'))
            
            output = client.run(
                        video_model,
                        input={
                            "prompt": video_positive_prompt,
                            "image": file_obj,
                            "aspect_ratio": video_ratio,
                            "duration": video_duration,
                            "generate_audio": video_generate_audio,
                            "resolution": video_resolution,
                        }
            )
            
            # 비디오 URL 추출
            video_url = None
            if isinstance(output, list): video_url = output[0]
            elif isinstance(output, str): video_url = output
            else: video_url = str(output)

            return JsonResponse({
                'status': 'success',
                'video_url': video_url
            })

        except Exception as e:
            print(f"Video Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})

    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})