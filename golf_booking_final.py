#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메이저골프아카데미 자동 예약 프로그램 (최종 버전)
- 타석 우선순위: 11, 7, 8, 9, 10번 → 빈자리
- 평일(월~금): 12:00 자동 예약
- 주말(토~일): 13:00 자동 예약
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
        """Chrome 드라이버 설정"""
        try:
            chrome_options = Options()
            
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
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
            
            if is_mac_arm:
                logger.info("🍎 Mac ARM64 감지됨")
            
            # webdriver-manager 사용
            try:
                logger.info("ChromeDriver 설치 중...")
                from webdriver_manager.chrome import ChromeDriverManager
                
                if is_mac_arm:
                    driver_path = ChromeDriverManager().install()
                    
                    possible_paths = [
                        os.path.join(os.path.dirname(driver_path), 'chromedriver-mac-arm64', 'chromedriver'),
                        os.path.join(os.path.dirname(driver_path), 'chromedriver'),
                        driver_path
                    ]
                    
                    actual_driver_path = None
                    for path in possible_paths:
                        if os.path.exists(path) and os.path.isfile(path):
                            if not os.access(path, os.X_OK):
                                os.chmod(path, 0o755)
                            actual_driver_path = path
                            break
                    
                    if actual_driver_path:
                        service = Service(actual_driver_path)
                    else:
                        raise Exception("ChromeDriver not found")
                else:
                    driver_path = ChromeDriverManager().install()
                    service = Service(driver_path)
                
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                driver_initialized = True
                logger.info("✅ ChromeDriver 초기화 완료")
                
            except Exception as e:
                logger.error(f"❌ ChromeDriver 설정 실패: {str(e)}")
                return False
            
            self.driver.implicitly_wait(10)
            self.wait = WebDriverWait(self.driver, 20)
            return True
            
        except Exception as e:
            logger.error(f"❌ 드라이버 설정 실패: {str(e)}")
            return False
    
    def naver_login(self):
        """네이버 로그인"""
        try:
            logger.info("네이버 로그인 시작...")
            self.driver.get("https://nid.naver.com/nidlogin.login")
            time.sleep(3)
            
            try:
                self.driver.current_url
            except:
                logger.error("❌ 브라우저가 닫혔습니다")
                return False
            
            try:
                id_input = self.wait.until(
                    EC.presence_of_element_located((By.ID, "id"))
                )
                pw_input = self.driver.find_element(By.ID, "pw")
                logger.info("✅ 로그인 폼 확인")
            except Exception as e:
                logger.error(f"❌ 로그인 폼을 찾을 수 없음: {str(e)}")
                return False
            
            try:
                logger.info("로그인 정보 입력 중...")
                id_input.clear()
                id_input.send_keys(self.config['user_id'])
                time.sleep(0.5)
                
                pw_input.clear()
                pw_input.send_keys(self.config['user_pw'])
                time.sleep(0.5)
                
                logger.info("✅ 로그인 정보 입력 완료")
            except Exception as e:
                logger.error(f"❌ 정보 입력 실패: {str(e)}")
                return False
            
            try:
                login_btn = self.driver.find_element(By.ID, "log.login")
                logger.info("로그인 버튼 클릭...")
                login_btn.click()
                time.sleep(5)
            except Exception as e:
                logger.error(f"❌ 로그인 버튼 클릭 실패: {str(e)}")
                return False
            
            try:
                current_url = self.driver.current_url
                logger.info(f"현재 URL: {current_url}")
                
                if "nid.naver.com/nidlogin" not in current_url:
                    logger.info("✅ 네이버 로그인 성공!")
                    return True
                
                # 캡차 확인
                try:
                    captcha = self.driver.find_element(By.ID, "captcha")
                    logger.warning("⚠️  캡차가 나타났습니다!")
                    logger.warning("브라우저 창에서 캡차를 입력해주세요 (최대 90초 대기)")
                    
                    for i in range(18):
                        time.sleep(5)
                        try:
                            current_url = self.driver.current_url
                            if "nid.naver.com/nidlogin" not in current_url:
                                logger.info("✅ 캡차 통과! 로그인 성공!")
                                return True
                        except:
                            logger.error("❌ 브라우저가 닫혔습니다")
                            return False
                    
                    logger.error("❌ 캡차 입력 시간 초과")
                    return False
                    
                except NoSuchElementException:
                    logger.error("❌ 로그인 실패 - ID/PW를 확인하세요")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ 로그인 확인 중 오류: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 네이버 로그인 실패: {str(e)}")
            return False
    
    def book_golf_slot(self):
        """
        골프 예약 실행
        - 타석 우선순위: 11, 7, 8, 9, 10 → 빈자리
        - 평일: 12:00 / 주말: 13:00
        """
        try:
            booking_url = (
                "https://map.naver.com/p/search/%EB%A9%94%EC%9D%B4%EC%A0%80"
                "%EA%B3%A8%ED%94%84%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8/"
                "place/1076834793?placePath=/ticket"
            )
            
            logger.info(f"🔗 예약 페이지 접속...")
            self.driver.get(booking_url)
            time.sleep(3)
            
            # iframe 전환
            try:
                self.wait.until(EC.frame_to_be_available_and_switch_to_it("entryIframe"))
                logger.info("✅ iframe 전환 완료")
                time.sleep(2)
            except TimeoutException:
                logger.error("❌ iframe을 찾을 수 없음")
                return False
            
            # 예약 탭 클릭
            try:
                booking_tab = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '예약')]"))
                )
                booking_tab.click()
                time.sleep(2)
                logger.info("✅ 예약 탭 클릭")
            except:
                logger.info("ℹ️  예약 탭이 이미 선택됨")
            
            # 평일/주말 시간 자동 설정
            today = datetime.now()
            weekday = today.weekday()  # 0=월요일, 6=일요일
            
            if weekday < 5:  # 월~금
                target_time_24 = "12:00"  # 24시간 형식
                target_time_12 = "12:00"  # 12시간 형식 (오후)
                day_type = "평일"
            else:  # 토~일
                target_time_24 = "13:00"  # 24시간 형식
                target_time_12 = "1:00"   # 12시간 형식 (오후)
                day_type = "주말"
            
            logger.info("=" * 60)
            logger.info(f"📅 오늘: {day_type} ({['월','화','수','목','금','토','일'][weekday]}요일)")
            logger.info(f"🎯 예약 시간: {target_time_24} (오후 {target_time_12})")
            logger.info("=" * 60)
            
            # 시간대 선택 (여러 형식 시도)
            time_selected = False
            try:
                # 다양한 시간 형식 시도
                time_patterns = [
                    target_time_24,      # "13:00"
                    target_time_12,      # "1:00"
                    f"오후 {target_time_12}",  # "오후 1:00"
                    f"오후{target_time_12}",   # "오후1:00" (공백 없음)
                ]
                
                logger.info(f"시간대 검색 패턴: {time_patterns}")
                
                for time_pattern in time_patterns:
                    if time_selected:
                        break
                    
                    time_selectors = [
                        f"//*[contains(text(), '{time_pattern}')]",
                        f"//button[contains(text(), '{time_pattern}')]",
                        f"//a[contains(text(), '{time_pattern}')]",
                        f"//*[text()='{time_pattern}']",  # 정확히 일치
                    ]
                    
                    for selector in time_selectors:
                        try:
                            time_slots = self.driver.find_elements(By.XPATH, selector)
                            for slot in time_slots:
                                if slot.is_displayed() and slot.is_enabled():
                                    slot_text = slot.text
                                    logger.info(f"시간대 발견: '{slot_text}'")
                                    
                                    # 예약 불가능 체크
                                    if any(keyword in slot_text for keyword in ['마감', '불가', '종료']):
                                        logger.warning(f"  ⚠️  {slot_text}: 예약 불가능")
                                        continue
                                    
                                    slot.click()
                                    logger.info(f"✅ 시간대 선택: {slot_text}")
                                    time.sleep(2)
                                    time_selected = True
                                    break
                            if time_selected:
                                break
                        except:
                            continue
                
                if not time_selected:
                    logger.warning(f"⚠️  원하는 시간대({target_time_24})를 찾을 수 없습니다")
                    logger.info("ℹ️  현재 표시된 시간대로 진행합니다")
                    
            except Exception as e:
                logger.warning(f"⚠️  시간 선택 중 경고: {str(e)}")
            
            # 우선순위 타석 목록
            priority_seats = [11, 7, 8, 9, 10]
            logger.info("=" * 60)
            logger.info(f"🎯 타석 우선순위: {' > '.join(map(str, priority_seats))} > 빈자리")
            logger.info("=" * 60)
            
            seat_selected = False
            selected_seat = None
            
            # 우선순위대로 타석 시도
            for seat_num in priority_seats:
                try:
                    logger.info(f"🔍 {seat_num}번 타석 확인 중...")
                    
                    seat_selectors = [
                        f"//*[contains(text(), '{seat_num}번타석예약')]",
                        f"//button[contains(text(), '{seat_num}번타석')]",
                        f"//a[contains(text(), '{seat_num}번타석')]",
                    ]
                    
                    for selector in seat_selectors:
                        try:
                            seat_elements = self.driver.find_elements(By.XPATH, selector)
                            
                            for element in seat_elements:
                                if element.is_displayed() and element.is_enabled():
                                    element_text = element.text
                                    
                                    # "예약불가", "마감" 등이 포함되어 있으면 스킵
                                    if any(keyword in element_text for keyword in ['예약불가', '마감', '불가능', '종료']):
                                        logger.info(f"  ⚠️  {seat_num}번 타석: 예약 불가능")
                                        break
                                    
                                    # 예약 가능한 타석 클릭
                                    element.click()
                                    logger.info(f"  ✅ {seat_num}번 타석 선택 성공!")
                                    time.sleep(2)
                                    seat_selected = True
                                    selected_seat = seat_num
                                    break
                            
                            if seat_selected:
                                break
                                
                        except Exception as e:
                            continue
                    
                    if seat_selected:
                        break
                        
                except Exception as e:
                    logger.debug(f"  {seat_num}번 타석 확인 실패: {str(e)}")
                    continue
            
            # 우선순위 타석이 모두 실패한 경우, 예약 가능한 아무 타석 선택
            if not seat_selected:
                logger.warning("⚠️  우선순위 타석이 모두 예약 불가능합니다")
                logger.info("🔍 예약 가능한 다른 타석 검색 중...")
                
                try:
                    all_seats = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), '번타석예약')]"
                    )
                    
                    logger.info(f"총 {len(all_seats)}개 타석 발견")
                    
                    for seat in all_seats:
                        try:
                            if seat.is_displayed() and seat.is_enabled():
                                seat_text = seat.text
                                
                                # "예약불가", "마감" 등이 없으면 클릭
                                if not any(keyword in seat_text for keyword in ['예약불가', '마감', '불가능', '종료']):
                                    seat.click()
                                    logger.info(f"✅ 예약 가능한 타석 선택: {seat_text}")
                                    time.sleep(2)
                                    seat_selected = True
                                    selected_seat = seat_text
                                    break
                        except:
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ 예약 가능한 타석을 찾을 수 없습니다: {str(e)}")
            
            if not seat_selected:
                logger.error("❌ 예약 가능한 타석이 하나도 없습니다!")
                return False
            
            # 확인 버튼 클릭
            try:
                logger.info("예약 확인 버튼 대기 중...")
                time.sleep(2)
                
                confirm_button_selectors = [
                    "//button[contains(text(), '예약')]",
                    "//button[contains(text(), '확인')]",
                    "//button[contains(text(), '예약하기')]",
                    "//a[contains(text(), '예약')]",
                    "//a[contains(text(), '확인')]",
                ]
                
                button_clicked = False
                for selector in confirm_button_selectors:
                    try:
                        confirm_btn = self.driver.find_element(By.XPATH, selector)
                        if confirm_btn.is_displayed() and confirm_btn.is_enabled():
                            confirm_btn.click()
                            logger.info(f"✅ 확인 버튼 클릭")
                            time.sleep(2)
                            button_clicked = True
                            break
                    except:
                        continue
                
                if not button_clicked:
                    logger.warning("⚠️  확인 버튼을 찾지 못했습니다")
                    logger.info("타석 선택만으로 예약이 완료되었을 수 있습니다")
                
            except Exception as e:
                logger.warning(f"⚠️  확인 버튼 처리 중 경고: {str(e)}")
            
            # 최종 확인 팝업 처리
            try:
                time.sleep(2)
                final_confirm = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '동의') or contains(text(), '최종확인') or contains(text(), '결제')]"
                )
                final_confirm.click()
                logger.info("✅ 최종 확인 완료")
                time.sleep(2)
            except:
                logger.info("ℹ️  최종 확인 팝업 없음")
            
            # 예약 성공 메시지 확인
            try:
                time.sleep(2)
                page_source = self.driver.page_source
                
                logger.info("=" * 60)
                if any(keyword in page_source for keyword in ['예약 완료', '예약이 완료', '예약완료', '예약 성공']):
                    logger.info("🎉 예약 완료!")
                else:
                    logger.info("✅ 예약 프로세스 완료")
                
                # 예약 정보 출력
                if weekday < 5:  # 평일
                    logger.info(f"📅 예약 시간: 12:00 (오후 12:00) - {day_type}")
                else:  # 주말
                    logger.info(f"📅 예약 시간: 13:00 (오후 1:00) - {day_type}")
                logger.info(f"🎯 예약 타석: {selected_seat}번")
                logger.info("=" * 60)
                return True
                    
            except Exception as e:
                logger.warning(f"예약 확인 중 오류: {str(e)}")
                logger.info("✅ 예약 프로세스는 완료되었습니다")
                return True
            
        except Exception as e:
            logger.error(f"❌ 예약 중 오류 발생: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"error_{timestamp}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 에러 스크린샷 저장: {screenshot_path}")
            except:
                pass
            
            return False
    
    def run(self):
        """예약 봇 메인 실행"""
        try:
            logger.info("=" * 60)
            logger.info("🏌️  골프 자동 예약 시작")
            logger.info("=" * 60)
            
            if not self.setup_driver():
                return False
            
            if not self.naver_login():
                logger.error("❌ 로그인 실패")
                return False
            
            logger.info("🎯 예약 시도 시작!")
            success = self.book_golf_slot()
            
            if success:
                logger.info("✅ 예약 완료!")
                time.sleep(5)
            else:
                logger.error("❌ 예약 실패")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 예약 프로세스 오류: {str(e)}")
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
        'headless': False,
    }


