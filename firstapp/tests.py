import replicate
import os
import requests
from dotenv import load_dotenv

load_dotenv()

client = replicate.Client(api_token="r8_TJajved1845Y6JVNH1zyxBRqOuitY1V4BAT6c")

output = client.run(
    "black-forest-labs/flux-kontext-pro",
    input={
        "prompt": "Korean game-youtuber kim-doe is drinking this small can of beer using one hand on a beach",
        "input_image": open("beer_can_no_bg.png", "rb"),
        "aspect_ratio": "16:9",
    }
)
