import asyncio
import time
import re
import os
from datetime import datetime
from io import BytesIO
import aiohttp # For async HTTP requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from urllib.parse import unquote, urlparse, parse_qs
from webdriver_manager.chrome import ChromeDriverManager
from unstructured.partition.pdf import partition_pdf

# from unstructured.partition.pdf import partition_pdf  # 임시 주석처리
import logging

# Configure logging
logger = logging.getLogger(__name__)

class ResearchCrawler:
    def __init__(self):
        # Initialize any necessary components, e.g., WebDriver options
        self.options = webdriver.ChromeOptions()
        self.options.add_argument("--headless") # Run in headless mode
        self.options.add_argument("--no-sandbox")
        self.options.add_argument("--disable-dev-shm-usage")
        # ChromeDriverManager().install() is a synchronous operation,
        # so it's fine to call it in __init__ or wrap it in to_thread if __init__ itself is async.
        # For simplicity, keeping it here as it's typically a one-time setup.
        self.service = Service(ChromeDriverManager().install())

    @staticmethod
    async def _extract_filtered_korean_elements_first_page_from_url(pdf_url: str) -> tuple[str, list[str]]:
        """
        PDF 링크에서 첫 페이지의 필터링된 한글 요소를 비동기적으로 추출합니다.
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer": "https://m.stock.naver.com/"
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(pdf_url, headers=headers, timeout=30) as response:
                    if response.status != 200:
                        logger.error(f"❌ PDF 다운로드 실패: {pdf_url}, 상태 코드: {response.status}")
                        return "", []

                    pdf_content = await response.read()
                    pdf_file = BytesIO(pdf_content)
                    logger.info(f"📥 HTTP 상태 코드: {response.status}")
                    logger.info(f"📎 응답 Content-Type: {response.headers.get('Content-Type')}")
                    logger.info(f"📄 PDF 바이트 크기: {len(pdf_content)} bytes")

            # 임시로 PDF 파싱 기능 비활성화
            elements = await asyncio.to_thread(
                partition_pdf,
                file=pdf_file,
                filename=None,
                languages=["ko"],
                strategy="fast",
                detect_languages=False,
                extract_images_in_pdf=False,
                include_page_breaks=True,
                hi_nr_of_pages=1
            )
            

            extracted_text_elements = []
            korean_pattern = re.compile('[가-힣]+')

            logger.info("--- unstructured 1페이지 필터링된 한글 포함 요소 추출 결과 ---")
            if not elements:
                logger.warning("1페이지에서 추출된 요소가 없습니다.")
                return "", []

            for el in elements:
                if el.category == "PageBreak":
                    break
                if el.category in ["Title", "NarrativeText", "UncategorizedText"] and korean_pattern.search(el.text):
                    extracted_text_elements.append(el.text)

            if extracted_text_elements:
                full_extracted_text = "\n".join(extracted_text_elements)
                logger.info(f"추출된 텍스트 (일부): {full_extracted_text[:200]}...")
            else:
                full_extracted_text = ""
                logger.warning("지정된 카테고리에서 한글 포함 요소를 찾지 못했습니다.")

            return full_extracted_text, extracted_text_elements
        except aiohttp.ClientError as e:
            logger.error(f"PDF 다운로드 중 네트워크 오류 (aiohttp): {e}")
            return "", []
        except Exception as e:
            logger.error(f"PDF 처리 중 오류 발생: {e}")
            return "", []

    async def get_preprocessed_text_for_stock(self, stock_code: str) -> str:
        """
        종목 코드를 기반으로 최신 리서치 PDF를 비동기적으로 크롤링하고 전처리된 텍스트를 반환합니다.
        """
        url = f"https://m.stock.naver.com/domestic/stock/{stock_code}/research"
        
        # Selenium operations are synchronous and I/O-bound (interacting with browser).
        # Wrap the entire Selenium block in asyncio.to_thread to make it non-blocking.
        def _sync_selenium_crawl():
            driver = None
            try:
                driver = webdriver.Chrome(service=self.service, options=self.options)
                logger.info(f"🔍 URL 접속: {url}")
                driver.get(url)

                logger.info("⏳ 요소 로딩 대기 중...")
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "li.ResearchList_item__suwvv"))
                )
                logger.info("✅ 요소 로딩 완료!")

                spans = driver.find_elements(By.CLASS_NAME, "Vitem_desc__EbOC4")
                date_regex = re.compile(r"\d{4}\.\d{2}\.\d{2}")
                date_elements = [(span, span.text.strip()) for span in spans if date_regex.fullmatch(span.text.strip())]

                if not date_elements:
                    logger.warning("❌ 날짜 형식 텍스트를 찾지 못함")
                    return ""

                date_elements.sort(key=lambda x: datetime.strptime(x[1], "%Y.%m.%d"), reverse=True)
                latest_span = date_elements[0][0]
                logger.info(f"✅ 최신 날짜 리서치: {latest_span.text}")

                clickable = latest_span.find_element(By.XPATH, "./ancestor::a")
                clickable.click()
                time.sleep(2) # Use time.sleep here as it's within a separate thread
                logger.info("✅ 최신 리서치 클릭 완료")

                detail_url = driver.current_url
                logger.info(f"📄 이동한 상세 리포트 URL: {detail_url}")

                # 🔗 PDF 링크 찾기
                pdf_button = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "ResearchContent_link__zeiGC"))
                )
                pdf_url = pdf_button.get_attribute("href")
                logger.info(f"📎 PDF 다운로드 링크: {pdf_url}")
                
                # 진짜 다운로드 가능한 PDF 원본 URL 추출
                parsed = urlparse(pdf_url)
                query_params = parse_qs(parsed.query)
                real_pdf_url = unquote(query_params.get("url", [""])[0])

                logger.info(f"📥 진짜 PDF 원본 링크: {real_pdf_url}")
                return real_pdf_url
            except Exception as e:
                logger.error(f"Selenium 크롤링 중 오류 발생: {e}")
                return ""
            finally:
                if driver:
                    driver.quit()

        real_pdf_url = await asyncio.to_thread(_sync_selenium_crawl)
        if not real_pdf_url:
            return ""

        # 🧠 전처리 실행 (already async)
        filtered_text, elements = await self._extract_filtered_korean_elements_first_page_from_url(real_pdf_url)

        logger.info(f"\n🔹 최종 추출된 텍스트 (일부) 🔹\n{filtered_text[50:250]}...")
        logger.info(f"\n총 추출된 요소 수: {len(elements)}")

        return filtered_text