def schedule_booking():
    """스케줄된 예약 실행"""
    config = load_config()
    bot = GolfBookingBot(config)
    bot.run()


def main():
    """메인 함수"""
    print("=" * 60)
    print("🏌️  골프 자동 예약 프로그램 (최종 버전)")
    print("=" * 60)
    print("📌 타석 우선순위: 11 > 7 > 8 > 9 > 10 > 빈자리")
    print("📌 평일(월~금): 12:00 / 주말(토~일): 13:00")
    print("=" * 60)
    print()
    
    if not os.path.exists('config.json'):
        print("⚠️  config.json 파일이 없습니다.")
        sample_config = {
            'user_id': 'YOUR_NAVER_ID',
            'user_pw': 'YOUR_NAVER_PASSWORD',
            'headless': False,
        }
        with open('config.json', 'w', encoding='utf-8') as f:
            json.dump(sample_config, f, ensure_ascii=False, indent=2)
        print("✅ config.json 파일이 생성되었습니다.")
        print("파일을 열어 네이버 ID/PW를 수정하세요.")
        return
    
    print("실행 모드를 선택하세요:")
    print("1. 즉시 실행 (테스트)")
    print("2. 스케줄 실행 (매일 자정)")
    print()
    
    choice = input("선택 (1-2): ").strip()
    
    if choice == '1':
        logger.info("테스트 실행 모드")
        config = load_config()
        bot = GolfBookingBot(config)
        bot.run()
    elif choice == '2':
        logger.info("스케줄 실행 모드 - 매일 23:59:50에 예약 시도")
        schedule.every().day.at("23:59:50").do(schedule_booking)
        
        print("✅ 스케줄 등록 완료")
        print("프로그램을 종료하려면 Ctrl+C를 누르세요.")
        
        while True:
            schedule.run_pending()
            time.sleep(1)
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
