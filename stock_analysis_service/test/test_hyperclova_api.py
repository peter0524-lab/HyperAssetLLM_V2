#!/usr/bin/env python3
"""
HyperCLOVA API 연결 테스트 스크립트
"""

import asyncio
import logging
import sys
import os

# 프로젝트 루트를 Python 경로에 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.llm.hyperclova_client import HyperCLOVAClient
from config.env_local import get_config

# 로깅 설정
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def test_hyperclova_api():
    """HyperCLOVA API 연결 테스트"""
    try:
        # 설정 로드
        config = get_config()
        hyperclova_config = config.get("hyperclova", {})
        
        api_key = hyperclova_config.get("api_key")
        api_url = hyperclova_config.get("api_url")
        
        logger.info("🔧 HyperCLOVA API 테스트 시작")
        logger.info(f"📋 API 키: {api_key[:10]}..." if api_key else "❌ API 키 없음")
        logger.info(f"🔗 API URL: {api_url}")
        
        if not api_key:
            logger.error("❌ API 키가 설정되지 않았습니다.")
            return False
        
        # 클라이언트 생성
        client = HyperCLOVAClient(api_key=api_key, base_url=api_url)
        
        # 간단한 테스트 프롬프트
        test_prompt = """
        다음 뉴스를 50자 이내로 요약해주세요.
        
        제목: SK하이닉스의 실적 개선 전망
        내용: SK하이닉스의 25년 2분기 매출액은 20.4조원(YoY +24%, QoQ +16%), 영업이익은 9.08조원(YoY +66%, QoQ +22%)으로 전망한다. 하나증권이 기존에 가정했던 환율보다 30원 이상 하락하면서 영업이익에서 3천억원 이상 하향 조정이 불가피했다. 다만, 기존에 추정했던 것보다 관세에 따른 선제적인 물량 증가가 일부 파악되어 bit growth는 DRAM을 기존 11%에서 15%로, NAND를 20%에서 25%로 상향 조정했다. DRAM은 HBM 매출비중 확대와 견조한 수급 밸런스를 기반으로 전사 이익을 견인할 전망이다. HBM 3E 12단 출하는 예정대로 원활하게 진행되었고, HBM 3E 매출액에서 절반 이상을 차지할 것으로 추정한다. NAND 부문은 출하량은 크게 증가했지만, DRAM대비 불안정한 수급으로 인해 가격이 여전히 하락하고 있어 전분기대비 이익 개선은 제한될 것으로 전망한다.
        
        요약:
        """
        
        logger.info("🚀 API 호출 테스트 시작...")
        logger.info(f"📝 테스트 프롬프트: {test_prompt.strip()}")
        
        # API 호출
        response = await client.generate_text(test_prompt)
        
        logger.info(f"✅ API 응답: {response}")
        
        if response and len(response.strip()) > 10:
            logger.info("✅ HyperCLOVA API 테스트 성공!")
            return True
        else:
            logger.warning("⚠️ API 응답이 비어있거나 너무 짧습니다.")
            return False
            
    except Exception as e:
        logger.error(f"❌ HyperCLOVA API 테스트 실패: {e}")
        return False

async def main():
    """메인 함수"""
    logger.info("🚀 HyperCLOVA API 연결 테스트 시작")
    
    success = await test_hyperclova_api()
    
    if success:
        logger.info("✅ 모든 테스트 통과!")
        sys.exit(0)
    else:
        logger.error("❌ 테스트 실패!")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main()) 