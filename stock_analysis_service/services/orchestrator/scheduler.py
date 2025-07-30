"""
단순 체크 신호 스케줄러 (Simple Check Signal Scheduler)
- 10분마다 모든 서비스에 "체크해봐" 신호 전송
- 각 서비스가 독립적으로 실행 시간 판단
- 진정한 분산형 마이크로서비스 패턴
- 조건 미충족 시 정기 알림 발송
"""

import asyncio
import aiohttp
import logging
from datetime import datetime, time
from typing import Dict, List
from pathlib import Path
import sys

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.append(str(project_root))

from shared.apis.telegram_api import TelegramBotClient
from config.env_local import get_config

class SimpleCheckScheduler:
    """단순 체크 신호 스케줄러"""
    
    def __init__(self):
        self.config = get_config()
        self.telegram_bot = TelegramBotClient()
        
        # 로깅 설정
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        )
        self.logger = logging.getLogger(__name__)
        
        # 서비스 목록 및 포트 (체크 신호 발송 대상)
        # Note: user_service는 프론트엔드 요청 기반 API이므로 스케줄링 불필요
        self.services = {
            "news_service": {"port": 8001, "enabled": True, "type": "hourly"},
            "disclosure_service": {"port": 8002, "enabled": True, "type": "hourly"}, 
            "chart_service": {"port": 8003, "enabled": True, "type": "market_close"},
            "report_service": {"port": 8004, "enabled": True, "type": "weekly"},
            "flow_analysis_service": {"port": 8010, "enabled": True, "type": "market_close"}
        }
        
        # 스케줄러 상태
        self.is_running = False
        
        # 마지막 알림 시간 추적
        self.last_notifications = {
            "news_service": None,
            "disclosure_service": None,
            "chart_service": None,
            "flow_analysis_service": None
        }
        
        # 장 마감 시간 (한국 시간)
        self.market_close_time = time(15, 30)  # 15:30
        
    def is_market_close_time(self) -> bool:
        """현재 시간이 장 마감 시간인지 확인"""
        now = datetime.now()
        return now.time() >= self.market_close_time and now.time() < time(16, 0)
    
    def should_send_hourly_notification(self, service_name: str) -> bool:
        """1시간마다 알림을 보내야 하는지 확인"""
        now = datetime.now()
        last_notification = self.last_notifications.get(service_name)
        
        if last_notification is None:
            return True
        
        # 마지막 알림으로부터 1시간이 지났는지 확인
        time_diff = (now - last_notification).total_seconds()
        return time_diff >= 3600  # 1시간 = 3600초
    
    async def send_no_event_notification(self, service_name: str, service_type: str):
        """조건을 만족하지 않았을 때 알림 발송"""
        try:
            now = datetime.now()
            
            if service_type == "hourly":
                # 1시간마다 알림
                if not self.should_send_hourly_notification(service_name):
                    return
                
                message = f"📢 **{service_name.replace('_', ' ').title()} 정기 알림**\n"
                message += f"⏰ 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                message += f"📋 상태: 중요 {service_name.replace('_', ' ').title()}가 발생하지 않았습니다\n"
                message += f"🔄 다음 체크: 1시간 후"
                
                self.last_notifications[service_name] = now
                
            elif service_type == "market_close":
                # 장 마감 시간 알림
                if not self.is_market_close_time():
                    return
                
                message = f"📢 **{service_name.replace('_', ' ').title()} 장 마감 알림**\n"
                message += f"⏰ 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}\n"
                message += f"📋 상태: 중요 {service_name.replace('_', ' ').title()} 조건이 확인되지 않았습니다\n"
                message += f"🔄 다음 체크: 내일 장 마감 시간"
                
                self.last_notifications[service_name] = now
            
            # 텔레그램 알림 발송
            await self.telegram_bot.send_message_async(message)
            self.logger.info(f"✅ {service_name} 조건 미충족 알림 발송 완료")
            
        except Exception as e:
            self.logger.error(f"❌ {service_name} 조건 미충족 알림 발송 실패: {e}")

    async def send_no_event_notifications(self):
        """조건을 만족하지 않은 서비스들에 대한 알림 발송"""
        try:
            for service_name, config in self.services.items():
                if not config["enabled"]:
                    continue
                
                service_type = config.get("type", "hourly")
                
                # 뉴스/공시 서비스: 1시간마다 알림
                if service_type == "hourly":
                    await self.send_no_event_notification(service_name, "hourly")
                
                # 차트/수급 서비스: 장 마감 시간 알림
                elif service_type == "market_close":
                    await self.send_no_event_notification(service_name, "market_close")
                    
        except Exception as e:
            self.logger.error(f"❌ 조건 미충족 알림 발송 실패: {e}")

    async def send_check_signal(self, service_name: str, port: int) -> Dict:
        """개별 서비스에 체크 신호 전송"""
        try:
            url = f"http://localhost:{port}/check-schedule"
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        result = await response.json()
                        if result.get("executed", False):
                            self.logger.info(f"✅ {service_name}: {result.get('message', '실행됨')}")
                        else:
                            self.logger.debug(f"⏭️ {service_name}: {result.get('message', '실행 시간 아님')}")
                        return result
                    else:
                        self.logger.warning(f"⚠️ {service_name}: HTTP {response.status}")
                        return {"executed": False, "error": f"HTTP {response.status}"}
                        
        except asyncio.TimeoutError:
            self.logger.warning(f"⏰ {service_name}: 체크 신호 타임아웃")
            return {"executed": False, "error": "timeout"}
        except Exception as e:
            self.logger.error(f"❌ {service_name}: 체크 신호 실패 - {e}")
            return {"executed": False, "error": str(e)}
    
    async def send_all_check_signals(self):
        """모든 서비스에 동시 체크 신호 전송"""
        try:
            self.logger.info("📡 모든 서비스에 체크 신호 전송 시작...")
            
            # 모든 활성화된 서비스에 동시 신호 전송
            tasks = []
            for service_name, config in self.services.items():
                if config["enabled"]:
                    task = self.send_check_signal(service_name, config["port"])
                    tasks.append((service_name, task))
            
            # 동시 실행
            results = {}
            if tasks:
                task_results = await asyncio.gather(
                    *[task for _, task in tasks], 
                    return_exceptions=True
                )
                
                # 결과 정리
                executed_services = []
                for i, (service_name, _) in enumerate(tasks):
                    result = task_results[i]
                    results[service_name] = result
                    
                    if isinstance(result, dict) and result.get("executed", False):
                        executed_services.append(service_name)
                
                # 실행된 서비스가 있으면 로그
                if executed_services:
                    self.logger.info(f"🚀 실행된 서비스: {', '.join(executed_services)}")
                else:
                    self.logger.debug("😴 모든 서비스가 대기 상태")
                    
                    # 조건 미충족 알림 발송
                    await self.send_no_event_notifications()
            
            return results
            
        except Exception as e:
            self.logger.error(f"❌ 체크 신호 전송 실패: {e}")
            return {}
    
    async def health_check_services(self):
        """서비스 헬스체크 (선택적)"""
        try:
            unhealthy_services = []
            
            for service_name, config in self.services.items():
                if not config["enabled"]:
                    continue
                    
                try:
                    url = f"http://localhost:{config['port']}/health"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                            if response.status != 200:
                                unhealthy_services.append(service_name)
                except:
                    unhealthy_services.append(service_name)
            
            if unhealthy_services:
                self.logger.warning(f"⚠️ 비정상 서비스: {', '.join(unhealthy_services)}")
            else:
                self.logger.debug("✅ 모든 서비스 정상")
            
        except Exception as e:
            self.logger.error(f"❌ 헬스체크 실패: {e}")
    
    async def start_scheduler(self):
        """단순 체크 신호 스케줄러 시작"""
        try:
            self.logger.info("🚀 단순 체크 신호 스케줄러 시작")
            self.logger.info("📋 관리 대상 서비스:")
            for service_name, config in self.services.items():
                status = "활성" if config["enabled"] else "비활성"
                notification_type = config.get("type", "hourly")
                self.logger.info(f"   • {service_name} (포트: {config['port']}) - {status} - 알림: {notification_type}")
            
            self.is_running = True
            
            # 시작 알림
            await self.telegram_bot.send_message_async(
                "🚀 **단순 체크 신호 스케줄러 시작**\n"
                "• 10분마다 모든 서비스에 체크 신호 전송\n"
                "• 각 서비스가 독립적으로 실행 시간 판단\n"
                "• 조건 미충족 시 정기 알림 발송"
            )
            
            # 메인 루프: 10분마다 체크 신호 전송
            while self.is_running:
                try:
                    # 체크 신호 전송
                    await self.send_all_check_signals()
                    
                    # 30분마다 헬스체크 (선택적)
                    current_minute = datetime.now().minute
                    if current_minute % 30 == 0:
                        await self.health_check_services()
                    
                    # 10분 대기
                    self.logger.debug("⏱️ 10분 대기 중...")
                    await asyncio.sleep(600)  # 10분 = 600초
                    
                except asyncio.CancelledError:
                    self.logger.info("스케줄러 중단 요청")
                    break
                except Exception as e:
                    self.logger.error(f"❌ 스케줄러 루프 오류: {e}")
                    await asyncio.sleep(60)  # 오류 시 1분 대기 후 재시도
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 시작 실패: {e}")
            raise
        finally:
            await self.stop_scheduler()
    
    async def stop_scheduler(self):
        """스케줄러 정지"""
        try:
            self.logger.info("🛑 스케줄러 정지 중...")
            self.is_running = False
            
            # 종료 알림
            await self.telegram_bot.send_message_async("🛑 단순 체크 신호 스케줄러가 정지되었습니다.")
            
        except Exception as e:
            self.logger.error(f"❌ 스케줄러 정지 실패: {e}")
    
    def get_status(self) -> Dict:
        """스케줄러 상태 조회"""
        return {
            "is_running": self.is_running,
            "current_time": datetime.now().isoformat(),
            "services": self.services,
            "check_interval": "10분마다",
            "architecture": "분산형 체크 신호 방식",
            "notification_types": {
                "hourly": "1시간마다 조건 미충족 알림",
                "market_close": "장 마감 시간 조건 미충족 알림"
            }
            }

async def main():
    """메인 실행 함수"""
    try:
        scheduler = SimpleCheckScheduler()
        
        # 스케줄러 시작
        await scheduler.start_scheduler()
            
    except KeyboardInterrupt:
        print("스케줄러 중단")
    except Exception as e:
        print(f"스케줄러 실행 실패: {e}")

if __name__ == "__main__":
    asyncio.run(main()) 