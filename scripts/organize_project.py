import os
import shutil
import glob

def organize():
    print("🚀 Starting Project Organization...")

    # 1. Create directories
    os.makedirs("tests", exist_ok=True)
    os.makedirs("scripts", exist_ok=True)
    
    # 2. Move prototype.py to production/prompts.py
    if os.path.exists("prototype.py"):
        shutil.move("prototype.py", "production/prompts.py")
        print("✅ Moved prototype.py -> production/prompts.py")
    
    # 3. Move test files
    for f in glob.glob("test_*.py"):
        shutil.move(f, f"tests/{f}")
        print(f"✅ Moved {f} -> tests/")
            
    # 4. Move scripts
    scripts_to_move = ["migrate.py", "get_gmail_token.py", "fix_schema.py", "organize_project.py"]
    for f in scripts_to_move:
        if os.path.exists(f):
            shutil.move(f, f"scripts/{f}")
            print(f"✅ Moved {f} -> scripts/")

    # 5. Update imports
    files_to_fix = []
    if os.path.exists("tests/"):
        for f in os.listdir("tests/"):
            if f.endswith(".py"):
                files_to_fix.append(f"tests/{f}")
            
    files_to_fix.extend([
        "production/agents/classifier.py",
        "production/services/agent_service.py"
    ])
    
    for filepath in files_to_fix:
        if os.path.exists(filepath):
            try:
                with open(filepath, 'r', encoding='utf-8') as file:
                    content = file.read()
                
                new_content = content.replace("from prototype import", "from production.prompts import")
                
                if new_content != content:
                    with open(filepath, 'w', encoding='utf-8') as file:
                        file.write(new_content)
                    print(f"🔧 Fixed imports in {filepath}")
            except Exception as e:
                print(f"⚠️ Failed to process {filepath}: {e}")

    print("✨ Project Organization Complete!")

if __name__ == "__main__":
    organize()
