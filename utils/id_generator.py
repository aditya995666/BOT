# utils/id_generator.py
import uuid
import time

def generate_id(prefix="TASK"):
    return f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}"
