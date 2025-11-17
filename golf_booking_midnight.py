#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메이저골프아카데미 자동 예약 프로그램 (자정 최적화 버전)
- 타석 우선순위: 11, 7, 8, 9, 10번 → 빈자리
- 평일(월~금): 12:00 / 주말(토~일): 13:00
- 자정 정확히 맞춰서 예약 시도
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
            
            is_mac_arm = platform.system() == 'Darwin' and platform.machine() == 'arm64'
            
            if is_mac_arm:
                logger.info("🍎 Mac ARM64 감지됨")
            
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
    
    def save_cookies(self):
        """로그인 쿠키 저장"""
        try:
            import pickle
            cookies = self.driver.get_cookies()
            with open('naver_cookies.pkl', 'wb') as f:
                pickle.dump(cookies, f)
            logger.info("✅ 쿠키 저장 완료")
        except Exception as e:
            logger.warning(f"⚠️  쿠키 저장 실패: {str(e)}")
    
    def load_cookies(self):
        """저장된 쿠키 로드"""
        try:
            import pickle
            if not os.path.exists('naver_cookies.pkl'):
                return False
            
            # 네이버 메인 페이지 먼저 방문 (쿠키 도메인 맞추기)
            self.driver.get("https://www.naver.com")
            time.sleep(2)
            
            with open('naver_cookies.pkl', 'rb') as f:
                cookies = pickle.load(f)
            
            for cookie in cookies:
                try:
                    self.driver.add_cookie(cookie)
                except:
                    pass
            
            logger.info("✅ 쿠키 로드 완료")
            
            # 로그인 확인
            self.driver.get("https://www.naver.com")
            time.sleep(2)
            
            # 로그인 상태 확인
            try:
                # 로그인 버튼이 없으면 이미 로그인됨
                self.driver.find_element(By.LINK_TEXT, "로그인")
                logger.info("ℹ️  쿠키 만료됨 - 재로그인 필요")
                return False
            except:
                logger.info("✅ 쿠키로 로그인 성공!")
                return True
                
        except Exception as e:
            logger.warning(f"⚠️  쿠키 로드 실패: {str(e)}")
            return False
    
    def naver_login(self):
        """네이버 로그인"""
        try:
            # 먼저 쿠키로 로그인 시도
            if self.load_cookies():
                logger.info("✅ 저장된 쿠키로 로그인 성공!")
                return True
            
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
                
                # 사람처럼 천천히 입력 (캡차 방지)
                id_input.clear()
                time.sleep(0.3)
                
                # ID 한 글자씩 입력
                for char in self.config['user_id']:
                    id_input.send_keys(char)
                    time.sleep(0.1 + (0.05 * (1 if len(char) > 0 else 0)))  # 0.1~0.15초 랜덤
                
                time.sleep(0.5)
                
                pw_input.clear()
                time.sleep(0.3)
                
                # PW 한 글자씩 입력
                for char in self.config['user_pw']:
                    pw_input.send_keys(char)
                    time.sleep(0.1 + (0.05 * (1 if len(char) > 0 else 0)))
                
                time.sleep(0.8)  # 입력 후 잠깐 대기 (사람처럼)
                
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
                
                if "nid.naver.com/nidlogin" not in current_url:
                    logger.info("✅ 네이버 로그인 성공!")
                    # 쿠키 저장
                    self.save_cookies()
                    return True
                
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
                                self.save_cookies()
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
    
    def wait_until_midnight(self):
        """자정까지 정확히 대기"""
        now = datetime.now()
        
        # 다음 날 자정 계산
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 자정 0.5초 전까지 대기
        target_time = midnight - timedelta(seconds=0.5)
        
        wait_seconds = (target_time - now).total_seconds()
        
        if wait_seconds > 0:
            logger.info("=" * 60)
            logger.info(f"⏰ 자정까지 대기 중...")
            logger.info(f"현재 시각: {now.strftime('%H:%M:%S')}")
            logger.info(f"예약 시각: {midnight.strftime('%H:%M:%S')}")
            logger.info(f"대기 시간: {wait_seconds:.1f}초")
            logger.info("=" * 60)
            
            # 진행률 표시
            if wait_seconds > 60:
                # 1분 이상 남으면 1분 단위로 표시
                while wait_seconds > 60:
                    time.sleep(30)
                    wait_seconds = (target_time - datetime.now()).total_seconds()
                    logger.info(f"⏰ 자정까지 {wait_seconds:.0f}초 남음...")
            
            # 마지막 60초는 정확히 대기
            if wait_seconds > 0:
                time.sleep(wait_seconds)
            
            logger.info("🎯 자정! 예약 시작!")
    
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
            # 중요: 오늘이 아니라 내일(예약하는 날) 기준!
            today = datetime.now()
            tomorrow = today + timedelta(days=1)  # 예약하는 날 = 내일
            weekday = tomorrow.weekday()  # 내일의 요일 (0=월요일, 6=일요일)
            
            if weekday < 5:  # 내일이 월~금
                target_time_24 = "12:00"
                target_time_12 = "12:00"
                day_type = "평일"
            else:  # 내일이 토~일
                target_time_24 = "13:00"
                target_time_12 = "1:00"
                day_type = "주말"
            
            logger.info("=" * 60)
            logger.info(f"📅 오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
            logger.info(f"📅 예약일: {tomorrow.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][weekday]}요일)")
            logger.info(f"🎯 예약 시간: {target_time_24} (오후 {target_time_12}) - {day_type}")
            logger.info("=" * 60)
            
            # 시간대 선택 (여러 번 시도)
            time_selected = False
            max_time_attempts = 5  # 최대 5번 시도
            
            for attempt in range(max_time_attempts):
                if time_selected:
                    break
                
                logger.info(f"━━━ 시간대 선택 시도 {attempt + 1}/{max_time_attempts} ━━━")
                
                try:
                    time_patterns = [
                        target_time_24,
                        target_time_12,
                        f"오후 {target_time_12}",
                        f"오후{target_time_12}",
                    ]
                    
                    logger.info(f"검색할 시간 패턴: {time_patterns}")
                    
                    for idx, time_pattern in enumerate(time_patterns):
                        if time_selected:
                            break
                        
                        logger.info(f"  [{idx+1}/{len(time_patterns)}] '{time_pattern}' 패턴으로 검색 중...")
                        
                        time_selectors = [
                            f"//*[contains(text(), '{time_pattern}')]",
                            f"//button[contains(text(), '{time_pattern}')]",
                            f"//a[contains(text(), '{time_pattern}')]",
                        ]
                        
                        for sel_idx, selector in enumerate(time_selectors):
                            try:
                                logger.debug(f"    selector {sel_idx+1}: {selector}")
                                time_slots = self.driver.find_elements(By.XPATH, selector)
                                logger.info(f"    → {len(time_slots)}개 요소 발견")
                                
                                for slot_idx, slot in enumerate(time_slots):
                                    try:
                                        if slot.is_displayed() and slot.is_enabled():
                                            slot_text = slot.text
                                            logger.info(f"      [{slot_idx+1}] 발견: '{slot_text}'")
                                            
                                            if any(keyword in slot_text for keyword in ['마감', '불가', '종료']):
                                                logger.warning(f"      ⚠️  '{slot_text}' - 예약 불가")
                                                continue
                                            
                                            logger.info(f"      ✅ 클릭 시도: '{slot_text}'")
                                            slot.click()
                                            logger.info(f"✅ 시간대 선택 성공: {slot_text}")
                                            time.sleep(1)
                                            time_selected = True
                                            break
                                    except Exception as e:
                                        logger.debug(f"      요소 처리 실패: {str(e)}")
                                        
                                if time_selected:
                                    break
                            except Exception as e:
                                logger.debug(f"    selector 실패: {str(e)}")
                                continue
                    
                    if not time_selected and attempt < max_time_attempts - 1:
                        logger.warning(f"시간대를 찾지 못함. 1초 후 재시도...")
                        time.sleep(1)
                        
                except Exception as e:
                    logger.warning(f"시간 선택 시도 {attempt + 1} 실패: {str(e)}")
                    if attempt < max_time_attempts - 1:
                        time.sleep(1)
            
            if not time_selected:
                logger.warning(f"⚠️  {target_time_24} 시간대를 찾지 못했습니다")
                logger.info("ℹ️  타석 선택으로 진행합니다")
            
            # 우선순위 타석
            priority_seats = [11, 7, 8, 9, 10]
            logger.info("=" * 60)
            logger.info(f"🎯 타석 우선순위: {' > '.join(map(str, priority_seats))} > 빈자리")
            logger.info("=" * 60)
            
            seat_selected = False
            selected_seat = None
            
            # 우선순위대로 타석 시도
            for seat_idx, seat_num in enumerate(priority_seats):
                if seat_selected:
                    break
                
                logger.info(f"━━━ [{seat_idx+1}/{len(priority_seats)}] {seat_num}번 타석 확인 중... ━━━")
                    
                try:
                    seat_selectors = [
                        f"//*[contains(text(), '{seat_num}번타석예약')]",
                        f"//button[contains(text(), '{seat_num}번타석')]",
                        f"//a[contains(text(), '{seat_num}번타석')]",
                    ]
                    
                    for sel_idx, selector in enumerate(seat_selectors):
                        if seat_selected:
                            break
                            
                        try:
                            logger.info(f"  selector [{sel_idx+1}/{len(seat_selectors)}]: {selector}")
                            seat_elements = self.driver.find_elements(By.XPATH, selector)
                            logger.info(f"  → {len(seat_elements)}개 요소 발견")
                            
                            for elem_idx, element in enumerate(seat_elements):
                                try:
                                    if element.is_displayed() and element.is_enabled():
                                        element_text = element.text
                                        logger.info(f"    [{elem_idx+1}] 발견: '{element_text}'")
                                        
                                        if any(keyword in element_text for keyword in ['예약불가', '마감', '불가능', '종료']):
                                            logger.warning(f"    ⚠️  {seat_num}번 타석: 예약 불가능 ('{element_text}')")
                                            break
                                        
                                        logger.info(f"    ✅ {seat_num}번 타석 클릭 시도...")
                                        element.click()
                                        logger.info(f"  ✅✅ {seat_num}번 타석 선택 성공!")
                                        time.sleep(2)
                                        seat_selected = True
                                        selected_seat = seat_num
                                        break
                                except Exception as e:
                                    logger.debug(f"    요소 처리 실패: {str(e)}")
                            
                            if seat_selected:
                                break
                                
                        except Exception as e:
                            logger.debug(f"  selector 실패: {str(e)}")
                            continue
                        
                except Exception as e:
                    logger.warning(f"  {seat_num}번 타석 확인 실패: {str(e)}")
                
                if not seat_selected:
                    logger.info(f"  ❌ {seat_num}번 타석 선택 실패\n")
            
            # 빈자리 찾기
            if not seat_selected:
                logger.warning("⚠️  우선순위 타석 모두 불가능")
                logger.info("━━━ 빈자리 검색 중... ━━━")
                
                try:
                    all_seats = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), '번타석예약')]"
                    )
                    
                    logger.info(f"총 {len(all_seats)}개 타석 발견")
                    
                    for idx, seat in enumerate(all_seats):
                        try:
                            if seat.is_displayed() and seat.is_enabled():
                                seat_text = seat.text
                                logger.info(f"  [{idx+1}/{len(all_seats)}] '{seat_text}' 확인 중...")
                                
                                if not any(keyword in seat_text for keyword in ['예약불가', '마감', '불가능', '종료']):
                                    logger.info(f"  ✅ 예약 가능한 타석 발견!")
                                    seat.click()
                                    logger.info(f"✅ 빈자리 선택 성공: {seat_text}")
                                    time.sleep(2)
                                    seat_selected = True
                                    selected_seat = seat_text
                                    break
                                else:
                                    logger.info(f"  ⚠️  '{seat_text}' - 예약 불가")
                        except Exception as e:
                            logger.debug(f"  타석 {idx+1} 처리 실패: {str(e)}")
                            continue
                    
                except Exception as e:
                    logger.error(f"❌ 빈자리 검색 실패: {str(e)}")
            
            if not seat_selected:
                logger.error("❌ 예약 가능한 타석이 없습니다!")
                return False
            
            # 확인 버튼
            try:
                logger.info("예약 확인 버튼 클릭 중...")
                time.sleep(2)
                
                confirm_button_selectors = [
                    "//button[contains(text(), '예약')]",
                    "//button[contains(text(), '확인')]",
                    "//button[contains(text(), '예약하기')]",
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
                    logger.warning("⚠️  확인 버튼 없음 - 타석 선택으로 예약 완료된 것으로 추정")
                
            except Exception as e:
                logger.warning(f"⚠️  확인 버튼 처리 중 경고: {str(e)}")
            
            # 최종 확인
            try:
                time.sleep(2)
                final_confirm = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '동의') or contains(text(), '최종확인')]"
                )
                final_confirm.click()
                logger.info("✅ 최종 확인 완료")
                time.sleep(2)
            except:
                logger.info("ℹ️  최종 확인 팝업 없음")
            
            # 결과
            logger.info("=" * 60)
            logger.info("🎉 예약 프로세스 완료!")
            logger.info(f"📅 예약일: {tomorrow.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][weekday]}요일)")
            if weekday < 5:
                logger.info(f"⏰ 예약 시간: 12:00 (오후 12:00) - 평일")
            else:
                logger.info(f"⏰ 예약 시간: 13:00 (오후 1:00) - 주말")
            logger.info(f"🎯 예약 타석: {selected_seat}번")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"❌ 예약 중 오류: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            
            try:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                screenshot_path = f"error_{timestamp}.png"
                self.driver.save_screenshot(screenshot_path)
                logger.info(f"📸 스크린샷: {screenshot_path}")
            except:
                pass
            
            return False
    
    def find_available_slots(self):
        """현재 예약 가능한 모든 타석 찾기 (테스트용)"""
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
            
            logger.info("=" * 60)
            logger.info("🔍 예약 가능한 타석 검색 중...")
            logger.info("=" * 60)
            
            # 페이지 전체 텍스트 가져오기
            page_text = self.driver.page_source
            
            # 모든 시간대 요소 찾기
            all_time_elements = []
            time_patterns = [
                "//*[contains(text(), ':00')]",
                "//button[contains(text(), ':00')]",
                "//a[contains(text(), ':00')]",
            ]
            
            for pattern in time_patterns:
                try:
                    elements = self.driver.find_elements(By.XPATH, pattern)
                    all_time_elements.extend(elements)
                except:
                    continue
            
            # 중복 제거
            unique_times = set()
            for elem in all_time_elements:
                try:
                    if elem.is_displayed():
                        text = elem.text.strip()
                        if ':' in text and len(text) < 20:
                            unique_times.add(text)
                except:
                    continue
            
            logger.info(f"발견된 시간대: {sorted(unique_times)}")
            logger.info("")
            
            # 각 시간대별로 예약 가능한 타석 확인
            available_slots = []
            
            for time_text in sorted(unique_times):
                logger.info(f"━━━ {time_text} 확인 중... ━━━")
                
                try:
                    # 시간대 클릭
                    time_elem = None
                    for pattern in time_patterns:
                        try:
                            elements = self.driver.find_elements(By.XPATH, pattern)
                            for elem in elements:
                                if elem.is_displayed() and elem.text.strip() == time_text:
                                    time_elem = elem
                                    break
                            if time_elem:
                                break
                        except:
                            continue
                    
                    if time_elem:
                        try:
                            time_elem.click()
                            logger.info(f"  ✅ {time_text} 클릭 성공")
                            time.sleep(2)
                        except:
                            logger.info(f"  ⚠️  {time_text} 클릭 실패")
                            continue
                    else:
                        logger.info(f"  ⚠️  {time_text} 요소를 찾을 수 없음")
                        continue
                    
                    # 타석 찾기
                    seat_elements = self.driver.find_elements(
                        By.XPATH, 
                        "//*[contains(text(), '번타석') or contains(text(), '타석')]"
                    )
                    
                    time_available_seats = []
                    
                    for seat in seat_elements:
                        try:
                            if seat.is_displayed():
                                seat_text = seat.text.strip()
                                
                                # "예약불가", "마감" 등이 없으면 예약 가능
                                if ('번타석' in seat_text or '타석' in seat_text) and \
                                   not any(keyword in seat_text for keyword in ['예약불가', '마감', '불가능', '종료', '대기']):
                                    time_available_seats.append(seat_text)
                        except:
                            continue
                    
                    if time_available_seats:
                        logger.info(f"  ✅ 예약 가능: {', '.join(time_available_seats)}")
                        available_slots.append({
                            'time': time_text,
                            'seats': time_available_seats
                        })
                    else:
                        logger.info(f"  ❌ 예약 가능한 타석 없음")
                    
                    logger.info("")
                    
                except Exception as e:
                    logger.debug(f"  오류: {str(e)}")
                    continue
            
            # 결과 요약
            logger.info("=" * 60)
            logger.info("📊 예약 가능 타석 요약")
            logger.info("=" * 60)
            
            if available_slots:
                logger.info(f"총 {len(available_slots)}개 시간대에 예약 가능")
                logger.info("")
                
                for idx, slot in enumerate(available_slots, 1):
                    logger.info(f"{idx}. {slot['time']}")
                    for seat in slot['seats']:
                        logger.info(f"   - {seat}")
                    logger.info("")
                
                # 가장 빠른 예약
                first_slot = available_slots[0]
                logger.info("=" * 60)
                logger.info("🎯 가장 빠른 예약 가능 시간")
                logger.info("=" * 60)
                logger.info(f"시간: {first_slot['time']}")
                logger.info(f"타석: {', '.join(first_slot['seats'])}")
                logger.info("=" * 60)
                
            else:
                logger.warning("❌ 현재 예약 가능한 타석이 없습니다")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 예약 가능 타석 검색 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def run(self, wait_for_midnight=False, find_mode=False):
        """예약 봇 실행"""
        try:
            logger.info("=" * 60)
            if find_mode:
                logger.info("🔍 예약 가능 타석 검색 모드")
            else:
                logger.info("🏌️  골프 자동 예약 시작")
            logger.info("=" * 60)
            
            if not self.setup_driver():
                return False
            
            if not self.naver_login():
                logger.error("❌ 로그인 실패")
                return False
            
            # 0번 모드: 예약 가능 타석 찾기
            if find_mode:
                logger.info("🔍 현재 예약 가능한 타석을 찾습니다...")
                success = self.find_available_slots()
                time.sleep(10)  # 결과 확인 시간
                return success
            
            # 예약 페이지로 이동 (자정 전에 미리 준비)
            if wait_for_midnight:
                booking_url = (
                    "https://map.naver.com/p/search/%EB%A9%94%EC%9D%B4%EC%A0%80"
                    "%EA%B3%A8%ED%94%84%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8/"
                    "place/1076834793?placePath=/ticket"
                )
                logger.info("🔗 예약 페이지로 미리 이동...")
                self.driver.get(booking_url)
                time.sleep(2)
                
                # 자정까지 대기
                self.wait_until_midnight()
            
            logger.info("🎯 예약 시도 시작!")
            success = self.book_golf_slot()
            
            if success:
                logger.info("✅ 예약 완료!")
                time.sleep(5)
            else:
                logger.error("❌ 예약 실패")
            
            return success
            
        except Exception as e:
            logger.error(f"❌ 오류: {str(e)}")
            return False
            
        finally:
            if self.driver:
                logger.info("🔚 브라우저 종료")
                time.sleep(3)
                self.driver.quit()


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
    """스케줄된 예약"""
    config = load_config()
    bot = GolfBookingBot(config)
    bot.run(wait_for_midnight=True)  # 자정까지 대기


