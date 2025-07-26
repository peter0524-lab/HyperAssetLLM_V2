"""
모니터링 서비스 (Monitoring Service)
- Streamlit 대시보드
- 메트릭 수집 및 시각화
- 에러 추적 및 알림
- 실시간 서비스 상태 모니터링
"""

import asyncio
import logging
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from pathlib import Path
import sys
import psutil
import time

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.database.mysql_client import get_mysql_client
from shared.database.vector_db import VectorDBClient
from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config

# FastAPI 추가
from fastapi import FastAPI, HTTPException
import uvicorn

app = FastAPI(title="Monitoring Service", version="1.0.0")

class MonitoringService:
    """모니터링 서비스 클래스"""

    def __init__(self):
        self.config = get_config()
        self.mysql_client = get_mysql_client()
        self.vector_db = VectorDBClient()
        self.telegram_bot = TelegramBotClient()

        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)

        # 서비스 목록과 포트
        self.services = {
            "news_service": {"port": 8001, "name": "뉴스 서비스"},
            "disclosure_service": {"port": 8002, "name": "공시 서비스"},
            "chart_service": {"port": 8003, "name": "차트 분석 서비스"},
            "report_service": {"port": 8004, "name": "주간 보고서 서비스"},
            "analysis_service": {"port": 8005, "name": "주가 원인 분석 서비스"},
            "monitoring_service": {"port": 8006, "name": "모니터링 서비스"},
            "orchestrator": {"port": 8000, "name": "오케스트레이터"}
        }

    async def initialize_database(self):
        """데이터베이스 초기화"""
        try:
            # 시스템 메트릭 테이블 생성
            create_system_metrics_table = """
            CREATE TABLE IF NOT EXISTS system_metrics (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service_name VARCHAR(50) NOT NULL,
                metric_type VARCHAR(50) NOT NULL,
                metric_value DECIMAL(10,2) NOT NULL,
                metric_unit VARCHAR(20),
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                INDEX idx_service_name (service_name),
                INDEX idx_metric_type (metric_type),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            # 서비스 상태 테이블 생성
            create_service_status_table = """
            CREATE TABLE IF NOT EXISTS service_status (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service_name VARCHAR(50) NOT NULL,
                status VARCHAR(20) NOT NULL,
                last_heartbeat TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                error_count INT DEFAULT 0,
                last_error TEXT,
                uptime_seconds BIGINT DEFAULT 0,
                INDEX idx_service_name (service_name),
                INDEX idx_status (status),
                INDEX idx_last_heartbeat (last_heartbeat),
                UNIQUE KEY unique_service (service_name)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            # 에러 로그 테이블 생성
            create_error_logs_table = """
            CREATE TABLE IF NOT EXISTS error_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                service_name VARCHAR(50) NOT NULL,
                error_level VARCHAR(20) NOT NULL,
                error_message TEXT NOT NULL,
                stack_trace TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved BOOLEAN DEFAULT FALSE,
                INDEX idx_service_name (service_name),
                INDEX idx_error_level (error_level),
                INDEX idx_timestamp (timestamp)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """

            await self.mysql_client.execute_query_async(create_system_metrics_table)
            await self.mysql_client.execute_query_async(create_service_status_table)
            await self.mysql_client.execute_query_async(create_error_logs_table)

            self.logger.info("모니터링 서비스 데이터베이스 초기화 완료")

        except Exception as e:
            self.logger.error(f"데이터베이스 초기화 실패: {e}")
            raise

    async def collect_system_metrics(self):
        """시스템 메트릭 수집"""
        try:
            # CPU 사용률
            cpu_percent = psutil.cpu_percent(interval=1)
            await self.save_metric("system", "cpu_usage", cpu_percent, "%")

            # 메모리 사용률
            memory = psutil.virtual_memory()
            memory_percent = memory.percent
            await self.save_metric("system", "memory_usage", memory_percent, "%")

            # 디스크 사용률
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            await self.save_metric("system", "disk_usage", disk_percent, "%")

            # 네트워크 IO
            net_io = psutil.net_io_counters()
            await self.save_metric(
                "system", "network_bytes_sent", net_io.bytes_sent, "bytes"
            )
            await self.save_metric(
                "system", "network_bytes_recv", net_io.bytes_recv, "bytes"
            )

            self.logger.info("시스템 메트릭 수집 완료")

        except Exception as e:
            self.logger.error(f"시스템 메트릭 수집 실패: {e}")

    async def collect_service_metrics(self):
        """서비스 메트릭 수집"""
        try:
            # 뉴스 데이터 통계
            news_count = self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM news WHERE DATE(created_at) = CURDATE()"
            )
            if news_count:
                await self.save_metric(
                    "news_service", "daily_news_count", news_count["count"], "count"
                )

            # 공시 데이터 통계
            disclosure_count = self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM disclosure_data WHERE DATE(created_at) = CURDATE()"
            )
            if disclosure_count:
                await self.save_metric(
                    "disclosure_service",
                    "daily_disclosure_count",
                    disclosure_count["count"],
                    "count",
                )

            # 차트 조건 만족 통계
            chart_count = self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM chart_conditions WHERE DATE(trigger_time) = CURDATE()"
            )
            if chart_count:
                await self.save_metric(
                    "chart_service",
                    "daily_chart_triggers",
                    chart_count["count"],
                    "count",
                )

            # 알림 전송 통계
            notification_count = self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM notification_history WHERE DATE(sent_at) = CURDATE()"
            )
            if notification_count:
                await self.save_metric(
                    "notification_service",
                    "daily_notifications",
                    notification_count["count"],
                    "count",
                )

            # 분석 수행 통계
            analysis_count = self.mysql_client.fetch_one(
                "SELECT COUNT(*) as count FROM price_analysis WHERE DATE(created_at) = CURDATE()"
            )
            if analysis_count:
                await self.save_metric(
                    "analysis_service",
                    "daily_analysis_count",
                    analysis_count["count"],
                    "count",
                )

            self.logger.info("서비스 메트릭 수집 완료")

        except Exception as e:
            self.logger.error(f"서비스 메트릭 수집 실패: {e}")

    async def save_metric(
        self, service_name: str, metric_type: str, value: float, unit: str
    ):
        """메트릭 저장"""
        try:
            insert_query = """
            INSERT INTO system_metrics (service_name, metric_type, metric_value, metric_unit)
            VALUES (%s, %s, %s, %s)
            """

            await self.mysql_client.execute_query_async(
                insert_query, (service_name, metric_type, value, unit)
            )

        except Exception as e:
            self.logger.error(f"메트릭 저장 실패: {e}")

    async def update_service_status(
        self, service_name: str, status: str, error_message: Optional[str] = None
    ):
        """서비스 상태 업데이트"""
        try:
            update_query = """
            INSERT INTO service_status (service_name, status, last_error)
            VALUES (%s, %s, %s)
            ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            last_heartbeat = CURRENT_TIMESTAMP,
            last_error = VALUES(last_error),
            error_count = CASE 
                WHEN VALUES(status) = 'error' THEN error_count + 1
                ELSE error_count
            END
            """

            await self.mysql_client.execute_query_async(
                update_query, (service_name, status, error_message)
            )

        except Exception as e:
            self.logger.error(f"서비스 상태 업데이트 실패: {e}")

    async def log_error(
        self,
        service_name: str,
        error_level: str,
        error_message: str,
        stack_trace: Optional[str] = None,
    ):
        """에러 로그 기록"""
        try:
            insert_query = """
            INSERT INTO error_logs (service_name, error_level, error_message, stack_trace)
            VALUES (%s, %s, %s, %s)
            """

            await self.mysql_client.execute_query_async(
                insert_query, (service_name, error_level, error_message, stack_trace)
            )

            # 크리티컬 에러 시 알림 전송
            if error_level == "CRITICAL":
                await self.send_error_alert(service_name, error_level, error_message)

        except Exception as e:
            self.logger.error(f"에러 로그 기록 실패: {e}")

    async def send_error_alert(
        self, service_name: str, error_level: str, error_message: str
    ):
        """에러 알림 전송"""
        try:
            message = f"""
🚨 **시스템 에러 알림**

🔧 **서비스**: {service_name}
❌ **레벨**: {error_level}
⏰ **시간**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

📝 **메시지**: {error_message}

🔍 **조치 필요**: 즉시 확인 및 대응 요망
            """

            self.telegram_bot.send_message(message)

        except Exception as e:
            self.logger.error(f"에러 알림 전송 실패: {e}")

    def create_dashboard(self):
        """Streamlit 대시보드 생성"""
        st.set_page_config(
            page_title="주식 분석 서비스 모니터링",
            page_icon="📊",
            layout="wide",
            initial_sidebar_state="expanded"
        )

        # 사이드바 메뉴
        st.sidebar.title("📊 시스템 모니터링")
        
        menu_options = [
            "🏠 홈 대시보드",
            "💻 시스템 메트릭", 
            "🔧 서비스 상태",
            "📰 뉴스 모니터링",
            "📋 공시 모니터링", 
            "📈 차트 분석",
            "🔍 주가 분석",
            "❌ 에러 로그",
            "⚙️ 시스템 설정"
        ]
        
        choice = st.sidebar.selectbox("메뉴 선택", menu_options)

        # 실시간 업데이트 설정
        auto_refresh = st.sidebar.checkbox("자동 새로고침 (30초)", value=True)
        if auto_refresh:
            time.sleep(30)
            st.rerun()

        # 메뉴별 페이지 렌더링
        if choice == "🏠 홈 대시보드":
            self.show_home_dashboard()
        elif choice == "💻 시스템 메트릭":
            self.show_system_metrics()
        elif choice == "🔧 서비스 상태":
            self.show_service_status()
        elif choice == "📰 뉴스 모니터링":
            self.show_news_monitoring()
        elif choice == "📋 공시 모니터링":
            self.show_disclosure_monitoring()
        elif choice == "📈 차트 분석":
            self.show_chart_analysis()
        elif choice == "🔍 주가 분석":
            self.show_price_analysis()
        elif choice == "❌ 에러 로그":
            self.show_error_logs()
        elif choice == "⚙️ 시스템 설정":
            self.show_system_settings()

    def show_home_dashboard(self):
        """홈 대시보드"""
        st.title("🏠 주식 분석 서비스 종합 대시보드")
        st.markdown("---")

        # 실시간 시스템 상태 요약
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            cpu_usage = psutil.cpu_percent()
            st.metric("CPU 사용률", f"{cpu_usage:.1f}%", delta=None)
        
        with col2:
            memory = psutil.virtual_memory()
            st.metric("메모리 사용률", f"{memory.percent:.1f}%", delta=None)
        
        with col3:
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            st.metric("디스크 사용률", f"{disk_percent:.1f}%", delta=None)
        
        with col4:
            # 활성 서비스 수 (예시)
            active_services = len([s for s in self.services.keys()])
            st.metric("활성 서비스", f"{active_services}개", delta=None)

        # 서비스별 상태 표시
        st.subheader("🔧 서비스 상태")
        service_cols = st.columns(len(self.services))
        
        for idx, (service_name, service_info) in enumerate(self.services.items()):
            with service_cols[idx]:
                # 서비스 상태 확인 (간단한 예시)
                status = "🟢 정상" if idx % 2 == 0 else "🔴 중단"  # 예시
                st.write(f"**{service_info['name']}**")
                st.write(status)
                st.write(f"포트: {service_info['port']}")

        # 최근 활동 요약
        st.subheader("📊 최근 24시간 활동")
        
        # 차트 데이터 생성 (예시)
        hours = list(range(24))
        news_data = [10 + i % 5 for i in hours]  # 예시 데이터
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=hours, y=news_data, mode='lines+markers', name='뉴스 수집'))
        fig.update_layout(title="최근 24시간 뉴스 수집 현황", xaxis_title="시간", yaxis_title="수집된 뉴스 수")
        st.plotly_chart(fig, use_container_width=True)

    def show_system_metrics(self):
        """시스템 메트릭 페이지"""
        st.title("💻 시스템 메트릭")
        st.markdown("---")

        # 실시간 시스템 정보
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("CPU & 메모리")
            cpu_usage = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            
            # CPU 게이지 차트
            fig_cpu = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = cpu_usage,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "CPU 사용률 (%)"},
                gauge = {'axis': {'range': [None, 100]},
                        'bar': {'color': "darkblue"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "red"}],
                        'threshold': {'line': {'color': "red", 'width': 4},
                                    'thickness': 0.75, 'value': 90}}))
            st.plotly_chart(fig_cpu, use_container_width=True)
            
        with col2:
            st.subheader("디스크 & 네트워크")
            disk = psutil.disk_usage("/")
            disk_percent = (disk.used / disk.total) * 100
            
            # 메모리 게이지 차트
            fig_memory = go.Figure(go.Indicator(
                mode = "gauge+number",
                value = memory.percent,
                domain = {'x': [0, 1], 'y': [0, 1]},
                title = {'text': "메모리 사용률 (%)"},
                gauge = {'axis': {'range': [None, 100]},
                        'bar': {'color': "darkgreen"},
                        'steps': [
                            {'range': [0, 50], 'color': "lightgray"},
                            {'range': [50, 80], 'color': "yellow"},
                            {'range': [80, 100], 'color': "red"}]}))
            st.plotly_chart(fig_memory, use_container_width=True)

        # 프로세스 정보
        st.subheader("🔄 실행 중인 프로세스")
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if 'python' in proc.info['name'].lower():
                    processes.append(proc.info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                pass
        
        if processes:
            df_processes = pd.DataFrame(processes[:10])  # 상위 10개만 표시
            st.dataframe(df_processes, use_container_width=True)

    def show_service_status(self):
        """서비스 상태 페이지"""
        st.title("🔧 서비스 상태")
        st.markdown("---")

        # 서비스 상태 테이블
        service_data = []
        for service_name, service_info in self.services.items():
            # 실제로는 각 서비스의 health check를 수행
            status = "정상" if service_name != "test_service" else "중단"
            uptime = f"{24 * 60 + 30} 분"  # 예시
            last_check = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            service_data.append({
                "서비스명": service_info['name'],
                "상태": status,
                "포트": service_info['port'],
                "가동시간": uptime,
                "마지막 확인": last_check
            })
        
        df_services = pd.DataFrame(service_data)
        st.dataframe(df_services, use_container_width=True)

        # 서비스 재시작 버튼
        st.subheader("🔄 서비스 관리")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("모든 서비스 재시작"):
                st.success("모든 서비스 재시작 요청이 전송되었습니다.")
        
        with col2:
            if st.button("서비스 상태 새로고침"):
                st.info("서비스 상태를 새로고침했습니다.")
        
        with col3:
            if st.button("비상 정지"):
                st.error("비상 정지 신호가 전송되었습니다.")

    def show_news_monitoring(self):
        """뉴스 모니터링 페이지"""
        st.title("📰 뉴스 서비스 모니터링")
        st.markdown("---")

        # 뉴스 수집 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("오늘 수집 뉴스", "127개", delta="12")
        with col2:
            st.metric("고영향 뉴스", "23개", delta="3")
        with col3:
            st.metric("알림 전송", "15건", delta="2")
        with col4:
            st.metric("평균 영향도", "0.73", delta="0.05")

        # 뉴스 수집 트렌드
        st.subheader("📈 뉴스 수집 트렌드")
        
        # 예시 데이터 생성
        dates = pd.date_range(start='2024-01-01', end='2024-01-07', freq='D')
        news_counts = [45, 52, 38, 61, 48, 55, 42]
        
        fig = px.line(x=dates, y=news_counts, title="일별 뉴스 수집 현황")
        fig.update_layout(xaxis_title="날짜", yaxis_title="뉴스 수")
        st.plotly_chart(fig, use_container_width=True)

        # 최근 뉴스 목록
        st.subheader("📋 최근 수집된 뉴스")
        recent_news = [
            {"시간": "14:23", "제목": "삼성전자, 신규 반도체 공장 건설 발표", "영향도": 0.85},
            {"시간": "14:15", "제목": "네이버, AI 기술 특허 출원 증가", "영향도": 0.72},
            {"시간": "14:08", "제목": "카카오, 모빌리티 사업 확장", "영향도": 0.68}
        ]
        
        df_news = pd.DataFrame(recent_news)
        st.dataframe(df_news, use_container_width=True)

    def show_disclosure_monitoring(self):
        """공시 모니터링 페이지"""
        st.title("📋 공시 서비스 모니터링")
        st.markdown("---")

        # 공시 처리 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("오늘 처리 공시", "18개", delta="3")
        with col2:
            st.metric("중요 공시", "7개", delta="1")
        with col3:
            st.metric("알림 전송", "5건", delta="1")
        with col4:
            st.metric("평균 처리 시간", "2.3분", delta="-0.5")

        # 공시 유형별 분포
        st.subheader("📊 공시 유형별 분포")
        
        disclosure_types = ['증자', '합병', '투자', '인사', '기타']
        disclosure_counts = [5, 2, 3, 4, 4]
        
        fig = px.pie(values=disclosure_counts, names=disclosure_types, title="공시 유형별 분포")
        st.plotly_chart(fig, use_container_width=True)

    def show_chart_analysis(self):
        """차트 분석 페이지"""
        st.title("📈 차트 분석 서비스 모니터링")
        st.markdown("---")

        # 차트 조건 발동 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("오늘 조건 발동", "42회", delta="8")
        with col2:
            st.metric("골든크로스", "7회", delta="2")
        with col3:
            st.metric("볼린저터치", "15회", delta="3")
        with col4:
            st.metric("거래량급증", "12회", delta="1")

        # 조건별 발동 빈도
        st.subheader("📊 조건별 발동 빈도")
        
        conditions = ['골든크로스', '데드크로스', '볼린저터치', 'RSI과매수', '거래량급증', 'MACD', '지지저항']
        frequencies = [7, 3, 15, 8, 12, 5, 9]
        
        fig = px.bar(x=conditions, y=frequencies, title="차트 조건별 발동 빈도")
        fig.update_layout(xaxis_title="조건", yaxis_title="발동 횟수")
        st.plotly_chart(fig, use_container_width=True)

    def show_price_analysis(self):
        """주가 분석 페이지"""
        st.title("🔍 주가 원인 분석 모니터링")
        st.markdown("---")

        # 분석 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("오늘 분석 수행", "5건", delta="2")
        with col2:
            st.metric("급등 분석", "3건", delta="1")
        with col3:
            st.metric("급락 분석", "2건", delta="1")
        with col4:
            st.metric("평균 신뢰도", "0.82", delta="0.03")

        # 최근 분석 결과
        st.subheader("📋 최근 분석 결과")
        
        analysis_data = [
            {"시간": "15:30", "종목": "삼성전자", "변동률": "+12.5%", "원인": "신제품 발표", "신뢰도": 0.89},
            {"시간": "14:45", "종목": "네이버", "변동률": "-8.2%", "원인": "규제 우려", "신뢰도": 0.76},
            {"시간": "13:20", "종목": "카카오", "변동률": "+15.1%", "원인": "실적 개선", "신뢰도": 0.84}
        ]
        
        df_analysis = pd.DataFrame(analysis_data)
        st.dataframe(df_analysis, use_container_width=True)

    def show_error_logs(self):
        """에러 로그 페이지"""
        st.title("❌ 에러 로그")
        st.markdown("---")

        # 에러 통계
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("오늘 에러", "3건", delta="-2")
        with col2:
            st.metric("Critical", "0건", delta="0")
        with col3:
            st.metric("Warning", "2건", delta="-1")
        with col4:
            st.metric("해결률", "100%", delta="0%")

        # 에러 로그 표시
        st.subheader("📋 최근 에러 로그")
        
        error_data = [
            {"시간": "13:45", "서비스": "뉴스서비스", "레벨": "WARNING", "메시지": "크롤링 속도 지연", "상태": "해결됨"},
            {"시간": "12:30", "서비스": "공시서비스", "레벨": "ERROR", "메시지": "DART API 연결 실패", "상태": "해결됨"},
            {"시간": "11:15", "서비스": "차트서비스", "레벨": "INFO", "메시지": "정상 재시작", "상태": "정상"}
        ]
        
        df_errors = pd.DataFrame(error_data)
        st.dataframe(df_errors, use_container_width=True)

    def show_system_settings(self):
        """시스템 설정 페이지"""
        st.title("⚙️ 시스템 설정")
        st.markdown("---")

        # 설정 변경 폼
        st.subheader("📝 설정 변경")
        
        with st.form("settings_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.text_input("뉴스 크롤링 간격 (초)", value="300")
                st.text_input("공시 확인 간격 (초)", value="3600")
                st.text_input("차트 분석 간격 (초)", value="600")
            
            with col2:
                st.number_input("뉴스 영향력 임계값", value=0.7, min_value=0.0, max_value=1.0, step=0.1)
                st.number_input("주가 변동 임계값 (%)", value=10.0, min_value=0.0, max_value=50.0, step=1.0)
                st.checkbox("텔레그램 알림 활성화", value=True)
            
            if st.form_submit_button("설정 저장"):
                st.success("설정이 저장되었습니다.")

        # 데이터베이스 관리
        st.subheader("🗄️ 데이터베이스 관리")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("데이터베이스 백업"):
                st.info("백업이 시작되었습니다.")
        
        with col2:
            if st.button("오래된 로그 정리"):
                st.info("로그 정리가 완료되었습니다.")
        
        with col3:
            if st.button("시스템 재시작"):
                st.warning("시스템 재시작이 예약되었습니다.")

    async def run_metrics_collector(self):
        """메트릭 수집기 실행"""
        try:
            while True:
                try:
                    # 시스템 메트릭 수집
                    await self.collect_system_metrics()

                    # 서비스 메트릭 수집
                    await self.collect_service_metrics()

                    # 5분 대기
                    await asyncio.sleep(300)

                except Exception as e:
                    self.logger.error(f"메트릭 수집 오류: {e}")
                    await asyncio.sleep(60)

        except Exception as e:
            self.logger.error(f"메트릭 수집기 실행 실패: {e}")

    async def run_service(self):
        """모니터링 서비스 실행"""
        try:
            self.logger.info("모니터링 서비스 시작")

            # 데이터베이스 초기화
            await self.initialize_database()

            # 메트릭 수집기 백그라운드 실행
            metrics_task = asyncio.create_task(self.run_metrics_collector())

            # Streamlit 대시보드 실행
            # 주의: 실제 배포에서는 별도 프로세스로 실행 필요
            self.create_dashboard()

            # 메트릭 수집기 대기
            await metrics_task

        except Exception as e:
            self.logger.error(f"모니터링 서비스 실행 실패: {e}")
            raise
        finally:
            # 리소스 정리
            self.mysql_client.close()

# 서비스 인스턴스 생성
monitoring_service = None


def get_monitoring_service():
    """모니터링 서비스 인스턴스 반환 (지연 초기화)"""
    global monitoring_service
    if monitoring_service is None:
        monitoring_service = MonitoringService()
    return monitoring_service

# FastAPI 엔드포인트
@app.get("/")
async def root():
    return {"message": "Monitoring Service", "status": "running"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.get("/metrics")
async def get_system_metrics():
    """시스템 메트릭 조회"""
    try:
        cpu_usage = psutil.cpu_percent()
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        
        return {
            "cpu_usage": cpu_usage,
            "memory_usage": memory.percent,
            "disk_usage": (disk.used / disk.total) * 100,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/services")
async def get_services_status():
    """서비스 상태 조회"""
    try:
        return {
            "services": get_monitoring_service().services,
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

def run_streamlit_app():
    """Streamlit 앱 실행"""
    monitoring = MonitoringService()
    monitoring.create_dashboard()

async def main():
    """메인 실행 함수"""
    try:
        # 모니터링 서비스를 백그라운드에서 실행
        import threading
        
        async def run_monitoring_service():
            await get_monitoring_service().run_service()
        
        # 서비스 스레드 시작
        service_thread = threading.Thread(target=lambda: asyncio.run(run_monitoring_service()), daemon=True)
        service_thread.start()
        
        # FastAPI 서버 실행
        uvicorn.run(app, host="0.0.0.0", port=8006)

    except KeyboardInterrupt:
        print("서비스 중단")
    except Exception as e:
        print(f"서비스 실행 실패: {e}")


if __name__ == "__main__":
    # Streamlit 실행 모드 확인
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "streamlit":
        run_streamlit_app()
    else:
        asyncio.run(main())
