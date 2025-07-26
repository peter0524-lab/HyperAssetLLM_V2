

import json
import re
import subprocess
import sys

def generate_prompt(disclosure_content: str, stock_name: str) -> str:
    """Gemini에게 보낼 프롬프트를 생성합니다."""
    prompt = f"""
    당신은 주식 투자 전문가입니다. 다음 공시가 {stock_name} 주식에 미치는 영향을 분석해주세요.

    공시 내용:
    {disclosure_content}

    다음 분석 결과항목을 제공해주세요:

    1. summary (공시 요약, 3줄 이내):
    2. impact_score (영향도 점수, 0-1 사이, 0: 매우 부정적, 0.5: 중립, 1: 매우 긍정적):
    3. sentiment (긍정/부정/중립 판단):
    4. sentiment_reason (판단 근거):
    5. keywords (주요 키워드, 리스트 형태):
    6. expected_impact (예상 주가 영향, 상승/하락/보합):
    7. impact_duration (영향 지속 시간, 단기/중기/장기):

    **🔒다음을 명심할것** 반드시 아래 JSON 형식에 맞춰 출력하고, **다른 문장 없이 오직 단 하나의 JSON 객체만 반환하세요.**

    {{
        "summary": "...",
        "impact_score": 0.0,
        "sentiment": "...",
        "sentiment_reason": "...",
        "keywords": ["...", "..."],
        "expected_impact": "...",
        "impact_duration": "..."
    }}
    """
    return prompt

def parse_response(response_text: str) -> dict:
    """Gemini의 응답(JSON 텍스트)을 파싱합니다."""
    try:
        match = re.search(r"\{.*\}", response_text, re.DOTALL)
        if not match:
            raise json.JSONDecodeError("JSON 객체를 찾을 수 없습니다.", response_text, 0)
        
        json_str = match.group(0)
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"❌ JSON 파싱 실패: {e}", file=sys.stderr)
        print(f"📤 받은 전체 응답:\n{response_text}", file=sys.stderr)
        # 실패 시 기본값 반환
        return {
            "summary": "응답 파싱 실패", "impact_score": 0.5, "sentiment": "중립",
            "sentiment_reason": "Gemini 응답 형식이 올바르지 않습니다.", "keywords": [],
            "expected_impact": "보합", "impact_duration": "알 수 없음",
        }

def analyze_disclosure_with_gemini(disclosure_content: str, stock_name: str) -> dict:
    """
    Gemini CLI를 호출하여 공시 분석을 수행하고 결과를 dict로 반환합니다.
    """
    # 1. Gemini에 전달할 프롬프트 생성
    prompt = generate_prompt(disclosure_content, stock_name)

    # 2. Gemini CLI 실행 명령어 준비
    # ❗ 중요: 아래는 'where gemini' 명령으로 찾은 절대 경로입니다.
    command = ['C:/Users/User/AppData/Roaming/npm/gemini.cmd', prompt]

    try:
        print("🚀 Gemini API 호출 중...")
        # 3. subprocess를 통해 Gemini CLI 실행 및 결과 캡처
        # ❗ 프롬프트를 인자가 아닌 표준 입력(stdin)으로 전달합니다.
        command = ['C:/Users/User/AppData/Roaming/npm/gemini.cmd', '--model', 'gemini-2.5-flash']
        result = subprocess.run(
            command,
            input=prompt, # 프롬프트를 stdin으로 전달
            capture_output=True,
            text=True,
            check=True,  # 오류 발생 시 예외를 던짐
            encoding='utf-8'
        )
        
        # 4. Gemini의 응답(stdout)을 파싱
        print("✅ 호출 성공. 응답 파싱 중...")
        return parse_response(result.stdout)

    except FileNotFoundError:
        print(f"❌ 오류: '{command[0]}' 명령을 찾을 수 없습니다.", file=sys.stderr)
        print("❗ 'command' 변수의 실행 파일 경로를 올바르게 수정해주세요.", file=sys.stderr)
        return {}
    except subprocess.CalledProcessError as e:
        print(f"❌ Gemini CLI 실행 중 오류 발생 (Exit Code: {e.returncode})", file=sys.stderr)
        print(f"   - Stderr: {e.stderr}", file=sys.stderr)
        return {}
    except Exception as e:
        print(f"❌ 예상치 못한 오류 발생: {e}", file=sys.stderr)
        return {}


# --- 사용 예시 ---
if __name__ == "__main__":
    # 분석할 공시 내용
    disclosure = "삼성전자는 2025년 2분기 실적 발표에서 영업이익이 전년 대비 30% 증가했다고 공시했습니다."
    stock_name = "삼성전자"

    # API처럼 함수를 호출하여 결과 받기
    analysis_result = analyze_disclosure_with_gemini(disclosure, stock_name)

    if analysis_result:
        import pprint
        print("\n--- 최종 분석 결과 ---")
        pprint.pprint(analysis_result)
        print("----------------------")

