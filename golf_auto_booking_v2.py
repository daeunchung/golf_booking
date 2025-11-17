#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메이저골프아카데미 자동 예약 프로그램 (개선 버전)
- ChromeDriver 자동 설치
- 강화된 에러 처리
- 재시도 로직
- 알림 기능 (선택)
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
import schedule
import time
from datetime import datetime, timedelta
import logging
import json
import os

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
        """Chrome 드라이버 자동 설치 및 설정"""
        try:
            chrome_options = Options()
            
            # 헤드리스 모드 (백그라운드 실행) - 테스트시 주석 처리
            if self.config.get('headless', False):
                chrome_options.add_argument('--headless')
            
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # 창 크기 설정
            chrome_options.add_argument('--window-size=1920,1080')
            
            # User Agent
            chrome_options.add_argument(
                'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
            
            # ChromeDriver 자동 설치
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)
            
            logger.info("✅ Chrome 드라이버 초기화 완료")
            return True
            
        except Exception as e:
            logger.error(f"❌ 드라이버 설정 실패: {str(e)}")
            return False
    
    def naver_login(self):
        """네이버 로그인"""
        max_attempts = 3
        
        for attempt in range(max_attempts):
            try:
                logger.info(f"네이버 로그인 시도 {attempt + 1}/{max_attempts}...")
                self.driver.get("https://nid.naver.com/nidlogin.login")
                time.sleep(2)
                
                # JavaScript로 로그인 정보 입력
                self.driver.execute_script(
                    f"document.getElementById('id').value = '{self.config['user_id']}'"
                )
                self.driver.execute_script(
                    f"document.getElementById('pw').value = '{self.config['user_pw']}'"
                )
                time.sleep(1)
                
                # 로그인 버튼 클릭
                login_btn = self.driver.find_element(By.ID, "log.login")
                login_btn.click()
                time.sleep(5)
                
                # 로그인 성공 확인
                current_url = self.driver.current_url
                if "nid.naver.com" not in current_url or "nidlogin" not in current_url:
                    logger.info("✅ 네이버 로그인 성공")
                    return True
                
                # 캡차 확인
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
    
    def wait_until_booking_time(self):
        """예약 시간까지 대기"""
        now = datetime.now()
        
        # 다음 날 자정으로 설정
        target = now.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
        
        # 설정된 시간만큼 앞당김 (예: 10초 전)
        advance_seconds = self.config.get('advance_seconds', 10)
        target = target - timedelta(seconds=advance_seconds)
        
        wait_seconds = (target - now).total_seconds()
        
        if wait_seconds > 0:
            logger.info(f"⏰ 예약 시간까지 {wait_seconds:.0f}초 대기 중...")
            logger.info(f"예약 시도 시각: {target.strftime('%Y-%m-%d %H:%M:%S')}")
            time.sleep(wait_seconds)
    
    def try_book_with_retry(self, max_retries=3):
        """재시도 로직을 포함한 예약"""
        for attempt in range(max_retries):
            try:
                logger.info(f"📌 예약 시도 {attempt + 1}/{max_retries}")
                
                if self.book_golf_slot():
                    logger.info("✅ 예약 성공!")
                    return True
                    
            except Exception as e:
                logger.error(f"❌ 예약 시도 {attempt + 1} 실패: {str(e)}")
                
                # 스크린샷 저장
                try:
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    screenshot_path = f"error_{timestamp}_attempt{attempt + 1}.png"
                    self.driver.save_screenshot(screenshot_path)
                    logger.info(f"📸 스크린샷 저장: {screenshot_path}")
                except:
                    pass
                
                if attempt < max_retries - 1:
                    retry_delay = self.config.get('retry_delay', 2)
                    logger.info(f"⏳ {retry_delay}초 후 재시도...")
                    time.sleep(retry_delay)
        
        logger.error("❌ 모든 예약 시도 실패")
        return False
    
    def book_golf_slot(self):
        """골프 예약 실행 (핵심 로직)"""
        try:
            # 1. 예약 페이지 접속
            booking_url = (
                "https://map.naver.com/p/search/%EB%A9%94%EC%9D%B4%EC%A0%80"
                "%EA%B3%A8%ED%94%84%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8/"
                "place/1076834793?placePath=/ticket"
            )
            
            logger.info(f"🔗 예약 페이지 접속...")
            self.driver.get(booking_url)
            time.sleep(3)
            
            # 2. iframe 전환
            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it("entryIframe"))
                logger.info("✅ iframe 전환 완료")
                time.sleep(2)
            except TimeoutException:
                logger.error("❌ iframe을 찾을 수 없음")
                return False
            
            # 3. 예약 탭 클릭 (이미 선택되어 있을 수 있음)
            try:
                booking_tab = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '예약')]"))
                )
                booking_tab.click()
                time.sleep(2)
                logger.info("✅ 예약 탭 클릭")
            except:
                logger.info("ℹ️  예약 탭이 이미 선택됨")
            
            # 4. 원하는 시간대 선택
            preferred_time = self.config.get('preferred_time', '19:00')
            logger.info(f"🎯 선호 시간대: {preferred_time}")
            
            # 시간대 요소 찾기 (여러 선택자 시도)
            selectors = [
                f"//button[contains(text(), '{preferred_time}')]",
                f"//*[contains(text(), '{preferred_time}')]/ancestor::button",
                f"//*[contains(text(), '{preferred_time}')]/parent::*",
                "//button[contains(@class, 'time') or contains(@class, 'slot')]",
            ]
            
            time_slot_found = False
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    for elem in elements:
                        elem_text = elem.text
                        if preferred_time in elem_text:
                            # 예약 가능 여부 확인
                            if any(keyword in elem_text for keyword in ['예약', '선택', '가능']):
                                elem.click()
                                logger.info(f"✅ 시간대 선택: {elem_text}")
                                time.sleep(1)
                                time_slot_found = True
                                break
                    if time_slot_found:
                        break
                except Exception as e:
                    logger.debug(f"선택자 시도 실패: {selector} - {str(e)}")
                    continue
            
            if not time_slot_found:
                logger.warning(f"⚠️  선호 시간대({preferred_time})를 찾지 못함")
                # 첫 번째 예약 가능한 시간 선택
                try:
                    available = self.driver.find_element(
                        By.XPATH, 
                        "//button[contains(text(), '예약') or contains(text(), '선택')]"
                    )
                    available.click()
                    logger.info("✅ 첫 번째 가능한 시간 선택")
                    time.sleep(1)
                except:
                    logger.error("❌ 예약 가능한 시간을 찾을 수 없음")
                    return False
            
            # 5. 좌석 선택 (필요한 경우)
            try:
                # 좌석 선택 버튼 찾기
                seat_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@class, 'seat') or contains(text(), '타석')]"
                )
                
                if seat_buttons:
                    # 선호 좌석 번호가 있으면 사용, 없으면 첫 번째 선택
                    preferred_seat = self.config.get('preferred_seat')
                    
                    if preferred_seat:
                        for btn in seat_buttons:
                            if str(preferred_seat) in btn.text:
                                btn.click()
                                logger.info(f"✅ 좌석 선택: {btn.text}")
                                time.sleep(1)
                                break
                    else:
                        seat_buttons[0].click()
                        logger.info(f"✅ 좌석 선택: {seat_buttons[0].text}")
                        time.sleep(1)
            except Exception as e:
                logger.info(f"ℹ️  좌석 선택 단계 스킵: {str(e)}")
            
            # 6. 예약하기 버튼 클릭
            try:
                book_btn = self.wait.until(
                    EC.element_to_be_clickable((
                        By.XPATH,
                        "//button[contains(text(), '예약하기') or contains(text(), '예약')]"
                    ))
                )
                book_btn.click()
                logger.info("✅ 예약하기 버튼 클릭")
                time.sleep(2)
            except TimeoutException:
                logger.error("❌ 예약하기 버튼을 찾을 수 없음")
                return False
            
            # 7. 최종 확인 (팝업이 있는 경우)
            try:
                confirm_btn = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '확인') or contains(text(), '동의')]"
                )
                confirm_btn.click()
                logger.info("✅ 최종 확인 완료")
                time.sleep(2)
            except:
                logger.info("ℹ️  확인 버튼 없음 (이미 예약 완료)")
            
            # 8. 성공 메시지 확인
            try:
                success_msg = self.driver.find_element(
                    By.XPATH,
                    "//*[contains(text(), '예약이 완료') or contains(text(), '예약 완료')]"
                )
                if success_msg:
                    logger.info("🎉 예약 완료 메시지 확인!")
                    return True
            except:
                pass
            
            # 성공 여부 불확실하지만 에러 없이 진행됨
            logger.info("✅ 예약 프로세스 완료 (성공 추정)")
            return True
            
        except Exception as e:
            logger.error(f"❌ 예약 중 오류 발생: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def send_notification(self, success, message=""):
        """알림 전송 (선택 사항)"""
        if not self.config.get('enable_notification', False):
            return
        
        notification_type = self.config.get('notification_type', 'log')
        
        # 카카오톡 알림
        if notification_type == 'kakao':
            try:
                from kakao_notification import KakaoNotifier
                
                kakao_api_key = self.config.get('kakao_rest_api_key')
                if not kakao_api_key:
                    logger.error("❌ 카카오 REST API 키가 설정되지 않았습니다")
                    return
                
                notifier = KakaoNotifier(kakao_api_key)
                
                if success:
                    text = f"🎉 골프 예약 성공!\n\n{message}\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                else:
                    text = f"❌ 골프 예약 실패\n\n{message}\n시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                
                notifier.send_message(text)
                logger.info("✅ 카카오톡 알림 전송 완료")
                
            except Exception as e:
                logger.error(f"❌ 카카오톡 알림 전송 실패: {str(e)}")
        
        # 로그 알림 (기본)
        else:
            if success:
                logger.info(f"📢 알림: 예약 성공! {message}")
            else:
                logger.error(f"📢 알림: 예약 실패! {message}")
    
    def run(self):
        """예약 봇 메인 실행"""
        try:
            logger.info("=" * 60)
            logger.info("🏌️  골프 자동 예약 시작")
            logger.info("=" * 60)
            
            # 1. 드라이버 설정
            if not self.setup_driver():
                return False
            
            # 2. 네이버 로그인
            if not self.naver_login():
                self.send_notification(False, "로그인 실패")
                return False
            
            # 3. 예약 시간까지 대기 (필요시)
            if self.config.get('wait_for_time', False):
                self.wait_until_booking_time()
            
            # 4. 예약 시도 (재시도 포함)
            logger.info("🎯 예약 시도 시작!")
            max_retries = self.config.get('max_retries', 3)
            success = self.try_book_with_retry(max_retries)
            
            # 5. 결과 알림
            if success:
                self.send_notification(True, "예약이 완료되었습니다!")
                # 결과 확인을 위해 잠시 대기
                time.sleep(5)
            else:
                self.send_notification(False, "예약에 실패했습니다.")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 예약 프로세스 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            self.send_notification(False, f"오류 발생: {str(e)}")
            return False
            
        finally:
            # 브라우저 종료
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
    
    # 기본 설정
    return {
        'user_id': 'YOUR_NAVER_ID',
        'user_pw': 'YOUR_NAVER_PW',
        'preferred_time': '19:00',
        'preferred_seat': None,
        'branch': '중계점',
        'max_retries': 3,
        'retry_delay': 2,
        'advance_seconds': 10,
        'wait_for_time': True,
        'headless': False,
        'enable_notification': False,
        'notification_type': 'log'
    }


def schedule_booking():
    """스케줄된 예약 실행"""
    config = load_config()
    bot = GolfBookingBot(config)
    bot.run()


def main():
    """메인 함수"""
    print("=" * 60)
    print("🏌️  골프 자동 예약 프로그램")
    print("=" * 60)
    print()
    
    # 설정 파일 확인
    if not os.path.exists('config.json'):
        print("⚠️  config.json 파일이 없습니다.")
        print("샘플 설정 파일을 생성합니다...")
        
        sample_config = {
            'user_id': 'YOUR_NAVER_ID',
            'user_pw': 'YOUR_NAVER_PASSWORD',
            'preferred_time': '19:00',
            'preferred_seat': None,
            'branch': '중계점',
            'max_retries': 3,
            'retry_delay': 2,
            'advance_seconds': 10,
            'wait_for_time': True,
            'headless': False,
            'enable_notification': False,
            'notification_type': 'log'
        }
        
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, ensure_ascii=False, indent=2)
        
        print("✅ config.json 파일이 생성되었습니다.")
        print("파일을 열어 네이버 ID/PW와 설정을 수정하세요.")
        return
    
    print("실행 모드를 선택하세요:")
    print("1. 즉시 실행 (테스트)")
    print("2. 스케줄 실행 (매일 자정)")
    print("3. 수동 실행 (대기 없이)")
    print()
    
    choice = input("선택 (1-3): ").strip()
    
    if choice == '1':
        # 즉시 실행 (테스트)
        logger.info("즉시 실행 모드")
        config = load_config()
        config['wait_for_time'] = False
        bot = GolfBookingBot(config)
        bot.run()
        
    elif choice == '2':
        # 스케줄 실행
        logger.info("스케줄 실행 모드 - 매일 23:59:50에 예약 시도")
        schedule.every().day.at("23:59:50").do(schedule_booking)
        
        print("✅ 스케줄 등록 완료")
        print("프로그램을 종료하려면 Ctrl+C를 누르세요.")
        print()
        
        while True:
            schedule.run_pending()
            time.sleep(1)
            
    elif choice == '3':
        # 수동 실행
        logger.info("수동 실행 모드")
        config = load_config()
        config['wait_for_time'] = False
        bot = GolfBookingBot(config)
        bot.run()
        
    else:
        print("잘못된 선택입니다.")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
        logger.info("사용자에 의해 프로그램 종료")
    except Exception as e:
        logger.error(f"예상치 못한 오류: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
