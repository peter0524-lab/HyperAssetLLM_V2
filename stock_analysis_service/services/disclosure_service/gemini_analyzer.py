import json
import re
import subprocess
import sys
import asyncio
from typing import Dict, Optional


class GeminiDisclosureAnalyzer:
    def __init__(self, gemini_cmd_path: str = "C:/Users/User/AppData/Roaming/npm/gemini.cmd"):
        self.gemini_cmd_path = gemini_cmd_path

    def generate_prompt(self, disclosure_content: str, stock_name: str) -> str:
        """Gemini에게 보낼 프롬프트 생성"""
        return f"""
당신은 주식 투자 전문가입니다. 다음 공시가 {stock_name} 주식에 미치는 영향을 분석해주세요.

공시 내용:
{disclosure_content}

다음 분석 결과항목을 제공해주세요:

1. 공시 요약 (3줄 이내):
2. 영향도 점수 (0-1 사이, 0: 매우 부정적, 0.5: 중립, 1: 매우 긍정적):
3. "긍정"/"부정"/"중립" 세가지 중 판단 및 근거:
4. 주요 키워드 (콤마로 구분):
5. 예상 주가 영향 (상승/하락/보합):
6. 영향 지속 시간(단기, 중기, 장기):

다음 JSON 형식으로 **정확하게 JSON 객체 하나만** 출력하세요. 그 외 문장은 포함하지 마세요:

{{
    "공시 요약": "",
    "영향도 점수": 0.0,
    "sentiment": "",
    "sentiment 판단근거": "",
    "주요키워드": ["", ""],
    "예상 주가 영향": "",
    "영향 지속 시간": ""
}}
        """

    def get_partial_key_value(self, d: dict, keyword: str):
        for k, v in d.items():
            if keyword in k:
                return v
        return None

    def parse_response(self, response_text: str) -> Dict:
        try:
            match = re.search(r"\{.*\}", response_text, re.DOTALL)
            if not match:
                raise json.JSONDecodeError("JSON 객체를 찾을 수 없습니다.", response_text, 0)

            parsed = json.loads(match.group(0))

            return {
                "summary": self.get_partial_key_value(parsed, "요약"),
                "impact_score": self.get_partial_key_value(parsed, "점수"),
                "sentiment": self.get_partial_key_value(parsed, "sentiment"),
                "sentiment_reason": self.get_partial_key_value(parsed, "근거"),
                "keywords": self.get_partial_key_value(parsed, "키워드"),
                "expected_impact": self.get_partial_key_value(parsed, "예상"),
                "impact_duration": self.get_partial_key_value(parsed, "지속"),
            }

        except json.JSONDecodeError as e:
            print(f"❌ JSON 파싱 실패: {e}", file=sys.stderr)
            print(f"📤 받은 전체 응답:\n{response_text}", file=sys.stderr)
            return self.default_response("Gemini 응답 파싱 실패")

    def default_response(self, reason: str) -> Dict:
        return {
            "summary": "공시 분석 실패",
            "impact_score": 0.5,
            "sentiment": "중립",
            "sentiment_reason": reason,
            "keywords": [],
            "expected_impact": "보합",
            "impact_duration": "중기",
        }

    def analyze(self, disclosure_content: str, stock_name: str) -> Dict:
        """동기 분석 실행"""
        prompt = self.generate_prompt(disclosure_content, stock_name)

        try:
            
            command = [self.gemini_cmd_path, "--model", "gemini-2.5-flash"]
            result = subprocess.run(
                command,
                input=prompt,
                capture_output=True,
                text=True,
                encoding="utf-8",
                check=True
            )
            return self.parse_response(result.stdout)

        except subprocess.CalledProcessError as e:
            print(f"❌ Gemini CLI 오류 (Exit Code: {e.returncode})", file=sys.stderr)
            print(f"stdout:\n{e.stdout}", file=sys.stderr)
            print(f"stderr:\n{e.stderr}", file=sys.stderr)
            return self.default_response("Gemini 호출 오류")

        except Exception as e:
            print(f"❌ 예외 발생: {e}", file=sys.stderr)
            return self.default_response(str(e))

    async def analyze_async(self, disclosure_content: str, stock_name: str) -> Dict:
        """비동기 래퍼 (executor 사용)"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, lambda: self.analyze(disclosure_content, stock_name)
        )
