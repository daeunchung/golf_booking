#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메이저골프아카데미 자동 예약 프로그램
Mac ARM64 (M1/M2/M3) 완벽 지원 버전
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import schedule
import time
from datetime import datetime, timedelta
import logging
import json
import os
import sys
import platform
import subprocess

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('golf_booking.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class GolfBookingBot:
    def __init__(self, config):
        self.config = config
        self.driver = None
        self.wait = None
        
    def setup_driver(self):
        """Chrome 드라이버 설정 (Mac ARM64 완벽 지원)"""
        try:
            chrome_options = Options()
            
            # 헤드리스 모드
            if self.config.get('headless', False):
                chrome_options.add_argument('--headless=new')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
            
            driver_initialized = False
            
            # Mac ARM64 감지
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
            
            if is_mac_arm:
                logger.info("🍎 Mac ARM64 (M1/M2/M3) 감지됨")
            
            # 방법 1: webdriver-manager 사용 (Mac ARM64 개선)
            try:
                logger.info("방법 1: webdriver-manager로 ChromeDriver 설치 시도...")
                from webdriver_manager.chrome import ChromeDriverManager
                from webdriver_manager.core.os_manager import ChromeType
                
                # Mac ARM64용 특별 처리
                if is_mac_arm:
                    logger.info("Mac ARM64용 ChromeDriver 다운로드 중...")
                    driver_path = ChromeDriverManager().install()
                    
                    # 올바른 chromedriver 파일 찾기
                    import glob
                    driver_dir = os.path.dirname(driver_path)
                    
                    # chromedriver-mac-arm64 폴더 안의 실제 chromedriver 찾기
                    possible_paths = [
                        os.path.join(driver_dir, 'chromedriver-mac-arm64', 'chromedriver'),
                        os.path.join(driver_dir, 'chromedriver'),
                        driver_path
                    ]
                    
                    actual_driver_path = None
                    for path in possible_paths:
                        if os.path.exists(path) and os.path.isfile(path):
                            # 실행 권한 확인 및 부여
                            if not os.access(path, os.X_OK):
                                os.chmod(path, 0o755)
                                logger.info(f"실행 권한 부여: {path}")
                            actual_driver_path = path
                            break
                    
                    if actual_driver_path:
                        logger.info(f"✅ ChromeDriver 경로: {actual_driver_path}")
                        service = Service(actual_driver_path)
                    else:
                        logger.warning("chromedriver 실행 파일을 찾을 수 없음")
                        raise Exception("ChromeDriver not found")
                else:
                    driver_path = ChromeDriverManager().install()
                    service = Service(driver_path)
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                driver_initialized = True
                logger.info("✅ webdriver-manager로 성공!")
                
            except Exception as e:
                logger.warning(f"방법 1 실패: {str(e)}")
                import traceback
                logger.debug(traceback.format_exc())
            
            # 방법 2: Homebrew로 설치된 chromedriver 사용 (Mac)
            if not driver_initialized and platform.system() == 'Darwin':
                try:
                    logger.info("방법 2: Homebrew chromedriver 확인 중...")
                    
                    # Homebrew 경로들
                    homebrew_paths = [
                        '/opt/homebrew/bin/chromedriver',  # M1/M2/M3
                        '/usr/local/bin/chromedriver',      # Intel Mac
                    ]
                    
                    for path in homebrew_paths:
                        if os.path.exists(path):
                            logger.info(f"Homebrew chromedriver 발견: {path}")
                            service = Service(path)
                            self.driver = webdriver.Chrome(service=service, options=chrome_options)
                            driver_initialized = True
                            logger.info("✅ Homebrew chromedriver로 성공!")
                            break
                    
                    if not driver_initialized:
                        logger.warning("Homebrew chromedriver가 설치되어 있지 않습니다.")
                        logger.info("설치 방법: brew install chromedriver")
                        
                except Exception as e:
                    logger.warning(f"방법 2 실패: {str(e)}")
            
            # 방법 3: 시스템 기본 chromedriver
            if not driver_initialized:
                try:
                    logger.info("방법 3: 시스템 기본 chromedriver 시도...")
                    self.driver = webdriver.Chrome(options=chrome_options)
                    driver_initialized = True
                    logger.info("✅ 시스템 chromedriver로 성공!")
                except Exception as e:
                    logger.warning(f"방법 3 실패: {str(e)}")
            
            if not driver_initialized:
                error_msg = (
                    "\n" + "=" * 60 + "\n"
                    "❌ ChromeDriver를 초기화할 수 없습니다.\n"
                    "=" * 60 + "\n\n"
                    "Mac ARM64 (M1/M2/M3) 해결 방법:\n\n"
                    "1️⃣ 캐시 삭제 후 재시도:\n"
                    "   rm -rf ~/.wdm\n"
                    "   python golf_auto_booking_mac.py\n\n"
                    "2️⃣ Homebrew로 설치 (권장):\n"
                    "   brew install chromedriver\n"
                    "   xattr -d com.apple.quarantine /opt/homebrew/bin/chromedriver\n\n"
                    "3️⃣ 수동 다운로드:\n"
                    "   - Chrome 버전 확인: chrome://version\n"
                    "   - https://googlechromelabs.github.io/chrome-for-testing/\n"
                    "   - mac-arm64 버전 다운로드\n\n"
                    "=" * 60
                )
                raise Exception(error_msg)
            
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)
            
            logger.info("✅ Chrome 드라이버 초기화 완료")
            logger.info(f"Chrome 버전: {self.get_chrome_version()}")
            return True
            
        except Exception as e:
            logger.error(f"❌ 드라이버 설정 실패: {str(e)}")
            return False
    
    def get_chrome_version(self):
        """Chrome 버전 확인"""
        try:
            if platform.system() == 'Darwin':  # Mac
                result = subprocess.run(
                    ['/Applications/Google Chrome.app/Contents/MacOS/Google Chrome', '--version'],
                    capture_output=True,
                    text=True
                )
                return result.stdout.strip()
            return "Unknown"
        except:
            return "Unknown"
    
    def naver_login(self):
        """네이버 로그인"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"네이버 로그인 시도 {attempt + 1}/{max_attempts}...")
                self.driver.get("https://nid.naver.com/nidlogin.login")
                time.sleep(2)
                
                self.driver.execute_script(
                    f"document.getElementById('id').value = '{self.config['user_id']}'"
                )
                self.driver.execute_script(
                    f"document.getElementById('pw').value = '{self.config['user_pw']}'"
                )
                time.sleep(1)
                
                login_btn = self.driver.find_element(By.ID, "log.login")
                login_btn.click()
                time.sleep(5)
                
                current_url = self.driver.current_url
                if "nid.naver.com" not in current_url or "nidlogin" not in current_url:
                    logger.info("✅ 네이버 로그인 성공")
                    return True
                
                try:
                    captcha = self.driver.find_element(By.ID, "captcha")
                    if captcha:
                        logger.warning("⚠️  캡차 감지됨 - 수동 입력 필요")
                        logger.warning("브라우저에서 캡차를 입력하고 60초 대기합니다...")
                        time.sleep(60)
                        
                        if "nid.naver.com" not in self.driver.current_url:
                            logger.info("✅ 수동 로그인 완료")
                            return True
                except:
                    pass
                
            except Exception as e:
                logger.error(f"로그인 시도 {attempt + 1} 실패: {str(e)}")
                if attempt < max_attempts - 1:
                    time.sleep(3)
        
        logger.error("❌ 네이버 로그인 실패")
        return False
    
    def book_golf_slot(self):
        """골프 예약 실행"""
        try:
            booking_url = (
                "https://map.naver.com/p/search/%EB%A9%94%EC%9D%B4%EC%A0%80"
                "%EA%B3%A8%ED%94%84%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8/"
                "place/1076834793?placePath=/ticket"
            )
            
            logger.info(f"🔗 예약 페이지 접속...")
            self.driver.get(booking_url)
            time.sleep(3)
            
            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it("entryIframe"))
                logger.info("✅ iframe 전환 완료")
                time.sleep(2)
            except TimeoutException:
                logger.error("❌ iframe을 찾을 수 없음")
                return False
            
            try:
                booking_tab = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '예약')]"))
                )
                booking_tab.click()
                time.sleep(2)
                logger.info("✅ 예약 탭 클릭")
            except:
                logger.info("ℹ️  예약 탭이 이미 선택됨")
            
            logger.info("✅ 예약 프로세스 테스트 완료")
            logger.info("ℹ️  실제 예약 로직은 구현 필요")
            return True
            
        except Exception as e:
            logger.error(f"❌ 예약 중 오류 발생: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def send_notification(self, success, message=""):
        """알림 전송"""
        if success:
            logger.info(f"📢 알림: 예약 성공! {message}")
        else:
            logger.error(f"📢 알림: 예약 실패! {message}")
    
    def run(self):
        """예약 봇 메인 실행"""
        try:
            logger.info("=" * 60)
            logger.info("🏌️  골프 자동 예약 시작 (Mac ARM64 최적화)")
            logger.info("=" * 60)
            
            if not self.setup_driver():
                return False
            
            if not self.naver_login():
                self.send_notification(False, "로그인 실패")
                return False
            
            logger.info("🎯 예약 시도 시작!")
            success = self.book_golf_slot()
            
            if success:
                self.send_notification(True, "테스트 완료!")
                time.sleep(5)
            else:
                self.send_notification(False, "테스트 실패")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 예약 프로세스 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
            
        finally:
            if self.driver:
                logger.info("🔚 브라우저 종료 중...")
                time.sleep(3)
                self.driver.quit()
                logger.info("✅ 브라우저 종료 완료")


def load_config(config_file='config.json'):
    """설정 파일 로드"""
    try:
        if os.path.exists(config_file):
            with open(config_file, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        logger.error(f"설정 파일 로드 실패: {str(e)}")
    
    return {
        'user_id': 'YOUR_NAVER_ID',
        'user_pw': 'YOUR_NAVER_PW',
        'preferred_time': '19:00',
        'headless': False,
    }


def main():
    """메인 함수"""
    print("=" * 60)
    print("🏌️  골프 자동 예약 프로그램")
    print("🍎 Mac ARM64 (M1/M2/M3) 최적화 버전")
    print("=" * 60)
    print()
    
    # 시스템 정보 출력
    print(f"시스템: {platform.system()} {platform.machine()}")
    print(f"Python: {sys.version.split()[0]}")
    print()
    
    if not os.path.exists('config.json'):
        print("⚠️  config.json 파일이 없습니다.")
        sample_config = {
            'user_id': 'YOUR_NAVER_ID',
            'user_pw': 'YOUR_NAVER_PASSWORD',
            'preferred_time': '19:00',
            'headless': False,
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, ensure_ascii=False, indent=2)
        print("✅ config.json 파일이 생성되었습니다.")
        return
    
    print("실행 모드를 선택하세요:")
    print("1. 즉시 실행 (테스트)")
    print("2. 스케줄 실행 (매일 자정)")
    print("3. 수동 실행 (대기 없이)")
    print()
    
    choice = input("선택 (1-3): ").strip()
    
    if choice in ['1', '3']:
        logger.info("테스트 실행 모드")
        config = load_config()
        bot = GolfBookingBot(config)
        bot.run()
    elif choice == '2':
        logger.info("스케줄 실행 모드 - 준비 중")
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
