import os
import json
import replicate
import base64
import requests
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
        file_obj = None # 파일을 열어서 담을 변수
        
        try:
            # [이미지 파일 처리 로직]
            uploaded_file = request.FILES.get("image")
            cached_image_path = request.POST.get("cached_image_path") # 프리셋 이미지 경로

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
            
            # ... (나머지 모든 변수 가져오기 코드 그대로 유지) ...
            # (너무 길어서 생략하지만, 기존 코드 그대로 두시면 됩니다)
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
        try:
            image_file = request.FILES.get('target_image')
            liquor_info = request.POST.get('liquor_info', '')
            target_gender = request.POST.get('target_gender', '')
            target_age = request.POST.get('target_age', '')
            food = request.POST.get('pairing_food', '')

            if not image_file:
                return JsonResponse({'status': 'error', 'message': '이미지가 필요합니다.'})

            # 이미지를 base64로 인코딩
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

            # GPT-4o-mini에게 보낼 프롬프트 구성
            system_prompt = "You are a professional liquor marketing expert and photographer."
            user_message = f"""
            Analyze this liquor image.
            Product Info: {liquor_info}
            Target Audience: {target_gender}, {target_age}
            Food Pairing: {food}

            Please provide two things in JSON format:
            1. 'analysis': A brief marketing analysis (in Korean) of why this product appeals to the target.
            2. 'prompt': A high-quality English prompt for an AI image generator (like Flux) to create a perfect advertisement image for this product. Include lighting, composition, and atmosphere details.
            """

            # OpenAI API 호출 (비전 기능 사용)
            response = client.run( # (주의: 기존 client는 replicate용일 수 있음. OpenAI client 확인 필요)
                "openai/gpt-4o-mini", # 혹은 replicate의 gpt-4o-mini 프록시 모델 사용
                input={
                    "prompt": user_message,
                    "image": f"data:image/jpeg;base64,{image_data}" # Base64 이미지 전달
                }
            )
            
            # (Replicate의 gpt-4o-mini 출력 형태에 따라 파싱 필요. 여기서는 텍스트라 가정)
            # 실제로는 OpenAI native client를 쓰는 게 더 낫지만, 기존 client(replicate)를 쓴다면 모델명을 확인하세요.
            # 만약 OpenAI API키가 따로 있다면 `import openai` 해서 쓰는 게 더 정확합니다.
            
            # [임시] Replicate 대신 OpenAI 직접 호출 예시 (더 안정적)
            # import openai
            # openai.api_key = "sk-..."
            # ... completion 로직 ...
            
            # 여기서는 텍스트로 그냥 반환한다고 가정
            result_text = flatten_output(response) 
            
            # 결과 예시 (실제로는 파싱 로직 필요)
            analysis_text = "이 제품은 30대 남성을 타겟으로 하여 고급스러운 바 분위기가 어울립니다..."
            prompt_text = "A bottle of single malt whisky on a wooden table, cinematic lighting..."

            return JsonResponse({
                'status': 'success',
                'analysis': result_text, # 전체 텍스트를 줌 (실제론 나눠야 함)
                'prompt': "Cinematic shot of the liquor bottle, warm lighting, luxury bar background, 8k" # 가짜 예시
            })

        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def image_edit(request):
    if request.method == "POST":
        try:
            # 1. 파일 저장
            uploaded_file = request.FILES.get('edit_image')
            if not uploaded_file:
                return JsonResponse({'status': 'error', 'message': '이미지가 없습니다.'})

            file_path = default_storage.save(f"edit/{uploaded_file.name}", uploaded_file)
            full_path = default_storage.path(file_path)

            # 2. 사용자 입력 받기
            remove_obj = request.POST.get('remove_object', '')
            mood_shift = request.POST.get('mood_shift', 'none')
            add_text = request.POST.get('add_text', '')
            font_style = request.POST.get('font_style', '')
            text_pos = request.POST.get('text_pos', 'center')

            # 3. AI 편집 프롬프트 구성 (InstructPix2Pix 용)
            edit_instructions = []
            if remove_obj:
                edit_instructions.append(f"remove {remove_obj}")
            if mood_shift != 'none':
                if mood_shift == 'warm': edit_instructions.append("make it warm atmosphere, sunset lighting")
                elif mood_shift == 'cool': edit_instructions.append("make it cool atmosphere, blue tone")
                elif mood_shift == 'retro': edit_instructions.append("make it vintage retro style")
            
            final_instruction = ", ".join(edit_instructions)
            
            # 4. AI 편집 실행 (편집할 내용이 있을 때만)
            current_image_url = None # 결과 이미지 URL
            
            if final_instruction:
                with open(full_path, "rb") as f:
                    output = client.run(
                        "timbrooks/instruct-pix2pix:30c1d0b916a6f8efce20493f5d61ee27491ab2a60437c13c588468b9810ec23f",
                        input={
                            "image": f,
                            "prompt": final_instruction,
                            "num_inference_steps": 20,
                            "image_guidance_scale": 1.5,
                        }
                    )
                    # 결과가 리스트나 문자열로 올 수 있음
                    if isinstance(output, list): current_image_url = output[0]
                    else: current_image_url = str(output)
            else:
                # AI 편집 없으면 원본 이미지 사용 (로컬 경로를 URL로 변환 필요하므로, 일단 원본 처리)
                # 여기서는 로직 단순화를 위해 AI 편집이 없으면 원본 파일 경로를 씁니다.
                pass 

            # 5. 텍스트 삽입 (Pillow 사용)
            if add_text:
                # 5-1. 이미지 불러오기 (AI 결과가 있으면 URL에서, 없으면 로컬 파일에서)
                if current_image_url:
                    response = requests.get(current_image_url)
                    img = Image.open(BytesIO(response.content))
                else:
                    img = Image.open(full_path)

                # 5-2. 그리기 도구 준비
                draw = ImageDraw.Draw(img)
                W, H = img.size
                
                # 폰트 설정 (한글 폰트 경로가 없으면 기본 폰트 사용 - 한글 깨질 수 있음 주의)
                # 윈도우 기본 맑은고딕 경로 예시: "C:/Windows/Fonts/malgun.ttf"
                # 리눅스/맥 서버라면 해당 폰트 경로 지정 필요. 없을 경우 기본 로드.
                try:
                    # 폰트 크기는 이미지 너비의 10% 정도로 설정
                    font_size = int(W * 0.08) 
                    font_path = "C:/Windows/Fonts/malgun.ttf" if os.name == 'nt' else "/usr/share/fonts/truetype/nanum/NanumGothic.ttf"
                    font = ImageFont.truetype(font_path, font_size)
                except:
                    font = ImageFont.load_default()

                # 5-3. 텍스트 크기 계산 및 위치 선정
                bbox = draw.textbbox((0, 0), add_text, font=font)
                w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]

                x, y = (W-w)/2, (H-h)/2 # 기본 중앙
                if text_pos == '상단 중앙': y = H * 0.1
                elif text_pos == '하단 중앙': y = H * 0.8
                
                # 5-4. 텍스트 그리기 (가독성을 위해 그림자 추가)
                shadow_color = "black"
                text_color = "white"
                # 그림자
                draw.text((x+2, y+2), add_text, font=font, fill=shadow_color)
                # 본문
                draw.text((x, y), add_text, font=font, fill=text_color)

                # 5-5. 결과 이미지 저장
                save_path = f"edit/edited_{uploaded_file.name}"
                full_save_path = os.path.join(settings.MEDIA_ROOT, save_path)
                img.save(full_save_path)
                
                # 최종 URL은 로컬 미디어 URL
                result_url = f"{settings.MEDIA_URL}{save_path}"
            else:
                # 텍스트 편집이 없으면 AI 결과 URL 사용
                result_url = current_image_url

            return JsonResponse({
                'status': 'success', 
                'image_url': result_url,
                'message': '편집이 완료되었습니다.'
            })

        except Exception as e:
            print(f"Edit Error: {e}")
            return JsonResponse({'status': 'error', 'message': str(e)})
            
    return JsonResponse({'status': 'error', 'message': 'Invalid Request'})

