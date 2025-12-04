import os
import replicate
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from dotenv import load_dotenv
from .models import GeneratedImage, UserProfile, Preset
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.contrib.auth.models import User
from django.conf import settings

def home_view(request):
    context = {}
    return render(request, "home.html")
    
def login_view(request):
    context = {}
    return render(request, "login.html")

def delete_account_view(request):
    context = {}
    return render(request, "delete_account.html")

def view_user_profile_view(request):
    context = {}
    return render(request, "view_user_profile.html")

# 2. 이미지 분석 페이지 (로그인 필수)
@login_required(login_url='login') 
def analysis_view(request):
    return render(request, "analysis.html")

# 3. 이미지 편집 페이지 (로그인 필수)
@login_required(login_url='login')
def editing_view(request):
    return render(request, "editing.html")

# 4. 영상 생성 페이지 (로그인 필수)
@login_required(login_url='login')
def video_view(request):
    return render(request, "video.html")

@login_required # 로그인을 해야만 접근 가능
def profile(request):
    # .get() 대신 get_object_or_404를 쓰면 유저 프로필이 없을 때 404 에러를 냅니다.
    user_profile = get_object_or_404(UserProfile, user=request.user)
    is_admin = user_profile.is_admin
    
    context = {
        'is_admin': is_admin,
    }

    if is_admin:
        # 관리자일 경우: '자신'을 제외한 모든 유저 목록을 context에 추가
        all_other_users = User.objects.exclude(id=request.user.id)
        context['all_users'] = all_other_users
    else:
        # 일반 회원일 경우: '자신'의 이미지 목록을 context에 추가
        images = GeneratedImage.objects.filter(user=request.user).order_by('-created_at')
        context['images'] = images
        
    # is_admin 값에 따라 'profile.html'이 다르게 렌더링됩니다.
    return render(request, 'profile.html', context)

@login_required
def view_user_profile(request, user_id):
    # 1) 요청한 유저가 관리자인지 확인
    if not request.user.userprofile.is_admin:
        # 관리자가 아니면 메인 페이지로 리다이렉트
        return redirect('main')

    # 2) 관리자가 보려는 '대상' 유저를 찾음
    target_user = get_object_or_404(User, id=user_id)
    
    # 3) 대상 유저가 생성한 이미지 목록을 가져옴
    images = GeneratedImage.objects.filter(user=target_user).order_by('-created_at')
    
    context = {
        'target_user': target_user,
        'images': images
    }
    
    # 이 뷰를 위한 새 템플릿을 렌더링합니다.
    return render(request, 'view_user_profile.html', context)

@login_required
def delete_account(request):
    if request.method == 'POST':
        user = request.user
        logout(request)  # 먼저 로그아웃 세션을 정리
        user.delete()    # 유저 정보를 DB에서 삭제
        return redirect('main') # 메인 페이지로 이동
    
    # GET 요청일 경우 (링크를 클릭해서 처음 접속한 경우)
    return render(request, 'delete_account.html')

load_dotenv()

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

def flatten_output(output):
    if isinstance(output, list):
        return ' '.join(str(item).strip() for item in output if item).replace("\n", " ").strip()
    elif isinstance(output, str):
        return output.replace("\n", " ").strip()
    return str(output).strip()

def flatten_output2(o):
    if isinstance(o, list):
        return ''.join(s for s in o if s).strip()
    return (o or '').strip()

def get_output_url(output):
    """Replicate 결과를 안전하게 문자열 URL로 변환"""
    if not output: return None
    if isinstance(output, list) and output: return str(output[0])
    return str(output)

