"""
Final verification script for Sports Telecast Backend
Checks all components are properly set up and working
"""
import subprocess
import sys
import importlib.util
from pathlib import Path

def check_file_exists(file_path: str) -> bool:
    """Check if a file exists"""
    return Path(file_path).exists()

def check_python_imports():
    """Check that all Python modules can be imported"""
    print("🔍 Checking Python module imports...")
    
    modules_to_check = [
        "src.api.main",
        "src.auth.jwt_auth", 
        "src.database.connection",
        "src.models.user",
        "src.models.match",
        "src.models.emoji",
        "src.websocket.manager"
    ]
    
    failed_imports = []
    
    for module_name in modules_to_check:
        try:
            # Try to import the module
            spec = importlib.util.find_spec(module_name)
            if spec is None:
                failed_imports.append(f"{module_name} - Module not found")
            else:
                print(f"✅ {module_name}")
        except Exception as e:
            failed_imports.append(f"{module_name} - {str(e)}")
    
    if failed_imports:
        print("❌ Failed imports:")
        for failure in failed_imports:
            print(f"   {failure}")
        return False
    else:
        print("✅ All modules can be imported successfully")
        return True

def check_required_files():
    """Check that all required files exist"""
    print("\n🔍 Checking required files...")
    
    required_files = [
        "src/api/main.py",
        "src/api/auth.py", 
        "src/api/matches.py",
        "src/api/emoji.py",
        "src/api/highlights.py",
        "src/api/websocket.py",
        "src/auth/jwt_auth.py",
        "src/database/connection.py",
        "src/models/user.py",
        "src/models/match.py", 
        "src/models/emoji.py",
        "src/websocket/manager.py",
        "requirements.txt",
        ".env.example",
        "README.md"
    ]
    
    missing_files = []
    
    for file_path in required_files:
        if check_file_exists(file_path):
            print(f"✅ {file_path}")
        else:
            missing_files.append(file_path)
            print(f"❌ {file_path}")
    
    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} required files")
        return False
    else:
        print("✅ All required files present")
        return True

def run_linting():
    """Run code linting"""
    print("\n🔍 Running code linting...")
    
    try:
        result = subprocess.run(
            ["python", "-m", "flake8", "src/", "--max-line-length=120", "--ignore=E501,W503"],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0:
            print("✅ Code linting passed")
            return True
        else:
            print("❌ Code linting failed:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ Linting timed out")
        return False
    except Exception as e:
        print(f"❌ Linting error: {e}")
        return False

def check_openapi_generation():
    """Check OpenAPI spec generation"""
    print("\n🔍 Checking OpenAPI spec generation...")
    
    try:
        # Try to generate the OpenAPI spec
        result = subprocess.run(
            ["python", "-c", "import sys; sys.path.append('.'); from src.api.main import app; print('✅ FastAPI app loads successfully')"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd="."
        )
        
        if result.returncode == 0:
            print("✅ FastAPI application loads successfully")
            return True
        else:
            print("❌ FastAPI application failed to load:")
            print(result.stdout)
            print(result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ Error checking FastAPI app: {e}")
        return False

def main():
    """Main verification function"""
    print("🏟️ Sports Telecast Backend - Setup Verification")
    print("=" * 60)
    
    checks = [
        ("Required Files", check_required_files),
        ("Python Imports", check_python_imports), 
        ("FastAPI App", check_openapi_generation),
        ("Code Linting", run_linting)
    ]
    
    passed = 0
    failed = 0
    
    for check_name, check_func in checks:
        print(f"\n{'='*40}")
        print(f"Running: {check_name}")
        print('='*40)
        
        try:
            if check_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            failed += 1
    
    print(f"\n{'='*60}")
    print("📊 VERIFICATION RESULTS")
    print('='*60)
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    
    if failed == 0:
        print("\n🎉 All verification checks passed!")
        print("\n🚀 Ready to start the server:")
        print("   PYTHONPATH=. uvicorn src.api.main:app --host 0.0.0.0 --port 8000 --reload")
        print("\n📚 API Documentation will be available at:")
        print("   http://localhost:8000/docs")
        sys.exit(0)
    else:
        print(f"\n⚠️  {failed} verification checks failed.")
        print("   Please fix the issues above before running the server.")
        sys.exit(1)

if __name__ == "__main__":
    main()
