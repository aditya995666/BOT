import os
from dotenv import load_dotenv
from google import genai
from agents.security_guard import security_check

from memory.image_memory import fetch_image, store_image

load_dotenv()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def image_agent(prompt: str, user_id="IMAGE_USER") -> bytes:
    # 🔐 MODERATION
    security_check(user_id, prompt)

    cached = fetch_image(prompt)
    if cached:
        return cached


    print("🔵 Generating image using Gemini (Imagen)")

    # 2️⃣ ✅ CORRECT IMAGE API
    response = client.models.generate_images(
        model="gemini-2.0-flash-exp",
        prompt=prompt
    )

    # 3️⃣ Extract image
    image_bytes = response.generated_images[0].image.image_bytes

    store_image(prompt, image_bytes)
    return image_bytes