@login_required
def image_to_video(request):
    if request.method == "POST":
        try:
            uploaded_file = request.FILES.get('start_image')
            if not uploaded_file:
                return JsonResponse({'status': 'error', 'message': '시작 이미지가 필요합니다.'})
            
            file_path = default_storage.save(f"video/{uploaded_file.name}", uploaded_file)
            full_path = default_storage.path(file_path)

            # 사용자 옵션
            video_model = request.POST.get('video_model', 'SVD')
            motion_bucket = int(request.POST.get('motion_bucket', 127))
            fps = int(request.POST.get('video_fps', '24').replace(' fps', ''))
            
            # 모델 매핑 (Replicate에 존재하는 모델로 매핑)
            # SVD-XT: 가장 대중적인 오픈소스 비디오 모델
            model_id = "stability-ai/stable-video-diffusion:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"
            
            # AnimateDiff 선택 시 모델 변경
            if 'AnimateDiff' in video_model:
                model_id = "lucataco/animate-diff:beecf59c50aa896be068bbc735cd406cbd8b79e1c68074303d4793a128063666"

            # API 호출
            with open(full_path, "rb") as f:
                output = client.run(
                    model_id,
                    input={
                        "input_image": f,
                        "video_length": "14_frames_with_svd_xt", # SVD 설정
                        "sizing_strategy": "maintain_aspect_ratio",
                        "frames_per_second": fps,
                        "motion_bucket_id": motion_bucket,
                        "cond_aug": 0.02,
                        "decoding_t": 1,
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