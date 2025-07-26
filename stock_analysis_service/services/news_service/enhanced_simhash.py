"""
향상된 SimHash 필터 - 로컬 구현
뉴스 중복 제거를 위한 SimHash 기반 필터링
"""
import hashlib
import re
from typing import Set, Optional, Dict, Tuple
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class EnhancedSimHashFilter:
    """향상된 SimHash 필터 - 로컬 구현"""
    
    def __init__(self, hamming_threshold: int = 3, ttl_hours: int = 48):
        """
        Args:
            hamming_threshold: 해밍 거리 임계값 (기본: 3)
            ttl_hours: 해시 보관 시간 (기본: 48시간)
        """
        self.hamming_threshold = hamming_threshold
        self.ttl_hours = ttl_hours
        self.processed_hashes: Dict[int, datetime] = {}
        self.processed_texts: Set[str] = set()
        
        logger.info(f"✅ EnhancedSimHashFilter 초기화: 임계값={hamming_threshold}, TTL={ttl_hours}시간")
    
    def _clean_text(self, text: str) -> str:
        """텍스트 정리"""
        if not text:
            return ""
        
        # 기본 정리
        text = re.sub(r'[^\w\s가-힣]', ' ', text)  # 특수문자 제거
        text = re.sub(r'\s+', ' ', text)  # 연속 공백 정리
        text = text.strip().lower()
        
        return text
    
    def _calculate_simhash(self, text: str) -> int:
        """텍스트의 SimHash 계산"""
        if not text:
            return 0
        
        # 텍스트 정리
        clean_text = self._clean_text(text)
        
        # 간단한 해시 기반 SimHash (실제 구현 대신)
        text_hash = hashlib.md5(clean_text.encode('utf-8')).hexdigest()
        
        # 해시를 정수로 변환
        simhash = int(text_hash[:8], 16)  # 32비트 해시
        
        return simhash
    
    def _hamming_distance(self, hash1: int, hash2: int) -> int:
        """두 해시 간 해밍 거리 계산"""
        xor_result = hash1 ^ hash2
        distance = bin(xor_result).count('1')
        return distance
    
    def _cleanup_old_hashes(self):
        """오래된 해시 정리"""
        current_time = datetime.now()
        cutoff_time = current_time - timedelta(hours=self.ttl_hours)
        
        old_hashes = [
            hash_val for hash_val, timestamp in self.processed_hashes.items()
            if timestamp < cutoff_time
        ]
        
        for hash_val in old_hashes:
            del self.processed_hashes[hash_val]
        
        if old_hashes:
            logger.debug(f"🧹 오래된 해시 {len(old_hashes)}개 정리 완료")
    
    def is_duplicate(self, text: str) -> bool:
        """텍스트 중복 검사 (간단한 버전)"""
        if not text:
            return False
        
        # 정확한 텍스트 중복 검사
        clean_text = self._clean_text(text)
        if clean_text in self.processed_texts:
            logger.debug(f"🔄 정확한 텍스트 중복 감지: {clean_text[:50]}...")
            return True
        
        # 텍스트 저장
        self.processed_texts.add(clean_text)
        
        # 해시 중복 검사
        text_hash = self._calculate_simhash(text)
        current_time = datetime.now()
        
        # 오래된 해시 정리
        self._cleanup_old_hashes()
        
        # 유사 해시 검사
        for existing_hash, timestamp in self.processed_hashes.items():
            distance = self._hamming_distance(text_hash, existing_hash)
            if distance <= self.hamming_threshold:
                logger.debug(f"🔄 SimHash 유사 중복 감지: 거리={distance}, 임계값={self.hamming_threshold}")
                return True
        
        # 새로운 해시 저장
        self.processed_hashes[text_hash] = current_time
        
        return False
    
    def check_and_insert(self, stock_code: str, title: str, content: str, url: str) -> Tuple[bool, Optional[object]]:
        """기존 인터페이스 호환성을 위한 메서드"""
        combined_text = f"{title} {content}"
        is_duplicate = self.is_duplicate(combined_text)
        
        if is_duplicate:
            # 중복 정보 객체 (간단한 버전)
            match_info = type('MatchInfo', (), {
                'distance': 0,
                'matched_id': 'simhash_match',
                'matched_title': title[:50] + '...'
            })()
            return True, match_info
        
        return False, None
    
    def get_stats(self) -> Dict[str, int]:
        """통계 정보 반환"""
        return {
            "total_hashes": len(self.processed_hashes),
            "total_texts": len(self.processed_texts),
            "hamming_threshold": self.hamming_threshold,
            "ttl_hours": self.ttl_hours
        } 