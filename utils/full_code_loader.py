import os

IGNORED = ("__pycache__", ".venv", ".git", "node_modules", "site-packages")

# 🔥 FORCE REAL PROJECT ROOT (not working dir)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def load_full_project_code():
    project_code = []

    for root_dir, dirs, files in os.walk(BASE_DIR):
        dirs[:] = [d for d in dirs if d not in IGNORED]

        for file in files:
            if not file.endswith(".py"):
                continue

            path = os.path.join(root_dir, file)

            try:
                # Skip huge files (Gemini token protection)
                if os.path.getsize(path) > 200_000:
                    continue

                with open(path, "r", encoding="utf-8", errors="ignore") as f:
                    content = f.read()

                relative = os.path.relpath(path, BASE_DIR)

                project_code.append(
                    + content
                )

            except Exception:
                continue

    return "\n".join(project_code)
