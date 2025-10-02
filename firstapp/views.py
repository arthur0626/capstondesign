import os
import replicate
from django.shortcuts import render
from django.core.files.storage import default_storage
from dotenv import load_dotenv

load_dotenv()

client = replicate.Client(api_token=os.getenv("REPLICATE_API_TOKEN"))

def flatten_output(output):
    if isinstance(output, list):
        return ' '.join(str(item).strip() for item in output if item).replace("\n", " ").strip()
    elif isinstance(output, str):
        return output.replace("\n", " ").strip()
    return str(output).strip()

def generate_images(request):
    image_urls = []
    word_urls = []

    if request.method == "POST":
        # GET POST VALUES
        theme = request.POST.get("theme", "")
        mood = request.POST.get("mood", "")
        placement = request.POST.get("placement", "")
        user_prompt = request.POST.get("prompt", "")
        aspect_ratio = request.POST.get("aspect_ratio", "16:9")
        image_number = request.POST.get("count", "4")
        # 추가(김현준)
        model_choice = (request.POST.get("model", "flux") or "flux").lower()  # "flux" | "nanobanana"
        uploaded_file = request.FILES.get("image")

        # 안전하게 정수 변환
        try:
            image_number = max(1, min(int(image_number), 10))  # 1~10 범위 제한
        except ValueError:
            image_number = 4  # 기본값

        # 프롬프트 합성
        full_prompt = f"""
        Translate the following product marketing scene into natural and realistic English, without listing:
        "{mood} 분위기의 {theme}에서, 술이 {placement}에 위치한 상황입니다. {user_prompt}"
        """.strip()
        word_prompt = f"""
        위 상황을 기반으로, 술 마케팅에 어울리는 간결하고 창의적인 한국어 한 줄 문장을 추천해줘.
        상황: {mood} 분위기의 {theme}에서, 술이 {placement}에 위치함. {user_prompt}
        """.strip()

        translated_prompt = client.run(
            "openai/o4-mini",
            input={
                "prompt": full_prompt,
            }
        )
        full_prompt = translated_prompt.strip() if isinstance(translated_prompt, str) else str(translated_prompt)


        if uploaded_file:
            file_path = default_storage.save(uploaded_file.name, uploaded_file)
            full_path = default_storage.path(file_path)


            # 모델 추가
            for _ in range(image_number):
                with open(full_path, "rb") as f:
                    if model_choice == "nanobanana":
                        output = client.run(
                            "google/nano-banana",
                            input={
                                "prompt": full_prompt,
                                "image_input": [f],  # 핵심: 리스트 형태
                                "output_format": "jpg"
                            }
                        )
                    else:
                        # 기본: Flux-Kontext-Pro (기존 코드)
                        output = client.run(
                            "black-forest-labs/flux-kontext-pro",
                            input={
                                "prompt": full_prompt,
                                "input_image": f,
                                "aspect_ratio": aspect_ratio,
                            }
                        )
                    image_urls.append(output)

            with open(full_path, "rb") as f:
                    output = client.run(
                        "openai/o4-mini",
                        input={
                            "prompt": word_prompt,
                            "input_image": f,
                        }
                    )
                    word_urls.append(flatten_output(output))


    
                    
    return render(request, "main.html", {
        "image_urls": image_urls,
        "word_urls": word_urls
    })
