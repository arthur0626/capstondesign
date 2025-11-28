import os
import replicate
from django.shortcuts import render, redirect, get_object_or_404
from django.core.files.storage import default_storage
from dotenv import load_dotenv
from .models import GeneratedImage, UserProfile
from django.contrib.auth import logout, login
from django.contrib.auth.decorators import login_required
from .forms import CustomUserCreationForm
from django.contrib.auth.models import User

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

def generate_images(request):
    image_urls = []
    word_urls = []

    if request.method != "POST":
        return render(request, "main.html")
    
    if request.method == "POST":
        # GET POST VALUES
        product_type = request.POST.get("product_type", "맥주")
        theme = request.POST.get("theme", "")
        mood = request.POST.get("mood", "")
        placement = request.POST.get("placement", "")
        user_prompt = request.POST.get("prompt", "")
        aspect_ratio = request.POST.get("aspect_ratio", "16:9")
        image_number = request.POST.get("count", "4")
        uploaded_file = request.FILES.get("image")
        model_choice = request.POST.get("model", "flux").lower()

        # 안전하게 정수 변환
        try:
            image_number = max(1, min(int(image_number), 4))  # 1~10 범위 제한
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
        위 상황을 기반으로, 술 마케팅에 어울리는 간결하고 창의적인 한국어 한 줄 문장을 추천해줘.
        상황: {mood} 분위기의 {theme}에서, {product_type} 종류의 술이 {placement}에 위치함. {user_prompt}
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
                    elif model_choice == "alcohol_beach":
                        output0 = replicate.run(
                            "clipnpaper/alcohol_beach:5c3ef136e48fd434e8fa47c9deaad6d12527a61757305ca01169e58fc5b19ef5",
                            input={
                                "model": "dev",
                                "input_image": f,
                                "prompt": full_prompt + "alcohol_beach"+"Do not create alcohol products",
                                "go_fast": False,
                                "lora_scale": 1,
                                "megapixels": "1",
                                "num_outputs": 1,
                                "aspect_ratio": aspect_ratio,
                                "output_format": "png",
                                "guidance_scale": 3,
                                "output_quality": 80,
                                "prompt_strength": 0.8,
                                "extra_lora_scale": 1,
                                "num_inference_steps": 28
                            }
                        )
                        output1 = replicate.run(
                            "google/nano-banana-pro",
                            input={
                                "prompt" : "주류 광고 이미지를 제작합니다. 배경 이미지와 제품 이미지를 합성하세요. 제품의 일관성을 유지하세요. ",
                                "input_image": [f, output0],
                                "aspect_ratio": aspect_ratio,
                                "output_format" : "png"
                            }
                        )
                        output = output1[0]
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