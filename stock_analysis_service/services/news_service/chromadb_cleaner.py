"""
크로마 DB 정리 및 초기화 스크립트
테스트 데이터 제거 및 깨끗한 상태로 초기화
"""
import os
import shutil
import logging
from pathlib import Path

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ChromaDBCleaner:
    """크로마 DB 정리 도구"""
    
    def __init__(self, base_path: str = "../../data/chroma"):
        self.base_path = Path(base_path)
        self.backup_path = Path("../../data/chroma_backup")
        
    def backup_current_db(self):
        """현재 DB 백업"""
        try:
            if self.base_path.exists():
                if self.backup_path.exists():
                    shutil.rmtree(self.backup_path)
                
                shutil.copytree(self.base_path, self.backup_path)
                logger.info(f"✅ 크로마 DB 백업 완료: {self.backup_path}")
                return True
            else:
                logger.warning("⚠️ 백업할 크로마 DB가 없습니다")
                return False
        except Exception as e:
            logger.error(f"❌ 백업 실패: {e}")
            return False
    
    def clean_chromadb(self):
        """크로마 DB 완전 정리"""
        try:
            if self.base_path.exists():
                shutil.rmtree(self.base_path)
                logger.info("🧹 기존 크로마 DB 삭제 완료")
            
            # 새 디렉토리 생성
            self.base_path.mkdir(parents=True, exist_ok=True)
            logger.info("📁 새 크로마 DB 디렉토리 생성 완료")
            
            return True
        except Exception as e:
            logger.error(f"❌ 크로마 DB 정리 실패: {e}")
            return False
    
    def restore_from_backup(self):
        """백업에서 복원"""
        try:
            if self.backup_path.exists():
                if self.base_path.exists():
                    shutil.rmtree(self.base_path)
                
                shutil.copytree(self.backup_path, self.base_path)
                logger.info("📥 백업에서 크로마 DB 복원 완료")
                return True
            else:
                logger.error("❌ 백업 파일이 없습니다")
                return False
        except Exception as e:
            logger.error(f"❌ 복원 실패: {e}")
            return False
    
    def initialize_clean_db(self):
        """깨끗한 DB로 초기화"""
        try:
            logger.info("🚀 크로마 DB 초기화 시작...")
            
            # 1. 백업
            self.backup_current_db()
            
            # 2. 정리
            self.clean_chromadb()
            
            # 3. 기본 컬렉션 생성 준비
            logger.info("✅ 크로마 DB 초기화 완료!")
            logger.info("💡 이제 뉴스 서비스를 실행하면 깨끗한 상태에서 시작됩니다")
            
            return True
        except Exception as e:
            logger.error(f"❌ 초기화 실패: {e}")
            return False

def main():
    """메인 실행 함수"""
    print("🧹 크로마 DB 정리 도구")
    print("=" * 50)
    
    cleaner = ChromaDBCleaner()
    
    while True:
        print("\n선택하세요:")
        print("1. 크로마 DB 완전 초기화 (권장)")
        print("2. 현재 DB 백업만")
        print("3. 백업에서 복원")
        print("4. 종료")
        
        choice = input("\n선택 (1-4): ").strip()
        
        if choice == "1":
            if cleaner.initialize_clean_db():
                print("✅ 초기화 완료! 뉴스 서비스를 실행하세요.")
                break
            else:
                print("❌ 초기화 실패")
        
        elif choice == "2":
            if cleaner.backup_current_db():
                print("✅ 백업 완료!")
            else:
                print("❌ 백업 실패")
        
        elif choice == "3":
            if cleaner.restore_from_backup():
                print("✅ 복원 완료!")
            else:
                print("❌ 복원 실패")
        
        elif choice == "4":
            print("👋 종료합니다.")
            break
        
        else:
            print("❌ 잘못된 선택입니다.")

if __name__ == "__main__":
    main() 