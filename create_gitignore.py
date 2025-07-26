#!/usr/bin/env python3
"""
.gitignore 파일을 생성하는 스크립트
"""

def create_gitignore():
    gitignore_content = """# Virtual environments
venv/
.venv/
*/venv/
*/.venv/

# Python
__pycache__/
*.py[cod]
*.so
*.egg-info/
*.pyc
*.pyo
*.pyd
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/

# IDE
.vscode/
.idea/
*.swp
*.swo
*~

# OS
.DS_Store
.DS_Store?
._*
.Spotlight-V100
.Trashes
ehthumbs.db
Thumbs.db

# Logs
*.log

# Environment variables
.env
.env.local
.env.development.local
.env.test.local
.env.production.local

# Database
*.db
*.sqlite3

# Jupyter Notebook
.ipynb_checkpoints

# Node modules (if using frontend)
node_modules/
npm-debug.log*
yarn-debug.log*
yarn-error.log*
"""

    try:
        with open('.gitignore', 'w', encoding='utf-8') as f:
            f.write(gitignore_content)
        print("✅ .gitignore 파일이 성공적으로 생성되었습니다!")
        print("\n다음 명령어를 실행하세요:")
        print("git add .gitignore")
        print("git commit -m 'Add .gitignore file'")
        print("git push origin main")
        
    except Exception as e:
        print(f"❌ 에러 발생: {e}")

if __name__ == "__main__":
    create_gitignore()