def main():
    """메인 함수"""
    print("=" * 60)
    print("🏌️  골프 자동 예약 프로그램 (자정 최적화)")
    print("=" * 60)
    print("📌 타석 우선순위: 11 > 7 > 8 > 9 > 10 > 빈자리")
    print("📌 평일: 12:00 / 주말: 13:00")
    print("📌 자정에 정확히 맞춰서 예약 시도")
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
        print("✅ config.json 생성 완료")
        return
    
    print("실행 모드:")
    print("0. 예약 가능 타석 찾기 (테스트용) 🔍")
    print("1. 즉시 실행 (테스트)")
    print("2. 자정 예약 (오늘 자정에 자동 예약)")
    print("3. 매일 자정 예약 (스케줄)")
    print()
    
    choice = input("선택 (0-3): ").strip()
    
    if choice == '0':
        logger.info("🔍 예약 가능 타석 찾기 모드")
        print()
        print("=" * 60)
        print("현재 예약 가능한 타석을 찾습니다...")
        print("잠시만 기다려주세요 (약 30초~1분 소요)")
        print("=" * 60)
        print()
        config = load_config()
        bot = GolfBookingBot(config)
        bot.run(wait_for_midnight=False, find_mode=True)
        
    elif choice == '1':
        logger.info("즉시 실행 모드")
        config = load_config()
        bot = GolfBookingBot(config)
        bot.run(wait_for_midnight=False, find_mode=False)
        
    elif choice == '2':
        logger.info("자정 예약 모드")
        config = load_config()
        bot = GolfBookingBot(config)
        bot.run(wait_for_midnight=True, find_mode=False)
        
    elif choice == '3':
        logger.info("매일 자정 예약 모드")
        # 매일 23:59:00에 시작 (자정 1분 전)
        schedule.every().day.at("23:59:00").do(schedule_booking)
        
        print("✅ 스케줄 등록 완료")
        print("매일 23:59:00에 시작해서 자정에 정확히 예약합니다")
        print("종료: Ctrl+C")
        print()
        
        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        print("잘못된 선택")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n프로그램 종료")
    except Exception as e:
        logger.error(f"오류: {str(e)}")
