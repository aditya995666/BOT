import os
from memory.database import get_connection

IMAGE_DIR = "generated_images"
os.makedirs(IMAGE_DIR, exist_ok=True)

conn = get_connection()


def normalize_prompt(prompt: str) -> str:
    return prompt.lower().strip()


def fetch_image(prompt: str):
    prompt = normalize_prompt(prompt)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT image_path FROM image_memory WHERE prompt=?",
        (prompt,)
    )
    row = cursor.fetchone()

    if row and os.path.exists(row[0]):
        with open(row[0], "rb") as f:
            return f.read()

    return None


def store_image(prompt: str, image_bytes: bytes):
    prompt = normalize_prompt(prompt)

    filename = f"{abs(hash(prompt))}.png"
    path = os.path.join(IMAGE_DIR, filename)

    with open(path, "wb") as f:
        f.write(image_bytes)

    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO image_memory (prompt, image_path) VALUES (?, ?)",
        (prompt, path)
    )
    conn.commit()

    return path
