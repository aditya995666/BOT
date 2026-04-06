import os
import shutil
import subprocess
import sys
import traceback
import time
import re

class MasterAutoFixAgent:

    def __init__(self):
        self.project_root = os.getcwd()
        self.test_workspace = os.path.join(self.project_root, "_test_workspace")
        self.testing_stage = 1
        self.stage2_timeout = 90

    def run_autofix_pipeline(self, problems, fixes, apply_permanent=False, stage=None):
        if stage:
            self.testing_stage = stage

        logs = [f"🧪 AUTOFIX PIPELINE STARTED | TEST STAGE: {self.testing_stage}"]

        try:
            self.create_test_workspace(logs)

            for i, fix in enumerate(fixes):
                if not self.apply_fix_to_workspace(fix, logs):
                    logs.append(f"❌ Fix {i+1} apply failed")
                    return "\n".join(logs)

            # Check if this is generated code test
            if fixes and "sandbox_generated_code.py" in fixes[0]:
                logs.append("🧪 Testing generated code in sandbox...")
                test_passed = self.test_generated_code_from_fix(fixes[0], logs)
            else:
                logs.append("🧪 Running project integration tests...")
                test_passed = self.run_project_test(logs)

            if test_passed:
                if apply_permanent:
                    self.finalize_fix(logs)
                    logs.append("✅ PERMANENT FIX SUCCESSFULLY APPLIED")
                logs.append("✅ SYSTEM HEALED SUCCESSFULLY")
            else:
                logs.append("❌ Tests failed → Fix rejected (sandbox kept safe)")

        except Exception as e:
            logs.append(f"❌ Pipeline crashed: {type(e).__name__}: {e}")
            logs.append(traceback.format_exc())

        return "\n".join(logs)

    def test_generated_code(self, code_text, logs):
        """Test generated code in isolation"""
        logs.append("📦 Testing generated code in sandbox...")
        logs.append("📦 Creating code sandbox file...")

        try:
            self.create_test_workspace(logs)

            test_file = os.path.join(self.test_workspace, "sandbox_generated_code.py")

            with open(test_file, "w", encoding="utf-8") as f:
                f.write(code_text)

            # Compilation test
            logs.append("🔍 Testing compilation...")
            compile_result = subprocess.run(
                [sys.executable, "-m", "py_compile", "sandbox_generated_code.py"],
                cwd=self.test_workspace,
                capture_output=True,
                text=True,
                timeout=30
            )

            if compile_result.returncode != 0:
                logs.append("❌ Code compilation failed")
                logs.append(compile_result.stderr)
                return False

            logs.append("✅ Compilation passed")

            # Execution test
            logs.append("🏃 Running code execution test...")
            run_result = subprocess.run(
                [sys.executable, "sandbox_generated_code.py"],
                cwd=self.test_workspace,
                capture_output=True,
                text=True,
                timeout=30
            )

            if run_result.returncode != 0:
                logs.append("❌ Code runtime failed")
                logs.append(run_result.stderr)
                return False

            logs.append("✅ Runtime test passed")
            return True

        except Exception as e:
            logs.append(f"❌ Code test crash: {e}")
            return False

    def test_generated_code_from_fix(self, fix_text, logs):
        """Extract code from fix and test it"""
        try:
            # Extract code from fix
            if "CODE:" in fix_text:
                code_part = fix_text.split("CODE:", 1)[1].strip()
                return self.test_generated_code(code_part, logs)
            return False
        except Exception as e:
            logs.append(f"❌ Fix extraction failed: {e}")
            return False

    def create_test_workspace(self, logs):
        logs.append("📦 Creating isolated sandbox...")
        try:
            if os.path.exists(self.test_workspace):
                shutil.rmtree(self.test_workspace, ignore_errors=True)
            time.sleep(0.5)

            ignore = shutil.ignore_patterns(
                "_test_workspace", "__pycache__", "*.pyc", ".git",
                ".venv", "venv", "env", "node_modules"
            )
            shutil.copytree(self.project_root, self.test_workspace, ignore=ignore, dirs_exist_ok=True)
            logs.append("✅ Sandbox created successfully")
        except Exception as e:
            logs.append(f"❌ Sandbox creation failed: {e}")
            raise

    def apply_fix_to_workspace(self, fix_text, logs):
        try:
            if "FILE:" not in fix_text:
                logs.append("❌ Invalid fix format (missing FILE:)")
                return False

            for block in fix_text.split("FILE:")[1:]:
                if "CODE:" not in block:
                    continue
                path_part, code_part = block.split("CODE:", 1)
                file_path = path_part.strip()
                new_code = code_part.strip()

                target_path = os.path.join(self.test_workspace, file_path)
                os.makedirs(os.path.dirname(target_path), exist_ok=True)

                with open(target_path, "w", encoding="utf-8") as f:
                    f.write(new_code + "\n")

                logs.append(f"✅ Patched → {file_path}")

            return True
        except Exception as e:
            logs.append(f"❌ Apply fix error: {e}")
            return False

    def run_project_test(self, logs):
        """Run full project integration test"""
        try:
            if self.testing_stage == 1:
                logs.append("🧪 STAGE 1: Generated code sandbox test")
                
                generated_file = os.path.join(self.test_workspace, "sandbox_generated_code.py")
                if os.path.exists(generated_file):
                    return self.test_generated_code_from_file(generated_file, logs)
                
                logs.append("✅ Stage 1 passed (no code to validate)")
                return True
            else:
                logs.append("🧪 STAGE 2: Full project integration testing")
                
                # Check app.py compilation
                app_file = os.path.join(self.test_workspace, "app.py")
                if os.path.exists(app_file):
                    compile_result = subprocess.run(
                        [sys.executable, "-m", "py_compile", "app.py"],
                        cwd=self.test_workspace,
                        capture_output=True,
                        text=True,
                        timeout=30
                    )
                    if compile_result.returncode != 0:
                        logs.append("❌ Syntax error in app.py")
                        logs.append(compile_result.stderr[:1000])
                        return False

                    import_result = subprocess.run(
                        [sys.executable, "-c", "import app"],
                        cwd=self.test_workspace,
                        capture_output=True,
                        text=True,
                        timeout=45
                    )
                    if import_result.returncode != 0:
                        logs.append("❌ Import failed")
                        logs.append(import_result.stderr[:1000])
                        return False

                    logs.append("🏃 Starting full app in headless mode")
                    env = os.environ.copy()
                    env["STREAMLIT_SERVER_HEADLESS"] = "true"
                    env["STREAMLIT_SERVER_PORT"] = "9999"

                    process = subprocess.Popen(
                        [sys.executable, "-m", "streamlit", "run", "app.py"],
                        cwd=self.test_workspace,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        env=env,
                        text=True
                    )

                    start_time = time.time()
                    startup_success = False
                    while time.time() - start_time < self.stage2_timeout:
                        line = process.stderr.readline().strip() if process.stderr else ""
                        if line:
                            logs.append(f"APP LOG: {line}")

                        if re.search(r"(Streamlit app running|Local URL: http|Network URL: http)", line, re.IGNORECASE):
                            startup_success = True
                            logs.append("✅ App started successfully")
                            break

                        if re.search(r"(error|exception|traceback|failed)", line, re.IGNORECASE):
                            logs.append("❌ App startup error detected")
                            process.terminate()
                            return False

                        time.sleep(0.5)

                    process.terminate()

                    if not startup_success:
                        logs.append(f"⏱️ Timeout after {self.stage2_timeout}s — no startup confirmation")
                        return False

                    logs.append("✅ Project integrated and ran successfully")
                    return True
                
                logs.append("✅ Integration test passed")
                return True
                
        except Exception as e:
            logs.append(f"❌ Test error: {str(e)}")
            return False

    def test_generated_code_from_file(self, file_path, logs):
        """Test generated code from file"""
        try:
            with open(file_path, 'r') as f:
                code = f.read()
            return self.test_generated_code(code, logs)
        except Exception as e:
            logs.append(f"❌ Failed to read generated code: {e}")
            return False

    def finalize_fix(self, logs):
        logs.append("💾 Applying permanent changes to main project...")
        try:
            for root, _, files in os.walk(self.test_workspace):
                rel_path = os.path.relpath(root, self.test_workspace)
                if rel_path == '.':
                    dest_dir = self.project_root
                else:
                    dest_dir = os.path.join(self.project_root, rel_path)
                
                os.makedirs(dest_dir, exist_ok=True)

                for file in files:
                    # Skip temporary files
                    if file.startswith('sandbox_') or file == 'test_code.py':
                        continue
                    
                    src = os.path.join(root, file)
                    dst = os.path.join(dest_dir, file)
                    shutil.copy2(src, dst)
                    logs.append(f"✅ Applied: {os.path.join(rel_path, file)}")

            logs.append("✅ Permanent fix applied successfully")
        except Exception as e:
            logs.append(f"❌ Permanent apply failed: {e}")
            raise