def generate_images(request):
    image_urls = []
    word_urls = []

    if request.method != "POST":
        context = {
            "settings": {
                "product_type": request.GET.get("product_type", "소주"),
                "theme": request.GET.get("theme", "해변"),
                "mood": request.GET.get("mood", "따듯한"),
                "placement": request.GET.get("placement", "테이블 위에 놓인"),
                "prompt": request.GET.get("prompt", ""),
                "extra_requirements": request.GET.get("extra_requirements", ""),
                "model": request.GET.get("model", "flux"),
                "aspect_ratio": request.GET.get("aspect_ratio", "16:9"),
                "count": request.GET.get("count", "1"),
            }
        }
        return render(request, "main.html")
    
    if request.method == "POST":
        # GET POST VALUES
        product_type = request.POST.get("product_type", "맥주")
        theme = request.POST.get("theme", "식당")
        mood = request.POST.get("mood", "신나는")
        placement = request.POST.get("placement", "테이블 위에 놓인")
        user_prompt = request.POST.get("prompt", "")
        aspect_ratio = request.POST.get("aspect_ratio", "16:9")
        image_number = request.POST.get("count", "1")
        uploaded_file = request.FILES.get("image")
        model_choice = request.POST.get("model", "flux").lower()

        # 안전하게 정수 변환
        try:
            image_number = max(1, min(int(image_number), 10))  # 1~10 범위 제한
        except ValueError:
            image_number = 1  # 기본값

        original_settings = {
        'product_type': product_type,
        'theme': theme,
        'mood': mood,
        'placement': placement,
        'prompt': user_prompt,
        'extra_requirements': user_prompt,
        'model': model_choice,
        'aspect_ratio': aspect_ratio,
        'count': image_number,
        }

        # 프롬프트 합성
        full_prompt_ = f"""
        Translate the following product marketing scene into natural and realistic English, without listing:
        "입력된 이미지에 있는 바로 그 {product_type} 제품의 외형(라벨 디자인, 병 모양, 색상 등)을 완벽하게 유지한 채, 다음 상황에 자연스럽게 배치된 고품질 광고 사진을 만드세요: {mood} 분위기의 {theme} 배경에서, 해당 {product_type}이(가) {placement}에 놓여 있습니다. {user_prompt}"
        """.strip()
        
        word_prompt = f"""
        너의 역할은 카피라이터야.
        상황을 기반으로, 술 마케팅에 어울리는 간결하고 감각적인 한국어 광고 문구 3가지를 추천해줘.
        상황: {mood} 분위기의 {theme} 배경에서, 해당 {product_type}이(가) {placement}에 놓여 있습니다. {user_prompt}
        제약 : 서론 없이 문구 3개만 줄바꿈으로 출력.
        """.strip()

        translated_prompt = client.run(
            "openai/o4-mini",
            input={
                "prompt": full_prompt_,
            }
        )

        full_prompt = flatten_output2(translated_prompt)

        if uploaded_file:
            file_path = default_storage.save(uploaded_file.name, uploaded_file)
            full_path = default_storage.path(file_path)

            with open(full_path, "rb") as f:
                # 1. 이미지 생성
                f.seek(0)
                output = None
                for _ in range(image_number):
                    if model_choice == "flux":
                        output = client.run(
                            "black-forest-labs/flux-kontext-pro",
                            input={
                                "prompt": full_prompt,
                                "input_image": f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                    elif model_choice == "custom_beach":
                        output0 = replicate.run(
                            "clipnpaper/alcohol_beach:5c3ef136e48fd434e8fa47c9deaad6d12527a61757305ca01169e58fc5b19ef5",
                            input={
                                "model": "dev",
                                "input_image": f,
                                "prompt": ",alcohol_beach background" +full_prompt+ ",Do not create alcohol products",
                                "mask" : f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                        if isinstance(output0, list):
                            bg_url = str(output0[0])
                        else:
                            bg_url = str(output0)
                        f.seek(0)
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "image_input": [f, bg_url],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        if isinstance(output1, list) and len(output1) > 0:
                            output = output1[0]  # 리스트면 첫 번째 요소
                        else:
                            output = output1
                    elif model_choice == "custom_bar":
                        output0 = replicate.run(
                            "clipnpaper/alcohol_cozy_bar:8f3dff77476698778b50f4d7a1112e10f03496d0f19ce38c583ab16cecec6fba",
                            input={
                                "model": "dev",
                                #"input_image": f,
                                "prompt": ",cozy_bar background" +full_prompt+ "\n keep the provided bottle exactly as it is, "
                                                            "do not alter the bottle. Do not alter, redraw, re-create, re-interpret,"
                                                            " or modify the bottle, label, logo, text, shape, typography, or any branding elements in any way.",
                                "mask" : f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                        if isinstance(output0, list):
                            bg_url = str(output0[0])
                        else:
                            bg_url = str(output0)
                        f.seek(0)
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "image_input": [f, bg_url],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        if isinstance(output1, list) and len(output1) > 0:
                            output = output1[0]  # 리스트면 첫 번째 요소
                        else:
                            output = output1

                    elif model_choice == "custom_stylish":
                        output0 = replicate.run(
                            "clipnpaper/alcohol_stylish:b320a707aabb4390f663d2e834c30b072b3b1ad0d294182b1c4eec329818074f",
                            input={
                                "model": "dev",
                                #"input_image": f,
                                "prompt": "stylish background" +full_prompt+ "\n keep the provided bottle exactly as it is, "
                                                            "do not alter the bottle. Do not alter, redraw, re-create, re-interpret,"
                                                            " or modify the bottle, label, logo, text, shape, typography, or any branding elements in any way.",
                                "mask" : f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                        if isinstance(output0, list):
                            bg_url = str(output0[0])
                        else:
                            bg_url = str(output0)
                        f.seek(0)
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "image_input": [f, bg_url],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        if isinstance(output1, list) and len(output1) > 0:
                            output = output1[0]  # 리스트면 첫 번째 요소
                        else:
                            output = output1

                    elif model_choice == "custom_bbq":
                        output0 = replicate.run(
                            "clipnpaper/alcohol_bbq:81520f34f3770086c356c923a1101026bf77cbbe0bc84c3d2d9a496fa81735fa",
                            input={
                                "model": "dev",
                                #"input_image": f,
                                "prompt": "BBQ background" +full_prompt+ "\n keep the provided bottle exactly as it is, "
                                                            "do not alter the bottle. Do not alter, redraw, re-create, re-interpret,"
                                                            " or modify the bottle, label, logo, text, shape, typography, or any branding elements in any way.",
                                "mask" : f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                        if isinstance(output0, list):
                            bg_url = str(output0[0])
                        else:
                            bg_url = str(output0)
                        f.seek(0)
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "image_input": [f, bg_url],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        if isinstance(output1, list) and len(output1) > 0:
                            output = output1[0]  # 리스트면 첫 번째 요소
                        else:
                            output = output1

                    elif model_choice == "custom_pojangmacha":
                        output0 = replicate.run(
                            "clipnpaper/pojangmacha:5470dfeb19844ba06245c7e22214b7cdbce9e6034e8edcad74d9ef5a0c61a5cd",
                            input={
                                "model": "dev",
                                #"input_image": f,
                                "prompt": "pojangmacha background" +full_prompt+ "\n keep the provided bottle exactly as it is, "
                                                            "do not alter the bottle. Do not alter, redraw, re-create, re-interpret,"
                                                            " or modify the bottle, label, logo, text, shape, typography, or any branding elements in any way.",
                                "mask" : f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                        if isinstance(output0, list):
                            bg_url = str(output0[0])
                        else:
                            bg_url = str(output0)
                        f.seek(0)
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "image_input": [f, bg_url],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        if isinstance(output1, list) and len(output1) > 0:
                            output = output1[0]  # 리스트면 첫 번째 요소
                        else:
                            output = output1

                    elif model_choice=="nanobanana":
                        output = client.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt": full_prompt,
                                "image_input": [f],
                                "aspect_ratio": aspect_ratio,
                                "output_format": "png"
                            }
                        )

                    generated_url = None
                    if isinstance(output, list) and output:
                        generated_url = output[0]
                    elif isinstance(output, str):
                        generated_url = output

                    elif output: 
                        try:
                            generated_url = str(output)
                            # 변환된 문자열이 URL이 맞는지 간단히 확인
                            if not generated_url.startswith('http'):
                                generated_url = None # URL이 아니면 다시 None으로
                        except Exception:
                            generated_url = None # 변환 중 오류 발생 시

                    if generated_url:
                        image_urls.append(generated_url)
                        if request.user.is_authenticated:
                            # 생성된 이미지를 DB에 저장
                            GeneratedImage.objects.create(
                                user=request.user,
                                image_url=generated_url,
                                prompt=full_prompt,

                                product_type=product_type,
                                theme=theme,
                                mood=mood,
                                placement=placement,
                                user_prompt=user_prompt
                            )

                # 2. 추천 문구 생성 (파일을 다시 열 필요 없음)
                f.seek(0) # 파일 포인터를 다시 처음으로 돌립니다.
                output = client.run(
                    "openai/o4-mini",
                    input={
                        "prompt": word_prompt,
                        "input_image": f,
                    }
                )
                word_urls.append(flatten_output(output))
                        
                        # 임시로 업로드된 파일 삭제 (선택 사항)
                        # default_storage.delete(file_path)

                # GET 요청이거나, POST 처리가 완료된 후 템플릿을 렌더링합니다.
        return render(request, "result.html", {
            "image_urls": image_urls,
            "word_urls": word_urls
        })
    else : 
        context = {
            "settings": {
                "product_type": request.GET.get("product_type", "소주"),
                "theme": request.GET.get("theme", "해변"),
                "mood": request.GET.get("mood", "따듯한"),
                "placement": request.GET.get("placement", "테이블 위에 놓인"),
                "prompt": request.GET.get("prompt", ""),
                "extra_requirements": request.GET.get("extra_requirements", ""),
                "model": request.GET.get("model", "black-forest-labs/flux-kontext-pro"),
                "aspect_ratio": request.GET.get("aspect_ratio", "16:9"),
                "count": request.GET.get("count", "4"),
            }
        }
        # main.html을 렌더링 (폼 페이지)
        return render(request, "main.html", context)      
    """return render(request, "main.html", {
        "image_urls": image_urls,
        "word_urls": word_urls
    })"""

# views.py

# ... (기존 코드들) ...

@login_required(login_url='login')
def analysis_view(request):
    if request.method != "POST":
        return render(request, "analysis.html")

    uploaded_file = request.FILES.get("target_image")
    if not uploaded_file:
        return render(request, "analysis.html", {"error": "이미지를 선택해주세요."})
    
    file_path = default_storage.save(f"temp/analysis/{uploaded_file.name}", uploaded_file)
    full_path = default_storage.path(file_path)
    file_url = default_storage.url(file_path) # 템플릿에서 보여줄 URL
    original_image_url = settings.MEDIA_URL + file_path


    analysis_text = ""

    # 분석 결과 데이터 (기본값)
    parsed_data = {
        "product_type": "맥주", "theme": "해변", "mood": "신나는", "placement": "테이블 위에 놓인"
    }

    try:
        with open(file_path, "rb") as f:
            # ⭐ [핵심] 우리가 가진 선택지 리스트를 프롬프트에 포함시킵니다.
            # LLaVA에게 이 중에서만 고르라고 시킵니다.
            reasoning_effort = request.POST.get('reasoning_effort', 'minimal')
            verbosity = request.POST.get('verbosity', 'medium')
            system_prompt = "You are a professional liquor marketing expert and photographer. Your task is to analyze the provided image and generate a complete marketing brief and AI image generation prompts"
            prompt = """
            Analyze this image for a liquor advertisement and categorize it exactly into the options provided below.
            Output must be in Korean.

            1. Product Type (Choose one): [소주, 맥주, 와인, 위스키, 막걸리, 칵테일]
            2. Theme (Choose one): [해변, 바, 집 (홈파티), 포장마차, 고급 식당, 캠핑장]
            3. Mood (Choose one): [따듯한, 차가운, 신나는, 세련된, 아련한, 역동적인]
            4. Placement (Choose one): [테이블 위, 사람 손, 바에 진열]
            5. Recommended Prompt: (Write a detailed prompt to generate a similar image in Korean)
            
            Format your response exactly like this:
            Product: [Value]
            Theme: [Value]
            Mood: [Value]
            Placement: [Value]
            Prompt: [Value]
            """
            
            output = client.run(
                "openai/gpt-5",
                input=
                    {"prompt": prompt,
                        "image_input": [f],
                        "system_prompt": system_prompt,
                        "reasoning_effort": reasoning_effort,
                        "verbosity": verbosity
                }
            )
            analysis_text = flatten_output(output)
            
            # 3. DB 업데이트
            #analyzed_obj.analysis_text = analysis_text
            
            #analyzed_obj.save()

            # 4. 결과 텍스트를 파싱해서 딕셔너리로 변환 (바로 적용하기 위해)
            # 예: "Product: 맥주" -> {"product_type": "맥주"}
            lines = analysis_text.split('\n')
            for line in lines:
                if "Product:" in line: parsed_data['product_type'] = line.split("Product:")[1].strip()
                elif "Theme:" in line: parsed_data['theme'] = line.split("Theme:")[1].strip()
                elif "Mood:" in line: parsed_data['mood'] = line.split("Mood:")[1].strip()
                elif "Placement:" in line: parsed_data['placement'] = line.split("Placement:")[1].strip()
                elif "Prompt:" in line: parsed_data['user_prompt'] = line.split("Prompt:")[1].strip()

    except Exception as e:
        print(f"Analysis Error: {e}")
        return render(request, "analysis.html", {"error": "분석 중 오류가 발생했습니다."})

    # 5. 결과 페이지로 이동 (분석된 옵션 값도 같이 넘김)
    return render(request, "result_analysis.html", {
        "original_iamge_url":original_image_url,
        "analysis_text": lines,
        "parsed_data": parsed_data # 파싱된 데이터 전달
    })

@login_required(login_url='login')
def editing_view(request):
    # 1. [GET] 편집 폼 페이지 보여주기
    if request.method != "POST":
        return render(request, "editing.html")

    # 2. [POST] 편집 로직 실행
    uploaded_file = request.FILES.get("edit_image")
    user_prompt = request.POST.get("edit_positive_prompt")

    if not uploaded_file:
        return render(request, "editing.html", {"error": "편집할 이미지를 첨부해주세요."})
    
    if not user_prompt:
        return render(request, "editing.html", {"error": "어떻게 편집할지 내용을 입력해주세요."})

    # 파일 임시 저장 (Replicate에 보내기 위함, DB 저장 X)
    # media/temp/edit/ 폴더에 저장
    file_path = default_storage.save(f"temp/edit/{uploaded_file.name}", uploaded_file)
    full_path = default_storage.path(file_path)
    # 템플릿에 보여줄 원본 이미지 URL
    original_image_url = settings.MEDIA_URL + file_path
    edited_image_url = None
    try:
        with open(full_path, "rb") as f:
            # ⭐ Replicate 모델 호출 (Instruct-Pix2Pix)
            output = client.run(
                "bytedance/seedream-4",
                input={
                    "image_input": [f],
                    "prompt": user_prompt,
                }
            )
            
            # 결과 URL 추출 (헬퍼 함수 사용)
            image_url = None
            if isinstance(output, list): image_url = output[0]
            elif isinstance(output, str): image_url = output
            else: image_url = str(output)

            image_url = str(image_url).strip()
    except Exception as e:
        print(f"Editing Error: {e}")
        return render(request, "editing.html", {"error": "이미지 편집 중 오류가 발생했습니다."})
    
    finally:
        pass

    # 3. 결과 페이지로 이동 (URL과 프롬프트만 전달)
    return render(request, "result_editing.html", {
        "original_image_url": original_image_url,
        "edited_image_url": image_url,
        "prompt": user_prompt
    })

@login_required(login_url='login')
def video_view(request):
    # 1. [GET] 입력 폼 보여주기
    if request.method != "POST":
        return render(request, "video.html")

    # 2. [POST] 영상 생성 요청 처리
    uploaded_file = request.FILES.get("video_image")
    
    if not uploaded_file:
        return render(request, "video.html", {"error": "이미지를 선택해주세요."})

    # 파일 임시 저장
    file_path = default_storage.save(f"temp/video/{uploaded_file.name}", uploaded_file)
    full_path = default_storage.path(file_path)
    file_obj = open(full_path, "rb")
    
    video_url = None

    try:
        with open(full_path, "rb") as f:
            # 사용자 입력값 가져오기 (video.html의 name과 일치)
            video_model = request.POST.get('video_model', 'google/veo-3.1') # 기본값 설정
            prompt = request.POST.get('video_positive_prompt', 'Animate this image')
            
            # 파라미터 형변환
            try:
                duration = int(request.POST.get('video_duration', '4'))
            except ValueError:
                duration = 4
                
            aspect_ratio = request.POST.get('video_ratio', '16:9')
            resolution = request.POST.get('video_resolution', '720p')
            
            # boolean 변환
            audio_val = request.POST.get('video_generate_audio', 'false')
            generate_audio = True if audio_val == 'true' else False

            output = client.run(
                video_model,
                input={
                    "image": f,
                    "prompt": prompt,
                    "aspect_ratio": aspect_ratio,
                    "duration": duration,
                    "resolution": resolution,
                    "generate_audio": generate_audio
                    # 모델에 따라 fps 등 추가 파라미터가 필요할 수 있음
                }
            )
            
            # 결과 URL 추출
            video_url = get_output_url(output)

    except Exception as e:
        print(f"Video Generation Error: {e}")
        return render(request, "video.html", {"error": f"영상 생성 중 오류가 발생했습니다: {str(e)}"})
    
    finally:
        # 임시 파일 삭제 (필요시)
        pass

    # 3. 결과 페이지로 이동
    return render(request, "result_video.html", {"video_url": video_url})

def signup(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) # 회원가입 후 자동 로그인
            return redirect('main') # 메인 페이지로 리다이렉트
    else:
        # GET 요청일 때 (페이지에 처음 접속)
        form = CustomUserCreationForm()
    
    # 템플릿에 폼을 전달
    return render(request, 'signup.html', {'form': form})