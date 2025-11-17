#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
메이저골프아카데미 자동 예약 프로그램 (최종 버전)
- 0번: 가장 빠른 타석 즉시 예약 (테스트용)
- 1번: 내일 타석 즉시 예약 (테스트용)
- 2번: 매일 자정 내일 타석 자동 예약 (실전용)
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
        """로그인 쿠키 저장 (나중에 재사용 가능)"""
        try:
            import pickle
            cookies = self.driver.get_cookies()
            with open('naver_cookies.pkl', 'wb') as f:
                pickle.dump(cookies, f)
            logger.info("✅ 쿠키 저장 완료")
        except Exception as e:
            logger.warning(f"⚠️  쿠키 저장 실패: {str(e)}")
    
    def naver_login(self):
        """네이버 로그인 - 무조건 수동 로그인 (ID 1초, PW 2초)"""
        try:
            logger.info("=" * 60)
            logger.info("🔐 네이버 로그인 시작 (수동 입력)")
            logger.info("=" * 60)
            
            logger.info("네이버 로그인 페이지 접속...")
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
                
                # ID 입력 (1초)
                id_input.clear()
                time.sleep(0.2)
                
                user_id = self.config['user_id']
                delay_per_char = 1.0 / len(user_id) if len(user_id) > 0 else 0.1
                
                for char in user_id:
                    id_input.send_keys(char)
                    time.sleep(delay_per_char)
                
                time.sleep(0.3)
                
                # PW 입력 (2초)
                pw_input.clear()
                time.sleep(0.2)
                
                user_pw = self.config['user_pw']
                delay_per_char = 2.0 / len(user_pw) if len(user_pw) > 0 else 0.1
                
                for char in user_pw:
                    pw_input.send_keys(char)
                    time.sleep(delay_per_char)
                
                time.sleep(0.5)
                
                logger.info("✅ 로그인 정보 입력 완료 (ID: 1초, PW: 2초)")
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
                
                # 사람처럼 천천히 입력
                # ID 입력 (1초)
                id_input.clear()
                time.sleep(0.2)
                
                user_id = self.config['user_id']
                delay_per_char = 1.0 / len(user_id) if len(user_id) > 0 else 0.1
                
                for char in user_id:
                    id_input.send_keys(char)
                    time.sleep(delay_per_char)
                
                time.sleep(0.5)
                
                # PW 입력 (2초)
                pw_input.clear()
                time.sleep(0.2)
                
                user_pw = self.config['user_pw']
                delay_per_char = 2.0 / len(user_pw) if len(user_pw) > 0 else 0.1
                
                for char in user_pw:
                    pw_input.send_keys(char)
                    time.sleep(delay_per_char)
                
                time.sleep(0.8)
                
                logger.info("✅ 로그인 정보 입력 완료 (ID: 1초, PW: 2초)")
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
    
    def send_kakao_notification(self, success, booking_info):
        """카카오톡 알림 전송"""
        if not self.config.get('enable_kakao', False):
            return
        
        try:
            from kakao_notification import KakaoNotifier
            
            kakao_api_key = self.config.get('kakao_rest_api_key')
            if not kakao_api_key:
                logger.warning("⚠️  카카오 REST API 키가 설정되지 않았습니다")
                return
            
            notifier = KakaoNotifier(kakao_api_key)
            
            if success:
                text = f"""🎉 골프 예약 성공!

📅 날짜: {booking_info['date']}
⏰ 시간: {booking_info['time']}
🎯 타석: {booking_info['seat']}

예약 완료 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            else:
                text = f"""❌ 골프 예약 실패

{booking_info.get('error', '알 수 없는 오류')}

시도 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
            
            notifier.send_message(text)
            logger.info("✅ 카카오톡 알림 전송 완료")
            
        except Exception as e:
            logger.warning(f"⚠️  카카오톡 알림 전송 실패: {str(e)}")
    
    def wait_until_midnight(self):
        """자정까지 대기 (준비 작업 시간 고려)"""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 준비 작업 소요 시간 (초)
        PREPARATION_TIME = 30  # 로그인 + 페이지 접속 + 타석 링크 검색
        
        # 자정 30초 전에 준비 완료되도록
        target_start_time = midnight - timedelta(seconds=PREPARATION_TIME)
        
        wait_seconds = (target_start_time - now).total_seconds()
        
        logger.info("=" * 60)
        logger.info("⏰ 자정 예약 타이밍 계산")
        logger.info("=" * 60)
        logger.info(f"현재 시각: {now.strftime('%H:%M:%S')}")
        logger.info(f"자정 시각: {midnight.strftime('%H:%M:%S')}")
        logger.info(f"준비 시간: {PREPARATION_TIME}초")
        logger.info(f"시작 시각: {target_start_time.strftime('%H:%M:%S')} (자정 {PREPARATION_TIME}초 전)")
        logger.info(f"대기 시간: {wait_seconds:.1f}초")
        logger.info("=" * 60)
        
        if wait_seconds > 0:
            logger.info("\n⏳ 시작 시각까지 대기 중...")
            
            # 1분 이상 남았으면 중간 알림
            if wait_seconds > 60:
                while wait_seconds > 60:
                    time.sleep(30)
                    wait_seconds = (target_start_time - datetime.now()).total_seconds()
                    remaining_minutes = int(wait_seconds / 60)
                    logger.info(f"⏰ {remaining_minutes}분 {int(wait_seconds % 60)}초 남음...")
            
            # 마지막 1분
            if wait_seconds > 0:
                logger.info(f"⏰ 마지막 {int(wait_seconds)}초...")
                time.sleep(max(0, wait_seconds))
            
            logger.info("\n" + "=" * 60)
            logger.info("🚀 준비 작업 시작! (자정 30초 전)")
            logger.info("=" * 60)
        else:
            logger.warning("⚠️  이미 시작 시각이 지났습니다. 즉시 시작합니다.")
    
    def wait_for_exact_midnight(self):
        """정확히 자정까지 대기 (준비 완료 후)"""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 이미 자정이 지났으면 리턴
        if now >= midnight:
            logger.info("✅ 자정 도달!")
            return
        
        wait_seconds = (midnight - now).total_seconds()
        
        if wait_seconds > 10:
            logger.warning(f"⚠️  자정까지 {wait_seconds:.1f}초 남음 (준비가 너무 빨리 끝남)")
            logger.info("자정까지 대기...")
            time.sleep(wait_seconds)
        elif wait_seconds > 0:
            logger.info(f"⏰ 자정까지 {wait_seconds:.1f}초...")
            time.sleep(wait_seconds)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 자정! 예약 시작!")
        logger.info("=" * 60)
    
    def _process_booking_steps(self):
        """예약 단계 처리: 다음 버튼 → 로그인 → 동의 → 확정"""
        try:
            # "다음" 버튼 클릭
            logger.info("🔍 '다음' 버튼 찾는 중...")
            
            next_button_selectors = [
                "//button[contains(@class, 'NextButton__btn_next')]",
                "//button[contains(text(), '다음')]",
                "//button[@data-click-code='nextbuttonview.request']",
            ]
            
            next_clicked = False
            for selector in next_button_selectors:
                try:
                    next_btn = self.driver.find_element(By.XPATH, selector)
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        next_btn.click()
                        logger.info("✅ '다음' 버튼 클릭")
                        time.sleep(3)
                        next_clicked = True
                        break
                except:
                    continue
            
            if not next_clicked:
                logger.warning("⚠️  '다음' 버튼을 찾지 못함")
            
            # 로그인 페이지 확인 및 처리
            time.sleep(2)
            current_url = self.driver.current_url
            
            if 'nid.naver.com' in current_url or 'login' in current_url.lower():
                logger.info("=" * 60)
                logger.info("🔐 예약 페이지에서 로그인 요청됨")
                logger.info("=" * 60)
                
                try:
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.ID, "id"))
                    )
                    pw_input = self.driver.find_element(By.ID, "pw")
                    logger.info("✅ 로그인 폼 확인")
                    
                    logger.info("로그인 정보 입력 중...")
                    id_input.clear()
                    time.sleep(0.3)
                    
                    user_id = self.config['user_id']
                    delay_per_char = 1.0 / len(user_id) if len(user_id) > 0 else 0.1
                    for char in user_id:
                        id_input.send_keys(char)
                        time.sleep(delay_per_char)
                    
                    time.sleep(0.5)
                    
                    pw_input.clear()
                    time.sleep(0.3)
                    
                    user_pw = self.config['user_pw']
                    delay_per_char = 2.0 / len(user_pw) if len(user_pw) > 0 else 0.1
                    for char in user_pw:
                        pw_input.send_keys(char)
                        time.sleep(delay_per_char)
                    
                    time.sleep(0.8)
                    logger.info("✅ 로그인 정보 입력 완료 (ID: 1초, PW: 2초)")
                    
                    # 로그인 버튼
                    logger.info("🔍 로그인 버튼 찾는 중...")
                    
                    login_button_selectors = [
                        (By.ID, "log.login"),
                        (By.XPATH, "//button[contains(text(), '로그인')]"),
                        (By.XPATH, "//input[@type='submit']"),
                        (By.XPATH, "//button[@type='submit']"),
                        (By.XPATH, "//*[contains(@class, 'btn_login')]"),
                    ]
                    
                    login_btn_found = False
                    for by_method, selector in login_button_selectors:
                        try:
                            login_btn = self.driver.find_element(by_method, selector)
                            if login_btn.is_displayed():
                                logger.info(f"✅ 로그인 버튼 발견")
                                login_btn.click()
                                logger.info("✅ 로그인 버튼 클릭")
                                time.sleep(5)
                                login_btn_found = True
                                break
                        except:
                            continue
                    
                    if not login_btn_found:
                        logger.error("❌ 로그인 버튼을 찾을 수 없습니다")
                        return False
                    
                    # 캡챠 체크
                    try:
                        captcha = self.driver.find_element(By.ID, "captcha")
                        logger.warning("⚠️  캡챠가 나타났습니다!")
                        logger.warning("브라우저 창에서 캡챠를 입력해주세요 (최대 90초 대기)")
                        
                        for i in range(18):
                            time.sleep(5)
                            try:
                                current_url = self.driver.current_url
                                if 'nid.naver.com' not in current_url:
                                    logger.info("✅ 캡챠 통과! 로그인 성공!")
                                    break
                            except:
                                pass
                    except NoSuchElementException:
                        logger.info("✅ 예약 페이지 로그인 성공!")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ 로그인 처리 실패: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return False
            
            # "동의하고 예약하기" 버튼
            try:
                time.sleep(1)
                logger.info("🔍 '동의하고 예약하기' 버튼 찾는 중...")
                
                agree_button_selectors = [
                    "//button[@data-click-code='submitbutton.submit']",
                    "//button[contains(@class, 'btn_request')]",
                    "//button[contains(text(), '동의하고 예약하기')]",
                ]
                
                agree_clicked = False
                for selector in agree_button_selectors:
                    try:
                        agree_btn = self.driver.find_element(By.XPATH, selector)
                        if agree_btn.is_displayed() and agree_btn.is_enabled():
                            agree_btn.click()
                            logger.info("✅ '동의하고 예약하기' 버튼 클릭")
                            time.sleep(3)
                            agree_clicked = True
                            break
                    except:
                        continue
                
                if not agree_clicked:
                    logger.error("❌ '동의하고 예약하기' 버튼을 찾지 못함")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ '동의하고 예약하기' 버튼 처리 실패: {str(e)}")
                return False
            
            # 예약 확정 확인
            try:
                time.sleep(2)
                logger.info("🔍 예약 확정 여부 확인 중...")
                
                confirmation_selectors = [
                    "//strong[contains(@class, 'popup_tit')][contains(text(), '예약이 확정')]",
                    "//*[contains(text(), '예약이 확정되었습니다')]",
                    "//strong[contains(text(), '예약이 확정')]",
                ]
                
                confirmed = False
                for selector in confirmation_selectors:
                    try:
                        confirm_elem = self.driver.find_element(By.XPATH, selector)
                        if confirm_elem.is_displayed():
                            confirm_text = confirm_elem.text
                            logger.info(f"✅ 확인: '{confirm_text}'")
                            confirmed = True
                            break
                    except:
                        continue
                
                if not confirmed:
                    try:
                        page_source = self.driver.page_source
                        if '예약이 확정' in page_source or '확정되었습니다' in page_source:
                            logger.info("✅ 페이지에서 '예약 확정' 메시지 발견")
                            confirmed = True
                    except:
                        pass
                
                if not confirmed:
                    logger.error("❌ 예약 실패: '예약이 확정되었습니다' 메시지를 찾을 수 없음")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"❌ 예약 확정 확인 실패: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 예약 단계 처리 실패: {str(e)}")
            return False
    
    def apply_cookies_to_domain(self, target_url):
        """특정 도메인으로 이동 후 쿠키 재적용"""
        try:
            import pickle
            if not os.path.exists('naver_cookies.pkl'):
                logger.warning("⚠️  쿠키 파일이 없습니다")
                return False
            
            # 쿠키 로드
            with open('naver_cookies.pkl', 'rb') as f:
                cookies = pickle.load(f)
            
            # 타겟 도메인으로 먼저 이동
            logger.info(f"🔗 {target_url[:60]}... 로 이동 중...")
            self.driver.get(target_url)
            time.sleep(2)
            
            # 쿠키 적용
            applied = 0
            for cookie in cookies:
                try:
                    # 도메인 호환성 체크
                    if 'domain' in cookie:
                        # .naver.com 쿠키는 모든 네이버 서브도메인에서 작동
                        if 'naver.com' in cookie['domain']:
                            self.driver.add_cookie(cookie)
                            applied += 1
                except Exception as e:
                    logger.debug(f"쿠키 적용 실패: {cookie.get('name', 'unknown')} - {str(e)}")
            
            if applied > 0:
                logger.info(f"✅ {applied}개 쿠키 적용 완료")
                
                # 페이지 새로고침으로 쿠키 적용
                self.driver.refresh()
                time.sleep(2)
                
                # 로그인 상태 확인
                if self._check_login_status():
                    logger.info("✅ 로그인 상태 확인됨")
                    return True
                else:
                    logger.warning("⚠️  쿠키 적용했으나 로그인 상태 아님")
                    return False
            else:
                logger.warning("⚠️  적용 가능한 쿠키가 없습니다")
                return False
            
        except Exception as e:
            logger.warning(f"⚠️  쿠키 재적용 실패: {str(e)}")
            return False
    
    def _check_login_status(self):
        """로그인 상태 확인"""
        try:
            # 로그인 버튼이 보이면 로그아웃 상태
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '로그인')]")
                if login_btn.is_displayed():
                    return False
            except:
                pass
            
            # 페이지 소스에서 확인
            page_source = self.driver.page_source
            
            # 로그인 관련 요소가 있으면 로그아웃 상태
            if '로그인이 필요' in page_source or '로그인하세요' in page_source:
                return False
            
            # 기본적으로 로그인 상태로 가정
            return True
            
        except:
            # 확인 불가시 로그인 상태로 가정
            return True
    
    def book_earliest_slot(self):
        """0번 모드: 여러 타석을 순회하며 가장 빠른 예약 가능 타석 찾기"""
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
                return False, {}
            
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
            logger.info("🔍 타석 링크 검색 및 순회")
            logger.info("=" * 60)
            
            time.sleep(2)
            
            # 타석 예약 링크 찾기
            try:
                # "번타석예약" 텍스트를 가진 링크들 찾기
                booth_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, 'booking.naver.com')][contains(., '번타석')]"
                )
                
                if not booth_links:
                    # 다른 패턴 시도
                    booth_links = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(., '번타석예약')]"
                    )
                
                logger.info(f"발견된 타석 링크: {len(booth_links)}개")
                
                # 링크 정보 추출
                booth_infos = []
                for link in booth_links:
                    try:
                        booth_text = link.text.strip()
                        booth_href = link.get_attribute('href')
                        
                        if booth_text and '번타석' in booth_text:
                            booth_infos.append({
                                'text': booth_text,
                                'href': booth_href,
                                'element': link
                            })
                            logger.info(f"  - {booth_text}: {booth_href[:80]}...")
                    except:
                        continue
                
                if not booth_infos:
                    logger.error("❌ 타석 링크를 찾을 수 없습니다")
                    return False, {'error': '타석 링크 없음'}
                
                logger.info(f"\n총 {len(booth_infos)}개 타석 확인 예정")
                
            except Exception as e:
                logger.error(f"❌ 타석 링크 검색 실패: {str(e)}")
                return False, {'error': str(e)}
            
            # 각 타석 확인
            today = datetime.now()
            found_slot = None
            
            for booth_idx, booth_info in enumerate(booth_infos):
                if found_slot:
                    break
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🎯 {booth_info['text']} 확인 중... ({booth_idx + 1}/{len(booth_infos)})")
                logger.info(f"{'=' * 60}")
                
                try:
                    # 타석 링크로 이동
                    logger.info(f"🔗 {booth_info['text']} 페이지로 이동...")
                    
                    # 쿠키를 유지하며 예약 페이지로 이동
                    cookie_success = self.apply_cookies_to_domain(booth_info['href'])
                    
                    # 쿠키 로그인 실패 시 현재 세션 유지
                    if not cookie_success:
                        logger.warning("⚠️  쿠키 로그인 실패 - 현재 세션 상태로 진행")
                        # 이미 메인에서 로그인했으므로 세션은 유지됨
                        self.driver.get(booth_info['href'])
                        time.sleep(2)
                    
                    # 로그인 페이지로 리다이렉트 되었는지 확인
                    current_url = self.driver.current_url
                    if 'nid.naver.com/nidlogin' in current_url or 'login' in current_url.lower():
                        logger.error("❌ 로그인 페이지로 리다이렉트됨 - 로그인 필요")
                        logger.error("프로그램을 재시작하고 다시 로그인해주세요")
                        return False, {'error': '로그인 필요'}
                    
                    time.sleep(1)
                    
                    # 3일간 확인
                    for day_offset in range(3):
                        if found_slot:
                            break
                        
                        target_date = today + timedelta(days=day_offset)
                        target_day = target_date.day
                        day_name = ["오늘", "내일", "모레"][day_offset]
                        
                        logger.info(f"\n  📅 {day_name} ({target_date.strftime('%Y-%m-%d')})")
                        
                        # 날짜 선택
                        if day_offset > 0:
                            try:
                                # 여러 패턴의 날짜 버튼 시도
                                date_selectors = [
                                    f"//button[text()='{target_day}']",
                                    f"//button[contains(text(), '{target_day}')]",
                                    f"//*[contains(@class, 'date')]//*[text()='{target_day}']",
                                ]
                                
                                date_selected = False
                                for selector in date_selectors:
                                    try:
                                        date_elements = self.driver.find_elements(By.XPATH, selector)
                                        for elem in date_elements:
                                            try:
                                                if elem.is_displayed():
                                                    elem_text = elem.text.strip()
                                                    if elem_text == str(target_day):
                                                        elem.click()
                                                        time.sleep(2)
                                                        date_selected = True
                                                        logger.info(f"    ✅ {target_day}일 선택")
                                                        break
                                            except:
                                                continue
                                        if date_selected:
                                            break
                                    except:
                                        continue
                                
                                if not date_selected:
                                    logger.info(f"    ℹ️  {target_day}일 선택 안됨 (기본값일 수 있음)")
                                    
                            except Exception as e:
                                logger.debug(f"    날짜 선택 오류: {str(e)}")
                        
                        # 시간대 확인
                        time.sleep(1.5)
                        
                        try:
                            # btn_time 클래스 버튼들 찾기
                            time_buttons = self.driver.find_elements(
                                By.XPATH,
                                "//button[contains(@class, 'btn_time')]"
                            )
                            
                            logger.info(f"    시간 버튼: {len(time_buttons)}개 발견")
                            
                            available_times = []
                            for btn in time_buttons:
                                try:
                                    is_disabled = btn.get_attribute('disabled')
                                    class_attr = btn.get_attribute('class') or ''
                                    has_unselectable = 'unselectable' in class_attr
                                    is_visible = btn.is_displayed()
                                    time_text = btn.text.strip()
                                    
                                    logger.debug(f"      {time_text}: disabled={is_disabled}, unselectable={has_unselectable}, visible={is_visible}")
                                    
                                    # 예약 가능 조건: disabled가 없고, unselectable 클래스가 없고, 보이는 상태
                                    if not is_disabled and not has_unselectable and is_visible and ':' in time_text:
                                        available_times.append((time_text, btn))
                                        logger.info(f"      ✅ {time_text}")
                                    else:
                                        reason = []
                                        if is_disabled:
                                            reason.append("disabled")
                                        if has_unselectable:
                                            reason.append("unselectable")
                                        if reason:
                                            logger.debug(f"      ❌ {time_text} 예약 불가능 ({', '.join(reason)})")
                                except Exception as e:
                                    logger.debug(f"      버튼 처리 실패: {str(e)}")
                                    continue
                            
                            logger.info(f"    예약 가능: {[t[0] for t in available_times]}")
                            
                            if available_times:
                                # 가장 빠른 시간 선택
                                first_time_text, first_time_btn = available_times[0]
                                
                                found_slot = {
                                    'booth_text': booth_info['text'],
                                    'booth_idx': booth_idx + 1,
                                    'booth_href': booth_info['href'],
                                    'date': target_date.strftime('%Y-%m-%d'),
                                    'day_name': day_name,
                                    'time': first_time_text,
                                    'time_btn': first_time_btn
                                }
                                
                                logger.info(f"\n{'=' * 60}")
                                logger.info(f"🎉 예약 가능 타석 발견!")
                                logger.info(f"{'=' * 60}")
                                logger.info(f"타석: {booth_info['text']}")
                                logger.info(f"날짜: {target_date.strftime('%Y-%m-%d')} ({day_name})")
                                logger.info(f"시간: {first_time_text}")
                                logger.info(f"{'=' * 60}")
                                break
                                
                        except Exception as e:
                            logger.warning(f"    시간대 확인 실패: {str(e)}")
                    
                    # 다음 타석 확인을 위해 메인 페이지로 돌아가기
                    if not found_slot and booth_idx < len(booth_infos) - 1:
                        logger.info(f"\n  ⬅️  메인 페이지로 복귀...")
                        self.driver.get(booking_url)
                        time.sleep(2)
                        
                        # iframe 다시 전환
                        try:
                            self.wait.until(EC.frame_to_be_available_and_switch_to_it("entryIframe"))
                            
                            # 예약 탭 클릭
                            try:
                                booking_tab = self.driver.find_element(By.XPATH, "//a[contains(text(), '예약')]")
                                booking_tab.click()
                                time.sleep(1)
                            except:
                                pass
                        except:
                            logger.warning("    iframe 재전환 실패")
                    
                except Exception as e:
                    logger.warning(f"  {booth_info['text']} 확인 실패: {str(e)}")
                    continue
            
            if not found_slot:
                logger.error("=" * 60)
                logger.error("❌ 모든 타석에서 예약 가능한 시간이 없습니다!")
                logger.error("=" * 60)
                return False, {'error': '예약 가능 타석 없음'}
            
            # 예약 진행
            logger.info(f"\n🎯 예약을 시작합니다...")
            
            try:
                found_slot['time_btn'].click()
                logger.info(f"✅ {found_slot['time']} 선택")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ 시간 선택 실패: {str(e)}")
                return False, found_slot
            
            # "다음" 버튼 클릭
            try:
                logger.info("🔍 '다음' 버튼 찾는 중...")
                
                next_button_selectors = [
                    "//button[contains(@class, 'NextButton__btn_next')]",
                    "//button[contains(text(), '다음')]",
                    "//button[@data-click-code='nextbuttonview.request']",
                ]
                
                next_clicked = False
                for selector in next_button_selectors:
                    try:
                        next_btn = self.driver.find_element(By.XPATH, selector)
                        if next_btn.is_displayed() and next_btn.is_enabled():
                            next_btn.click()
                            logger.info("✅ '다음' 버튼 클릭")
                            time.sleep(3)
                            next_clicked = True
                            break
                    except:
                        continue
                
                if not next_clicked:
                    logger.warning("⚠️  '다음' 버튼을 찾지 못함")
                
                # "다음" 버튼 후 로그인 페이지 확인
                time.sleep(2)
                current_url = self.driver.current_url
                
                if 'nid.naver.com' in current_url or 'login' in current_url.lower():
                    logger.info("=" * 60)
                    logger.info("🔐 예약 페이지에서 로그인 요청됨")
                    logger.info("=" * 60)
                    
                    # ID/PW 입력 폼 확인
                    try:
                        id_input = self.wait.until(
                            EC.presence_of_element_located((By.ID, "id"))
                        )
                        pw_input = self.driver.find_element(By.ID, "pw")
                        logger.info("✅ 로그인 폼 확인")
                        
                        # 사람처럼 천천히 입력
                        logger.info("로그인 정보 입력 중...")
                        id_input.clear()
                        time.sleep(0.3)
                        
                        user_id = self.config['user_id']
                        delay_per_char = 1.0 / len(user_id) if len(user_id) > 0 else 0.1
                        for char in user_id:
                            id_input.send_keys(char)
                            time.sleep(delay_per_char)
                        
                        time.sleep(0.5)
                        
                        pw_input.clear()
                        time.sleep(0.3)
                        
                        user_pw = self.config['user_pw']
                        delay_per_char = 2.0 / len(user_pw) if len(user_pw) > 0 else 0.1
                        for char in user_pw:
                            pw_input.send_keys(char)
                            time.sleep(delay_per_char)
                        
                        time.sleep(0.8)
                        logger.info("✅ 로그인 정보 입력 완료 (ID: 1초, PW: 2초)")
                        
                        # 로그인 버튼 찾기 (여러 패턴 시도)
                        logger.info("🔍 로그인 버튼 찾는 중...")
                        
                        login_button_selectors = [
                            (By.ID, "log.login"),
                            (By.XPATH, "//button[contains(text(), '로그인')]"),
                            (By.XPATH, "//input[@type='submit']"),
                            (By.XPATH, "//button[@type='submit']"),
                            (By.XPATH, "//*[contains(@class, 'btn_login')]"),
                            (By.XPATH, "//a[contains(text(), '로그인')]"),
                        ]
                        
                        login_btn_found = False
                        for by_method, selector in login_button_selectors:
                            try:
                                login_btn = self.driver.find_element(by_method, selector)
                                if login_btn.is_displayed():
                                    logger.info(f"✅ 로그인 버튼 발견: {selector}")
                                    login_btn.click()
                                    logger.info("✅ 로그인 버튼 클릭")
                                    time.sleep(5)
                                    login_btn_found = True
                                    break
                            except Exception as e:
                                logger.debug(f"버튼 찾기 실패 ({selector}): {str(e)}")
                                continue
                        
                        if not login_btn_found:
                            logger.error("❌ 로그인 버튼을 찾을 수 없습니다")
                            logger.info("페이지 HTML 일부:")
                            try:
                                page_html = self.driver.page_source
                                # 로그인 관련 부분만 출력
                                if '로그인' in page_html:
                                    idx = page_html.find('로그인')
                                    logger.info(page_html[max(0, idx-200):idx+200])
                            except:
                                pass
                            return False, found_slot
                        
                        # 캡챠 체크
                        try:
                            captcha = self.driver.find_element(By.ID, "captcha")
                            logger.warning("⚠️  캡챠가 나타났습니다!")
                            logger.warning("브라우저 창에서 캡챠를 입력해주세요 (최대 90초 대기)")
                            
                            for i in range(18):
                                time.sleep(5)
                                try:
                                    current_url = self.driver.current_url
                                    if 'nid.naver.com' not in current_url:
                                        logger.info("✅ 캡챠 통과! 로그인 성공!")
                                        break
                                except:
                                    pass
                        except NoSuchElementException:
                            # 캡챠 없음 - 로그인 성공
                            logger.info("✅ 예약 페이지 로그인 성공!")
                        
                        # 로그인 후 원래 페이지로 자동 이동되는지 확인
                        time.sleep(2)
                        
                    except Exception as e:
                        logger.error(f"❌ 로그인 처리 실패: {str(e)}")
                        import traceback
                        logger.error(traceback.format_exc())
                        return False, found_slot
                    
            except Exception as e:
                logger.warning(f"⚠️  '다음' 버튼 처리 중 오류: {str(e)}")
            
            # "동의하고 예약하기" 버튼 클릭
            try:
                time.sleep(1)
                logger.info("🔍 '동의하고 예약하기' 버튼 찾는 중...")
                
                agree_button_selectors = [
                    "//button[@data-click-code='submitbutton.submit']",
                    "//button[contains(@class, 'btn_request')]",
                    "//button[contains(text(), '동의하고 예약하기')]",
                ]
                
                agree_clicked = False
                for selector in agree_button_selectors:
                    try:
                        agree_btn = self.driver.find_element(By.XPATH, selector)
                        if agree_btn.is_displayed() and agree_btn.is_enabled():
                            agree_btn.click()
                            logger.info("✅ '동의하고 예약하기' 버튼 클릭")
                            time.sleep(3)  # 예약 처리 대기
                            agree_clicked = True
                            break
                    except:
                        continue
                
                if not agree_clicked:
                    logger.error("❌ '동의하고 예약하기' 버튼을 찾지 못함")
                    return False, found_slot
                    
            except Exception as e:
                logger.error(f"❌ '동의하고 예약하기' 버튼 처리 실패: {str(e)}")
                return False, found_slot
            
            # 예약 확정 확인
            try:
                time.sleep(2)
                logger.info("🔍 예약 확정 여부 확인 중...")
                
                # "예약이 확정되었습니다" 텍스트 찾기
                confirmation_selectors = [
                    "//strong[contains(@class, 'popup_tit')][contains(text(), '예약이 확정')]",
                    "//*[contains(text(), '예약이 확정되었습니다')]",
                    "//strong[contains(text(), '예약이 확정')]",
                ]
                
                confirmed = False
                for selector in confirmation_selectors:
                    try:
                        confirm_elem = self.driver.find_element(By.XPATH, selector)
                        if confirm_elem.is_displayed():
                            confirm_text = confirm_elem.text
                            logger.info(f"✅ 확인: '{confirm_text}'")
                            confirmed = True
                            break
                    except:
                        continue
                
                if not confirmed:
                    # 페이지 전체에서 "확정" 텍스트 검색
                    try:
                        page_source = self.driver.page_source
                        if '예약이 확정' in page_source or '확정되었습니다' in page_source:
                            logger.info("✅ 페이지에서 '예약 확정' 메시지 발견")
                            confirmed = True
                    except:
                        pass
                
                if not confirmed:
                    logger.error("❌ 예약 실패: '예약이 확정되었습니다' 메시지를 찾을 수 없음")
                    logger.error("예약이 완료되지 않았거나 오류가 발생했을 수 있습니다")
                    return False, found_slot
                
            except Exception as e:
                logger.error(f"❌ 예약 확정 확인 실패: {str(e)}")
                return False, found_slot
            
            # 결과
            logger.info("\n" + "=" * 60)
            logger.info("🎉 예약 완료!")
            logger.info("=" * 60)
            logger.info(f"📍 타석: {found_slot['booth_text']}")
            logger.info(f"📅 날짜: {found_slot['date']} ({found_slot['day_name']})")
            logger.info(f"⏰ 시간: {found_slot['time']}")
            logger.info("=" * 60)
            
            time.sleep(5)
            return True, found_slot
            
        except Exception as e:
            logger.error(f"❌ 예약 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {'error': str(e)}
        """0번 모드: 여러 타석을 순회하며 가장 빠른 예약 가능 타석 찾기"""
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
                return False, {}
            
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
            logger.info("🔍 타석 리스트에서 예약 가능한 타석 검색")
            logger.info("=" * 60)
            
            time.sleep(2)
            
            # 타석 리스트 찾기
            try:
                # "1번타석에약", "2번타석에약" 같은 텍스트를 가진 요소들 찾기
                booth_selectors = [
                    "//*[contains(text(), '번타석')]",
                    "//a[contains(text(), '번타석')]",
                    "//button[contains(text(), '번타석')]",
                    "//*[contains(@class, 'item')]//*[contains(text(), '번타석')]",
                ]
                
                all_booths = []
                for selector in booth_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        logger.info(f"타석 selector: {selector} → {len(elements)}개")
                        all_booths.extend(elements)
                    except Exception as e:
                        logger.debug(f"selector 실패: {str(e)}")
                        continue
                
                # 중복 제거 및 정렬
                unique_booths = []
                seen_texts = set()
                for booth in all_booths:
                    try:
                        booth_text = booth.text.strip()
                        if booth_text and '번타석' in booth_text and booth_text not in seen_texts:
                            seen_texts.add(booth_text)
                            unique_booths.append((booth_text, booth))
                            logger.info(f"  발견: {booth_text}")
                    except:
                        continue
                
                logger.info(f"\n총 {len(unique_booths)}개 타석 발견: {[b[0] for b in unique_booths]}")
                
                if not unique_booths:
                    logger.warning("⚠️  타석 리스트를 찾을 수 없습니다")
                    logger.info("페이지 구조 확인 필요 - 현재 날짜/시간으로 바로 진행")
                    # 타석 리스트 없이 바로 진행
                    return self._check_current_booth()
                
            except Exception as e:
                logger.error(f"타석 리스트 검색 실패: {str(e)}")
                return self._check_current_booth()
            
            # 각 타석을 클릭해서 확인
            found_slot = None
            today = datetime.now()
            
            for booth_idx, (booth_text, booth_elem) in enumerate(unique_booths):
                if found_slot:
                    break
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🎯 {booth_text} 확인 중... ({booth_idx + 1}/{len(unique_booths)})")
                logger.info(f"{'=' * 60}")
                
                try:
                    # 타석 클릭
                    booth_elem.click()
                    logger.info(f"✅ {booth_text} 클릭")
                    time.sleep(2)
                    
                    # 3일간 확인
                    for day_offset in range(3):
                        if found_slot:
                            break
                        
                        target_date = today + timedelta(days=day_offset)
                        target_day = target_date.day
                        day_name = ["오늘", "내일", "모레"][day_offset]
                        
                        logger.info(f"\n  📅 {day_name} ({target_date.strftime('%Y-%m-%d')})")
                        
                        # 날짜 선택
                        if day_offset > 0:
                            try:
                                date_elements = self.driver.find_elements(
                                    By.XPATH, 
                                    f"//button[text()='{target_day}']"
                                )
                                
                                for elem in date_elements:
                                    try:
                                        if elem.is_displayed():
                                            elem.click()
                                            time.sleep(1.5)
                                            logger.info(f"    ✅ {target_day}일 선택")
                                            break
                                    except:
                                        continue
                            except:
                                pass
                        
                        # 시간대 확인
                        time.sleep(1)
                        
                        try:
                            time_buttons = self.driver.find_elements(
                                By.XPATH,
                                "//button[contains(@class, 'btn_time')]"
                            )
                            
                            available_times = []
                            for btn in time_buttons:
                                try:
                                    is_disabled = btn.get_attribute('disabled')
                                    is_visible = btn.is_displayed()
                                    time_text = btn.text.strip()
                                    
                                    if not is_disabled and is_visible and ':' in time_text:
                                        available_times.append((time_text, btn))
                                except:
                                    continue
                            
                            logger.info(f"    예약 가능: {[t[0] for t in available_times]}")
                            
                            if available_times:
                                # 가장 빠른 시간 선택
                                first_time_text, first_time_btn = available_times[0]
                                
                                found_slot = {
                                    'booth_text': booth_text,
                                    'booth_idx': booth_idx + 1,
                                    'date': target_date.strftime('%Y-%m-%d'),
                                    'day_name': day_name,
                                    'time': first_time_text,
                                    'time_btn': first_time_btn
                                }
                                
                                logger.info(f"\n{'=' * 60}")
                                logger.info(f"🎉 예약 가능 타석 발견!")
                                logger.info(f"{'=' * 60}")
                                logger.info(f"타석: {booth_text}")
                                logger.info(f"날짜: {target_date.strftime('%Y-%m-%d')} ({day_name})")
                                logger.info(f"시간: {first_time_text}")
                                logger.info(f"{'=' * 60}")
                                break
                                
                        except Exception as e:
                            logger.debug(f"    시간대 확인 실패: {str(e)}")
                            
                except Exception as e:
                    logger.warning(f"  {booth_text} 확인 실패: {str(e)}")
                    continue
            
            if not found_slot:
                logger.error("=" * 60)
                logger.error("❌ 모든 타석에서 예약 가능한 시간이 없습니다!")
                logger.error("=" * 60)
                return False, {'error': '예약 가능 타석 없음'}
            
            # 예약 진행
            logger.info(f"\n🎯 예약을 시작합니다...")
            
            try:
                found_slot['time_btn'].click()
                logger.info(f"✅ {found_slot['time']} 선택")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ 시간 선택 실패: {str(e)}")
                return False, found_slot
            
            # 확인 버튼
            try:
                time.sleep(1)
                confirm_selectors = [
                    "//button[contains(text(), '예약')]",
                    "//button[contains(text(), '확인')]",
                ]
                
                for selector in confirm_selectors:
                    try:
                        btn = self.driver.find_element(By.XPATH, selector)
                        if btn.is_displayed():
                            btn.click()
                            logger.info("✅ 확인 버튼 클릭")
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
            
            # 최종 확인
            try:
                time.sleep(1)
                final = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '동의') or contains(text(), '최종')]"
                )
                final.click()
                logger.info("✅ 최종 확인")
                time.sleep(2)
            except:
                pass
            
            # 결과
            logger.info("\n" + "=" * 60)
            logger.info("🎉 예약 완료!")
            logger.info("=" * 60)
            logger.info(f"📍 타석: {found_slot['booth_text']}")
            logger.info(f"📅 날짜: {found_slot['date']} ({found_slot['day_name']})")
            logger.info(f"⏰ 시간: {found_slot['time']}")
            logger.info("=" * 60)
            
            time.sleep(5)
            return True, found_slot
            
        except Exception as e:
            logger.error(f"❌ 예약 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {'error': str(e)}
    
    def _check_current_booth(self):
        """타석 리스트 없이 현재 화면에서 바로 확인"""
        try:
            logger.info("현재 화면에서 바로 예약 가능 여부 확인...")
            
            today = datetime.now()
            
            for day_offset in range(3):
                target_date = today + timedelta(days=day_offset)
                target_day = target_date.day
                day_name = ["오늘", "내일", "모레"][day_offset]
                
                logger.info(f"\n📅 {day_name} ({target_date.strftime('%Y-%m-%d')})")
                
                if day_offset > 0:
                    try:
                        date_elem = self.driver.find_element(
                            By.XPATH,
                            f"//button[text()='{target_day}']"
                        )
                        date_elem.click()
                        time.sleep(1.5)
                        logger.info(f"✅ {target_day}일 선택")
                    except:
                        pass
                
                time.sleep(1)
                
                time_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(@class, 'btn_time')]"
                )
                
                available_times = []
                for btn in time_buttons:
                    try:
                        is_disabled = btn.get_attribute('disabled')
                        if not is_disabled and btn.is_displayed():
                            time_text = btn.text.strip()
                            if ':' in time_text:
                                available_times.append((time_text, btn))
                    except:
                        continue
                
                logger.info(f"예약 가능: {[t[0] for t in available_times]}")
                
                if available_times:
                    first_time_text, first_time_btn = available_times[0]
                    first_time_btn.click()
                    logger.info(f"✅ {first_time_text} 선택")
                    time.sleep(2)
                    
                    result = {
                        'booth_text': '기본 타석',
                        'date': target_date.strftime('%Y-%m-%d'),
                        'day_name': day_name,
                        'time': first_time_text
                    }
                    
                    logger.info("\n" + "=" * 60)
                    logger.info("🎉 예약 완료!")
                    logger.info("=" * 60)
                    logger.info(f"📅 날짜: {result['date']}")
                    logger.info(f"⏰ 시간: {result['time']}")
                    logger.info("=" * 60)
                    
                    return True, result
            
            return False, {'error': '예약 가능 시간 없음'}
            
        except Exception as e:
            logger.error(f"확인 실패: {str(e)}")
            return False, {'error': str(e)}
        """0번 모드: 여러 타석을 순회하며 가장 빠른 예약 가능 타석 찾기"""
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
                return False, {}
            
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
            logger.info("🔍 여러 타석을 순회하며 가장 빠른 예약 가능 타석 검색")
            logger.info("=" * 60)
            
            today = datetime.now()
            found_slot = None
            
            # 최대 15개 타석 확인 (충분히 많이)
            max_booths = 15
            
            for booth_idx in range(max_booths):
                if found_slot:
                    break
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🎯 타석 {booth_idx + 1} 확인 중...")
                logger.info(f"{'=' * 60}")
                
                # 3일간 확인 (오늘, 내일, 모레)
                for day_offset in range(3):
                    if found_slot:
                        break
                    
                    target_date = today + timedelta(days=day_offset)
                    target_day = target_date.day
                    day_name = ["오늘", "내일", "모레"][day_offset]
                    
                    logger.info(f"\n  📅 {day_name} ({target_date.strftime('%Y-%m-%d')}) 확인")
                    
                    # 날짜 선택 (오늘이 아닌 경우)
                    if day_offset > 0:
                        try:
                            date_selectors = [
                                f"//button[text()='{target_day}']",
                                f"//button[contains(text(), '{target_day}')]",
                            ]
                            
                            date_selected = False
                            for selector in date_selectors:
                                try:
                                    date_elements = self.driver.find_elements(By.XPATH, selector)
                                    for elem in date_elements:
                                        try:
                                            if elem.is_displayed():
                                                elem_text = elem.text.strip()
                                                if elem_text == str(target_day):
                                                    elem.click()
                                                    time.sleep(1.5)
                                                    date_selected = True
                                                    logger.info(f"    ✅ {target_day}일 선택")
                                                    break
                                        except:
                                            continue
                                    if date_selected:
                                        break
                                except:
                                    continue
                        except:
                            pass
                    
                    # 시간대 찾기
                    time.sleep(1)
                    
                    try:
                        time_buttons = self.driver.find_elements(
                            By.XPATH, 
                            "//button[contains(@class, 'btn_time')]"
                        )
                        
                        available_times = []
                        for btn in time_buttons:
                            try:
                                is_disabled = btn.get_attribute('disabled')
                                is_visible = btn.is_displayed()
                                time_text = btn.text.strip()
                                
                                if not is_disabled and is_visible and ':' in time_text:
                                    available_times.append((time_text, btn))
                            except:
                                continue
                        
                        logger.info(f"    시간대: {[t[0] for t in available_times]}")
                        
                        if not available_times:
                            logger.info(f"    ❌ 예약 가능 시간 없음")
                            continue
                        
                        # 가장 빠른 시간 선택
                        first_time_text, first_time_btn = available_times[0]
                        logger.info(f"    ✅ 가장 빠른 시간: {first_time_text}")
                        
                        # 예약 가능! 바로 저장
                        found_slot = {
                            'date': target_date.strftime('%Y-%m-%d'),
                            'day_name': day_name,
                            'time': first_time_text,
                            'booth': booth_idx + 1,
                            'time_btn': first_time_btn
                        }
                        
                        logger.info(f"\n{'=' * 60}")
                        logger.info(f"🎉 예약 가능 타석 발견!")
                        logger.info(f"{'=' * 60}")
                        logger.info(f"타석: {booth_idx + 1}번")
                        logger.info(f"날짜: {target_date.strftime('%Y-%m-%d')} ({day_name})")
                        logger.info(f"시간: {first_time_text}")
                        logger.info(f"{'=' * 60}")
                        break
                        
                    except Exception as e:
                        logger.warning(f"    시간대 확인 실패: {str(e)}")
                        continue
                
                # 예약 가능 타석을 찾았으면 종료
                if found_slot:
                    break
                
                # 못 찾았으면 뒤로가기 (다음 타석으로)
                if booth_idx < max_booths - 1:
                    try:
                        logger.info(f"\n  ⬅️  다음 타석으로 이동...")
                        
                        # 뒤로가기 버튼 찾기
                        back_button_selectors = [
                            "//button[contains(@class, 'BizItemHeader__ico_arrow')]",
                            "//*[contains(@class, 'BizItemHeader__ico_arrow')]",
                            "//button[contains(@class, 'ico_arrow')]",
                        ]
                        
                        back_clicked = False
                        for selector in back_button_selectors:
                            try:
                                back_btn = self.driver.find_element(By.XPATH, selector)
                                if back_btn.is_displayed():
                                    back_btn.click()
                                    time.sleep(2)
                                    back_clicked = True
                                    logger.info(f"    ✅ 뒤로가기 완료")
                                    break
                            except:
                                continue
                        
                        if not back_clicked:
                            logger.warning(f"    ⚠️  뒤로가기 버튼 없음 - 종료")
                            break
                            
                    except Exception as e:
                        logger.warning(f"    뒤로가기 실패: {str(e)}")
                        break
            
            if not found_slot:
                logger.error("=" * 60)
                logger.error("❌ 모든 타석에서 예약 가능한 시간이 없습니다!")
                logger.error("=" * 60)
                return False, {'error': '예약 가능 타석 없음'}
            
            # 예약 진행
            logger.info(f"\n🎯 예약을 시작합니다...")
            
            try:
                # 시간 버튼 클릭
                found_slot['time_btn'].click()
                logger.info(f"✅ {found_slot['time']} 선택")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ 시간 선택 실패: {str(e)}")
                return False, found_slot
            
            # 타석 선택 화면에서 타석 버튼 찾기
            try:
                logger.info("🔍 타석 버튼 찾는 중...")
                
                seat_buttons = self.driver.find_elements(
                    By.XPATH,
                    "//button[contains(text(), '번타석')]"
                )
                
                seat_clicked = False
                for seat_btn in seat_buttons:
                    try:
                        is_disabled = seat_btn.get_attribute('disabled')
                        seat_text = seat_btn.text.strip()
                        
                        if not is_disabled and '번타석' in seat_text:
                            seat_btn.click()
                            logger.info(f"✅ {seat_text} 선택")
                            found_slot['seat'] = seat_text
                            seat_clicked = True
                            time.sleep(2)
                            break
                    except:
                        continue
                
                if not seat_clicked:
                    logger.warning("⚠️  타석 버튼 없음 - 자동 선택되었을 수 있음")
                    found_slot['seat'] = "자동 선택"
                    
            except Exception as e:
                logger.warning(f"⚠️  타석 선택: {str(e)}")
                found_slot['seat'] = "자동 선택"
            
            # 확인 버튼
            try:
                time.sleep(1)
                confirm_selectors = [
                    "//button[contains(text(), '예약')]",
                    "//button[contains(text(), '확인')]",
                ]
                
                for selector in confirm_selectors:
                    try:
                        btn = self.driver.find_element(By.XPATH, selector)
                        if btn.is_displayed():
                            btn.click()
                            logger.info("✅ 확인 버튼 클릭")
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
            
            # 최종 확인
            try:
                time.sleep(1)
                final = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '동의') or contains(text(), '최종')]"
                )
                final.click()
                logger.info("✅ 최종 확인")
                time.sleep(2)
            except:
                pass
            
            # 결과
            logger.info("\n" + "=" * 60)
            logger.info("🎉 예약 완료!")
            logger.info("=" * 60)
            logger.info(f"📍 타석: {found_slot.get('booth')}번")
            logger.info(f"📅 날짜: {found_slot['date']} ({found_slot['day_name']})")
            logger.info(f"⏰ 시간: {found_slot['time']}")
            logger.info(f"🎯 좌석: {found_slot.get('seat', '자동')}")
            logger.info("=" * 60)
            
            time.sleep(5)
            return True, found_slot
            
        except Exception as e:
            logger.error(f"❌ 예약 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {'error': str(e)}
        """0번 모드: 가장 빠른 타석 찾아서 예약"""
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
                return False, {}
            
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
            logger.info("🔍 가장 빠른 예약 가능 타석 검색 중...")
            logger.info("=" * 60)
            
            today = datetime.now()
            found_slot = None
            
            for day_offset in range(3):
                if found_slot:
                    break
                
                target_date = today + timedelta(days=day_offset)
                target_day = target_date.day
                day_name = ["오늘", "내일", "모레"][day_offset]
                
                logger.info(f"\n━━━ {day_name} ({target_date.strftime('%Y-%m-%d')}) 확인 ━━━")
                
                # 날짜 선택 (오늘이 아닌 경우만)
                if day_offset > 0:
                    date_selected = False
                    try:
                        # 여러 selector 시도
                        date_selectors = [
                            f"//button[text()='{target_day}']",
                            f"//button[contains(text(), '{target_day}')]",
                            f"//*[text()='{target_day}']",
                            f"//*[contains(@class, 'date')]//*[text()='{target_day}']",
                        ]
                        
                        for selector in date_selectors:
                            if date_selected:
                                break
                            try:
                                date_elements = self.driver.find_elements(By.XPATH, selector)
                                logger.info(f"  날짜 selector: {selector} → {len(date_elements)}개")
                                
                                for elem in date_elements:
                                    try:
                                        if elem.is_displayed() and elem.is_enabled():
                                            elem_text = elem.text.strip()
                                            logger.info(f"    발견: '{elem_text}'")
                                            
                                            if elem_text == str(target_day) or f"{target_day}" in elem_text:
                                                logger.info(f"    클릭 시도...")
                                                elem.click()
                                                time.sleep(2)
                                                date_selected = True
                                                logger.info(f"  ✅ {target_day}일 선택 완료")
                                                break
                                    except Exception as e:
                                        logger.debug(f"    요소 처리 실패: {str(e)}")
                                        continue
                            except Exception as e:
                                logger.debug(f"  selector 실패: {str(e)}")
                                continue
                    except Exception as e:
                        logger.debug(f"  날짜 선택 오류: {str(e)}")
                    
                    if not date_selected:
                        logger.info(f"  ℹ️  {target_day}일 선택 안됨 - 이미 선택되었거나 기본값일 수 있음")
                        # 날짜 선택 실패해도 계속 진행 (이미 선택되어 있을 수 있음)
                else:
                    logger.info(f"  ℹ️  오늘은 기본 선택됨")
                
                # 시간대 찾기 (날짜 선택 여부와 관계없이 진행)
                time.sleep(1)
                # 시간대 찾기 (날짜 선택 여부와 관계없이 진행)
                time.sleep(1)
                
                # btn_time 클래스를 가진 모든 버튼 찾기
                time_selectors = [
                    "//button[contains(@class, 'btn_time')]",
                    "//button[contains(text(), ':')]",
                ]
                
                all_time_elements = []
                for selector in time_selectors:
                    try:
                        elements = self.driver.find_elements(By.XPATH, selector)
                        logger.info(f"  시간 selector: {selector} → {len(elements)}개")
                        all_time_elements.extend(elements)
                    except Exception as e:
                        logger.debug(f"  시간 selector 실패: {str(e)}")
                        continue
                
                time_slots = []
                seen_times = set()
                for elem in all_time_elements:
                    try:
                        # disabled 속성 확인
                        is_disabled = elem.get_attribute('disabled')
                        is_visible = elem.is_displayed()
                        text = elem.text.strip()
                        
                        logger.info(f"    시간 버튼: '{text}' / disabled={is_disabled} / visible={is_visible}")
                        
                        # disabled가 아니고, 보이고, 시간 형식이고, 중복 아니면 추가
                        if not is_disabled and is_visible and ':' in text and text not in seen_times:
                            seen_times.add(text)
                            time_slots.append((text, elem))
                            logger.info(f"      ✅ 예약 가능 시간: '{text}'")
                        elif is_disabled:
                            logger.info(f"      ⚠️  예약 불가 시간: '{text}' (disabled)")
                            
                    except Exception as e:
                        logger.debug(f"    시간 요소 처리 실패: {str(e)}")
                        continue
                
                logger.info(f"  ✅ 예약 가능 시간대: {[t[0] for t in time_slots]}")
                
                if not time_slots:
                    logger.warning(f"  ❌ {day_name}에 예약 가능한 시간대가 없습니다")
                    continue
                
                for time_text, time_elem in time_slots:
                    if found_slot:
                        break
                    
                    logger.info(f"\n    🔍 {time_text} 타석 확인...")
                    
                    try:
                        time_elem.click()
                        time.sleep(2)  # 타석 로딩 대기
                        logger.info(f"      ✅ {time_text} 클릭 완료")
                        
                        # 타석 버튼 찾기
                        seat_selectors = [
                            "//button[contains(text(), '번타석')]",
                            "//*[contains(text(), '번타석예약')]",
                        ]
                        
                        all_seats = []
                        for selector in seat_selectors:
                            try:
                                seats = self.driver.find_elements(By.XPATH, selector)
                                logger.info(f"        타석 selector: {selector} → {len(seats)}개")
                                all_seats.extend(seats)
                            except Exception as e:
                                logger.debug(f"        타석 selector 실패: {str(e)}")
                                continue
                        
                        found_available = False
                        for seat_elem in all_seats:
                            try:
                                is_visible = seat_elem.is_displayed()
                                is_disabled = seat_elem.get_attribute('disabled')
                                seat_text = seat_elem.text.strip()
                                
                                logger.info(f"        타석: '{seat_text}' / disabled={is_disabled} / visible={is_visible}")
                                
                                # disabled 아니고, 보이고, "번타석" 포함하면 예약 가능
                                if not is_disabled and is_visible and '번타석' in seat_text:
                                    # "예약불가" 같은 텍스트가 있는지도 체크
                                    if not any(keyword in seat_text for keyword in ['예약불가', '마감', '불가능', '종료']):
                                        logger.info(f"        ✅✅ 예약 가능 타석 발견!")
                                        found_slot = {
                                            'date': target_date.strftime('%Y-%m-%d'),
                                            'day_name': day_name,
                                            'time': time_text,
                                            'seat': seat_text,
                                            'elem': seat_elem
                                        }
                                        found_available = True
                                        break
                                    else:
                                        logger.info(f"        ⚠️  텍스트상 예약 불가: {seat_text}")
                                elif is_disabled:
                                    logger.info(f"        ⚠️  disabled 상태: {seat_text}")
                                    
                            except Exception as e:
                                logger.debug(f"        타석 처리 실패: {str(e)}")
                                continue
                        
                        if found_slot:
                            break
                        else:
                            logger.info(f"      ❌ {time_text}: 예약 가능 타석 없음")
                            
                    except Exception as e:
                        logger.warning(f"      시간대 처리 실패: {str(e)}")
                        continue
            
            if not found_slot:
                logger.error("=" * 60)
                logger.error("❌ 3일 이내에 예약 가능한 타석이 없습니다!")
                logger.error("=" * 60)
                return False, {'error': '예약 가능 타석 없음'}
            
            # 예약 진행
            logger.info("\n" + "=" * 60)
            logger.info("🎯 가장 빠른 예약 가능 타석 발견!")
            logger.info("=" * 60)
            logger.info(f"📅 날짜: {found_slot['date']} ({found_slot['day_name']})")
            logger.info(f"⏰ 시간: {found_slot['time']}")
            logger.info(f"🎯 타석: {found_slot['seat']}")
            logger.info("=" * 60)
            logger.info("\n🎯 예약 시작...")
            
            try:
                found_slot['elem'].click()
                logger.info(f"✅ {found_slot['seat']} 클릭")
                time.sleep(2)
            except:
                logger.error("❌ 타석 클릭 실패")
                return False, found_slot
            
            # 확인 버튼
            try:
                confirm_selectors = [
                    "//button[contains(text(), '예약')]",
                    "//button[contains(text(), '확인')]",
                ]
                
                for selector in confirm_selectors:
                    try:
                        btn = self.driver.find_element(By.XPATH, selector)
                        if btn.is_displayed() and btn.is_enabled():
                            btn.click()
                            logger.info("✅ 확인 버튼 클릭")
                            time.sleep(2)
                            break
                    except:
                        continue
            except:
                pass
            
            # 최종 확인
            try:
                time.sleep(2)
                final = self.driver.find_element(
                    By.XPATH,
                    "//button[contains(text(), '동의') or contains(text(), '최종확인')]"
                )
                final.click()
                logger.info("✅ 최종 확인")
                time.sleep(2)
            except:
                pass
            
            logger.info("\n" + "=" * 60)
            logger.info("🎉 예약 완료!")
            logger.info("=" * 60)
            logger.info(f"📅 예약 날짜: {found_slot['date']} ({found_slot['day_name']})")
            logger.info(f"⏰ 예약 시간: {found_slot['time']}")
            logger.info(f"🎯 예약 타석: {found_slot['seat']}")
            logger.info("=" * 60)
            
            time.sleep(5)
            return True, found_slot
            
        except Exception as e:
            logger.error(f"❌ 예약 실패: {str(e)}")
            return False, {'error': str(e)}
    
    def book_tomorrow_slot(self):
        """1번, 2번 모드: 내일(N+1일) 타석 예약 - 우선순위 후 전체 타석 확인"""
        try:
            booking_url = (
                "https://map.naver.com/p/search/%EB%A9%94%EC%9D%B4%EC%A0%80"
                "%EA%B3%A8%ED%94%84%EC%95%84%EC%B9%B4%EB%8D%B0%EB%AF%B8/"
                "place/1076834793?placePath=/ticket"
            )
            
            logger.info(f"🔗 예약 페이지 접속...")
            start_time = time.time()
            
            self.driver.get(booking_url)
            # 페이지 로드 대기 (iframe이 나타날 때까지)
            try:
                short_wait = WebDriverWait(self.driver, 5)  # 5초 타임아웃
                short_wait.until(EC.frame_to_be_available_and_switch_to_it("entryIframe"))
                logger.info(f"✅ iframe 전환 완료 ({time.time() - start_time:.2f}초)")
            except TimeoutException:
                logger.error("❌ iframe 찾기 실패")
                return False, {}
            
            # 예약 탭 클릭 (짧은 타임아웃으로 빠르게 처리)
            tab_start = time.time()
            try:
                short_wait = WebDriverWait(self.driver, 3)  # 3초 타임아웃
                booking_tab = short_wait.until(
                    EC.element_to_be_clickable((By.XPATH, "//a[contains(text(), '예약')]"))
                )
                booking_tab.click()
                logger.info(f"✅ 예약 탭 클릭 ({time.time() - tab_start:.2f}초)")
            except TimeoutException:
                logger.info(f"ℹ️  예약 탭이 이미 선택됨 또는 클릭 불필요 ({time.time() - tab_start:.2f}초)")
            except Exception as e:
                logger.debug(f"예약 탭 클릭 오류: {str(e)}")
            
            logger.info("=" * 60)
            logger.info("🔍 타석 링크 검색")
            logger.info("=" * 60)
            
            # 타석 링크가 나타날 때까지 대기 (짧은 타임아웃)
            link_start = time.time()
            try:
                short_wait = WebDriverWait(self.driver, 5)  # 5초 타임아웃
                short_wait.until(
                    EC.presence_of_element_located((By.XPATH, "//a[contains(@href, 'booking.naver.com')][contains(., '번타석')] | //a[contains(., '번타석예약')]"))
                )
                logger.info(f"✅ 타석 링크 로드 완료 ({time.time() - link_start:.2f}초)")
            except TimeoutException:
                # 타임아웃이어도 계속 진행 (타석 링크가 이미 있을 수 있음)
                logger.info(f"ℹ️  타석 링크 대기 타임아웃 (계속 진행) ({time.time() - link_start:.2f}초)")
            
            # 타석 예약 링크 찾기
            try:
                booth_links = self.driver.find_elements(
                    By.XPATH,
                    "//a[contains(@href, 'booking.naver.com')][contains(., '번타석')]"
                )
                
                if not booth_links:
                    booth_links = self.driver.find_elements(
                        By.XPATH,
                        "//a[contains(., '번타석예약')]"
                    )
                
                logger.info(f"발견된 타석 링크: {len(booth_links)}개")
                
                booth_infos = []
                for link in booth_links:
                    try:
                        booth_text = link.text.strip()
                        booth_href = link.get_attribute('href')
                        
                        if booth_text and '번타석' in booth_text:
                            # 타석 번호 추출
                            import re
                            match = re.search(r'(\d+)번타석', booth_text)
                            booth_num = int(match.group(1)) if match else 999
                            
                            booth_infos.append({
                                'num': booth_num,
                                'text': booth_text,
                                'href': booth_href,
                                'element': link
                            })
                            logger.info(f"  - {booth_text}")
                    except:
                        continue
                
                if not booth_infos:
                    logger.error("❌ 타석 링크를 찾을 수 없습니다")
                    return False, {'error': '타석 링크 없음'}
                
            except Exception as e:
                logger.error(f"❌ 타석 링크 검색 실패: {str(e)}")
                return False, {'error': str(e)}
            
            # 내일 날짜 및 시간 계산
            today = datetime.now()
            tomorrow = today + timedelta(days=1)
            weekday = tomorrow.weekday()
            
            if weekday < 5:  # 월~금
                target_time_24 = "12:00"
                target_time_12 = "12:00"
                day_type = "평일"
            else:  # 토~일
                target_time_24 = "13:00"
                target_time_12 = "1:00"
                day_type = "주말"
            
            logger.info("=" * 60)
            logger.info(f"📅 오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
            logger.info(f"📅 예약일: {tomorrow.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][weekday]}요일)")
            logger.info(f"🎯 예약 시간: {target_time_24} - {day_type}")
            logger.info("=" * 60)
            
            # 1단계: 우선순위 타석 확인
            priority_seats = [11, 7, 8, 9, 10]
            logger.info(f"🎯 우선순위 타석: {' > '.join(map(str, priority_seats))}")
            
            found_slot = None
            tomorrow_day = tomorrow.day
            
            # 우선순위 타석 확인
            for priority_num in priority_seats:
                if found_slot:
                    break
                
                logger.info(f"\n{'=' * 60}")
                logger.info(f"🎯 {priority_num}번 타석 확인 중...")
                logger.info(f"{'=' * 60}")
                
                # 해당 번호의 타석 링크 찾기
                target_booth = None
                for booth_info in booth_infos:
                    if booth_info['num'] == priority_num:
                        target_booth = booth_info
                        break
                
                if not target_booth:
                    logger.info(f"  ⚠️  {priority_num}번 타석 링크 없음")
                    continue
                
                # 타석 확인
                result = self._check_booth_availability(
                    target_booth, tomorrow_day, target_time_24, target_time_12
                )
                
                if result:
                    found_slot = result
                    logger.info(f"\n{'=' * 60}")
                    logger.info(f"🎉 {priority_num}번 타석에서 {target_time_24} 예약 가능!")
                    logger.info(f"{'=' * 60}")
                    break
            
            # 2단계: 우선순위 타석에서 못 찾으면 모든 타석 확인
            if not found_slot:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"⚠️  우선순위 타석에서 {target_time_24} 예약 불가")
                logger.info(f"🔍 다른 타석 확인 시작...")
                logger.info(f"{'=' * 60}")
                
                # 우선순위가 아닌 타석들만 확인
                other_booths = [b for b in booth_infos if b['num'] not in priority_seats]
                other_booths.sort(key=lambda x: x['num'])  # 번호 순으로 정렬
                
                for booth_info in other_booths:
                    if found_slot:
                        break
                    
                    logger.info(f"\n🔍 {booth_info['text']} 확인 중...")
                    
                    result = self._check_booth_availability(
                        booth_info, tomorrow_day, target_time_24, target_time_12
                    )
                    
                    if result:
                        found_slot = result
                        logger.info(f"\n{'=' * 60}")
                        logger.info(f"🎉 {booth_info['text']}에서 {target_time_24} 예약 가능!")
                        logger.info(f"{'=' * 60}")
                        break
            
            # 3단계: 예약 가능 타석이 없음
            if not found_slot:
                logger.error("=" * 60)
                logger.error(f"❌ {tomorrow.strftime('%Y-%m-%d')} ({day_type}) {target_time_24}에")
                logger.error(f"   예약 가능한 타석이 없습니다")
                logger.error("=" * 60)
                return False, {
                    'error': f'{tomorrow.strftime("%Y-%m-%d")} {target_time_24} 예약 불가',
                    'date': tomorrow.strftime('%Y-%m-%d'),
                    'time': target_time_24,
                    'day_type': day_type
                }
            
            # 예약 진행
            logger.info(f"\n🎯 예약을 시작합니다...")
            
            try:
                found_slot['time_btn'].click()
                logger.info(f"✅ {found_slot['time']} 선택")
                time.sleep(2)
            except Exception as e:
                logger.error(f"❌ 시간 선택 실패: {str(e)}")
                return False, found_slot
            
            # "다음" 버튼 및 로그인 처리
            success = self._process_booking_steps()
            if not success:
                return False, found_slot
            
            # 결과
            logger.info("\n" + "=" * 60)
            logger.info("🎉 예약 완료!")
            logger.info("=" * 60)
            logger.info(f"📍 타석: {found_slot['booth_text']}")
            logger.info(f"📅 예약일: {found_slot['date']} ({found_slot['day_type']})")
            logger.info(f"⏰ 예약 시간: {found_slot['time']}")
            logger.info("=" * 60)
            
            time.sleep(5)
            return True, found_slot
            
        except Exception as e:
            logger.error(f"❌ 예약 실패: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            return False, {'error': str(e)}
    
    def _check_booth_availability(self, booth_info, tomorrow_day, target_time_24, target_time_12):
        """타석의 예약 가능 여부 확인"""
        try:
            # 타석 페이지로 이동
            logger.info(f"  🔗 {booth_info['text']} 페이지로 이동...")
            
            cookie_success = self.apply_cookies_to_domain(booth_info['href'])
            
            if not cookie_success:
                logger.debug("  쿠키 로그인 실패 - 현재 세션으로 진행")
                self.driver.get(booth_info['href'])
                # 페이지 로드 대기 (캘린더가 나타날 때까지)
                try:
                    self.wait.until(
                        EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'calendar_date')] | //button[contains(@class, 'btn_time')]"))
                    )
                except TimeoutException:
                    time.sleep(0.5)  # 최소 대기
            
            # 로그인 페이지 체크
            current_url = self.driver.current_url
            if 'nid.naver.com/nidlogin' in current_url or 'login' in current_url.lower():
                logger.warning("  ⚠️  로그인 페이지로 리다이렉트됨")
                return None
            
            # 내일 날짜 선택: span.num 안에 N+1 값을 가진 요소 찾기
            logger.info(f"  📅 {tomorrow_day}일 버튼 찾는 중...")
            
            try:
                # span class="num" 안에 값이 N+1인 요소 찾기
                num_span_selector = f"//span[@class='num' and text()='{tomorrow_day}']"
                num_span = self.driver.find_element(By.XPATH, num_span_selector)
                
                # 부모 button class="calendar_date" 찾기
                parent_button = num_span.find_element(By.XPATH, "./ancestor::button[contains(@class, 'calendar_date')]")
                
                # 예약 불가능한 클래스 확인: unselectable, dayoff, closed
                class_attr = parent_button.get_attribute('class') or ''
                has_unselectable = 'unselectable' in class_attr
                has_dayoff = 'dayoff' in class_attr
                has_closed = 'closed' in class_attr
                
                if has_unselectable or has_dayoff or has_closed:
                    # 예약 불가능한 날짜이면 바로 다른 타석으로 넘어가기
                    reason = []
                    if has_unselectable:
                        reason.append("unselectable")
                    if has_dayoff:
                        reason.append("dayoff")
                    if has_closed:
                        reason.append("closed")
                    logger.info(f"  ❌ {tomorrow_day}일은 예약 불가능 ({', '.join(reason)}) - 다음 타석으로 이동")
                    return None
                
                # 예약 가능한 날짜이면 클릭
                if parent_button.is_displayed():
                    parent_button.click()
                    # 날짜 선택 후 시간 버튼이 나타날 때까지 대기 (최대 2초)
                    try:
                        self.wait.until(
                            EC.presence_of_element_located((By.XPATH, "//button[contains(@class, 'btn_time')]"))
                        )
                    except TimeoutException:
                        time.sleep(0.3)  # 최소 대기
                    logger.info(f"  ✅ {tomorrow_day}일 선택 성공!")
                else:
                    logger.info(f"  ⚠️  {tomorrow_day}일 버튼이 표시되지 않음")
                    return None
                    
            except NoSuchElementException:
                # N+1일이 페이지에 없으면 (아직 오픈 안됨)
                logger.info(f"  ⚠️  {tomorrow_day}일 버튼이 페이지에 없음 (아직 오픈 안됨)")
                return None
            except Exception as e:
                logger.debug(f"  날짜 찾기 오류: {str(e)}")
                return None
            
            # 시간대 확인 (날짜 선택 시 이미 시간 버튼이 나타날 때까지 대기했음)
            logger.info(f"  ⏰ 시간 버튼 찾는 중... (목표: {target_time_24})")
            
            time_buttons = self.driver.find_elements(
                By.XPATH,
                "//button[contains(@class, 'btn_time')]"
            )
            
            logger.info(f"  🔍 시간 버튼: {len(time_buttons)}개 발견")
            
            # 발견된 시간 버튼들의 텍스트 로그 출력
            if time_buttons:
                available_times = []
                for btn in time_buttons[:10]:  # 처음 10개만
                    try:
                        is_disabled = btn.get_attribute('disabled')
                        class_attr = btn.get_attribute('class') or ''
                        has_unselectable = 'unselectable' in class_attr
                        is_visible = btn.is_displayed()
                        time_text = btn.text.strip()
                        if is_visible:
                            if is_disabled or has_unselectable:
                                status = "❌ 불가능"
                                if is_disabled:
                                    status += "(disabled)"
                                if has_unselectable:
                                    status += "(unselectable)"
                            else:
                                status = "✅ 가능"
                            available_times.append(f"{time_text} ({status})")
                    except:
                        continue
                if available_times:
                    logger.info(f"  📋 발견된 시간: {', '.join(available_times)}")
            
            # 목표 시간 찾기
            target_time_patterns = [target_time_24, target_time_12, f"오후 {target_time_12}"]
            target_time_btn = None
            
            for btn in time_buttons:
                try:
                    is_disabled = btn.get_attribute('disabled')
                    class_attr = btn.get_attribute('class') or ''
                    has_unselectable = 'unselectable' in class_attr
                    is_visible = btn.is_displayed()
                    time_text = btn.text.strip()
                    
                    # 예약 가능 조건: disabled가 없고, unselectable 클래스가 없고, 보이는 상태
                    if not is_disabled and not has_unselectable and is_visible:
                        for pattern in target_time_patterns:
                            if pattern in time_text:
                                target_time_btn = btn
                                logger.info(f"  ✅ {time_text} 예약 가능!")
                                break
                    
                    if target_time_btn:
                        break
                except:
                    continue
            
            if target_time_btn:
                tomorrow = datetime.now() + timedelta(days=1)
                weekday = tomorrow.weekday()
                day_type = "평일" if weekday < 5 else "주말"
                
                logger.info(f"  ✅ 타석 예약 가능 확인 완료!")
                return {
                    'booth_text': booth_info['text'],
                    'booth_num': booth_info['num'],
                    'booth_href': booth_info['href'],
                    'date': tomorrow.strftime('%Y-%m-%d'),
                    'day_type': day_type,
                    'time': target_time_24,
                    'time_btn': target_time_btn
                }
            else:
                logger.info(f"  ❌ {target_time_24} 시간 버튼을 찾을 수 없음")
                logger.info(f"  ℹ️  해당 시간대가 예약 불가능하거나 아직 오픈되지 않았을 수 있습니다")
                return None
            
        except Exception as e:
            logger.debug(f"  ⚠️  {booth_info['text']} 확인 실패: {str(e)}")
            return None
    
    
    def _process_booking_steps(self):
        """예약 단계 처리: 다음 버튼 → 로그인 → 동의 → 확정"""
        try:
            # "다음" 버튼 클릭
            logger.info("🔍 '다음' 버튼 찾는 중...")
            
            next_button_selectors = [
                "//button[contains(@class, 'NextButton__btn_next')]",
                "//button[contains(text(), '다음')]",
                "//button[@data-click-code='nextbuttonview.request']",
            ]
            
            next_clicked = False
            for selector in next_button_selectors:
                try:
                    next_btn = self.driver.find_element(By.XPATH, selector)
                    if next_btn.is_displayed() and next_btn.is_enabled():
                        next_btn.click()
                        logger.info("✅ '다음' 버튼 클릭")
                        time.sleep(3)
                        next_clicked = True
                        break
                except:
                    continue
            
            if not next_clicked:
                logger.warning("⚠️  '다음' 버튼을 찾지 못함")
            
            # 로그인 페이지 확인 및 처리
            time.sleep(2)
            current_url = self.driver.current_url
            
            if 'nid.naver.com' in current_url or 'login' in current_url.lower():
                logger.info("=" * 60)
                logger.info("🔐 예약 페이지에서 로그인 요청됨")
                logger.info("=" * 60)
                
                try:
                    id_input = self.wait.until(
                        EC.presence_of_element_located((By.ID, "id"))
                    )
                    pw_input = self.driver.find_element(By.ID, "pw")
                    logger.info("✅ 로그인 폼 확인")
                    
                    logger.info("로그인 정보 입력 중...")
                    id_input.clear()
                    time.sleep(0.3)
                    
                    user_id = self.config['user_id']
                    delay_per_char = 1.0 / len(user_id) if len(user_id) > 0 else 0.1
                    for char in user_id:
                        id_input.send_keys(char)
                        time.sleep(delay_per_char)
                    
                    time.sleep(0.5)
                    
                    pw_input.clear()
                    time.sleep(0.3)
                    
                    user_pw = self.config['user_pw']
                    delay_per_char = 2.0 / len(user_pw) if len(user_pw) > 0 else 0.1
                    for char in user_pw:
                        pw_input.send_keys(char)
                        time.sleep(delay_per_char)
                    
                    time.sleep(0.8)
                    logger.info("✅ 로그인 정보 입력 완료 (ID: 1초, PW: 2초)")
                    
                    # 로그인 버튼
                    logger.info("🔍 로그인 버튼 찾는 중...")
                    
                    login_button_selectors = [
                        (By.ID, "log.login"),
                        (By.XPATH, "//button[contains(text(), '로그인')]"),
                        (By.XPATH, "//input[@type='submit']"),
                        (By.XPATH, "//button[@type='submit']"),
                        (By.XPATH, "//*[contains(@class, 'btn_login')]"),
                    ]
                    
                    login_btn_found = False
                    for by_method, selector in login_button_selectors:
                        try:
                            login_btn = self.driver.find_element(by_method, selector)
                            if login_btn.is_displayed():
                                logger.info(f"✅ 로그인 버튼 발견")
                                login_btn.click()
                                logger.info("✅ 로그인 버튼 클릭")
                                time.sleep(5)
                                login_btn_found = True
                                break
                        except:
                            continue
                    
                    if not login_btn_found:
                        logger.error("❌ 로그인 버튼을 찾을 수 없습니다")
                        return False
                    
                    # 캡챠 체크
                    try:
                        captcha = self.driver.find_element(By.ID, "captcha")
                        logger.warning("⚠️  캡챠가 나타났습니다!")
                        logger.warning("브라우저 창에서 캡챠를 입력해주세요 (최대 90초 대기)")
                        
                        for i in range(18):
                            time.sleep(5)
                            try:
                                current_url = self.driver.current_url
                                if 'nid.naver.com' not in current_url:
                                    logger.info("✅ 캡챠 통과! 로그인 성공!")
                                    break
                            except:
                                pass
                    except NoSuchElementException:
                        logger.info("✅ 예약 페이지 로그인 성공!")
                    
                    time.sleep(2)
                    
                except Exception as e:
                    logger.error(f"❌ 로그인 처리 실패: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return False
            
            # "동의하고 예약하기" 버튼
            try:
                time.sleep(1)
                logger.info("🔍 '동의하고 예약하기' 버튼 찾는 중...")
                
                agree_button_selectors = [
                    "//button[@data-click-code='submitbutton.submit']",
                    "//button[contains(@class, 'btn_request')]",
                    "//button[contains(text(), '동의하고 예약하기')]",
                ]
                
                agree_clicked = False
                for selector in agree_button_selectors:
                    try:
                        agree_btn = self.driver.find_element(By.XPATH, selector)
                        if agree_btn.is_displayed() and agree_btn.is_enabled():
                            agree_btn.click()
                            logger.info("✅ '동의하고 예약하기' 버튼 클릭")
                            time.sleep(3)
                            agree_clicked = True
                            break
                    except:
                        continue
                
                if not agree_clicked:
                    logger.error("❌ '동의하고 예약하기' 버튼을 찾지 못함")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ '동의하고 예약하기' 버튼 처리 실패: {str(e)}")
                return False
            
            # 예약 확정 확인
            try:
                time.sleep(2)
                logger.info("🔍 예약 확정 여부 확인 중...")
                
                confirmation_selectors = [
                    "//strong[contains(@class, 'popup_tit')][contains(text(), '예약이 확정')]",
                    "//*[contains(text(), '예약이 확정되었습니다')]",
                    "//strong[contains(text(), '예약이 확정')]",
                ]
                
                confirmed = False
                for selector in confirmation_selectors:
                    try:
                        confirm_elem = self.driver.find_element(By.XPATH, selector)
                        if confirm_elem.is_displayed():
                            confirm_text = confirm_elem.text
                            logger.info(f"✅ 확인: '{confirm_text}'")
                            confirmed = True
                            break
                    except:
                        continue
                
                if not confirmed:
                    try:
                        page_source = self.driver.page_source
                        if '예약이 확정' in page_source or '확정되었습니다' in page_source:
                            logger.info("✅ 페이지에서 '예약 확정' 메시지 발견")
                            confirmed = True
                    except:
                        pass
                
                if not confirmed:
                    logger.error("❌ 예약 실패: '예약이 확정되었습니다' 메시지를 찾을 수 없음")
                    return False
                
                return True
                
            except Exception as e:
                logger.error(f"❌ 예약 확정 확인 실패: {str(e)}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 예약 단계 처리 실패: {str(e)}")
            return False

    def apply_cookies_to_domain(self, target_url):
        """특정 도메인으로 이동 후 쿠키 재적용"""
        try:
            import pickle
            if not os.path.exists('naver_cookies.pkl'):
                logger.warning("⚠️  쿠키 파일이 없습니다")
                return False
            
            # 쿠키 로드
            with open('naver_cookies.pkl', 'rb') as f:
                cookies = pickle.load(f)
            
            # 타겟 도메인으로 먼저 이동
            logger.debug(f"🔗 {target_url[:60]}... 로 이동 중...")
            self.driver.get(target_url)
            time.sleep(2)
            
            # 쿠키 적용
            applied = 0
            for cookie in cookies:
                try:
                    # 도메인 호환성 체크
                    if 'domain' in cookie:
                        # .naver.com 쿠키는 모든 네이버 서브도메인에서 작동
                        if 'naver.com' in cookie['domain']:
                            self.driver.add_cookie(cookie)
                            applied += 1
                except Exception as e:
                    logger.debug(f"쿠키 적용 실패: {cookie.get('name', 'unknown')} - {str(e)}")
            
            if applied > 0:
                logger.debug(f"✅ {applied}개 쿠키 적용 완료")
                
                # 페이지 새로고침으로 쿠키 적용
                self.driver.refresh()
                time.sleep(2)
                
                # 로그인 상태 확인
                if self._check_login_status():
                    logger.debug("✅ 로그인 상태 확인됨")
                    return True
                else:
                    logger.debug("⚠️  쿠키 적용했으나 로그인 상태 아님")
                    return False
            else:
                logger.debug("⚠️  적용 가능한 쿠키가 없습니다")
                return False
            
        except Exception as e:
            logger.debug(f"⚠️  쿠키 재적용 실패: {str(e)}")
            return False
    
    def _check_login_status(self):
        """로그인 상태 확인"""
        try:
            # 로그인 버튼이 보이면 로그아웃 상태
            try:
                login_btn = self.driver.find_element(By.XPATH, "//button[contains(text(), '로그인')]")
                if login_btn.is_displayed():
                    return False
            except:
                pass
            
            # 페이지 소스에서 확인
            page_source = self.driver.page_source
            
            # 로그인 관련 요소가 있으면 로그아웃 상태
            if '로그인이 필요' in page_source or '로그인하세요' in page_source:
                return False
            
            # 기본적으로 로그인 상태로 가정
            return True
            
        except:
            # 확인 불가시 로그인 상태로 가정
            return True

    def wait_until_midnight(self):
        """자정까지 대기 (준비 작업 시간 고려)"""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 준비 작업 소요 시간 (초)
        PREPARATION_TIME = 30  # 로그인 + 페이지 접속 + 타석 링크 검색
        
        # 자정 30초 전에 준비 완료되도록
        target_start_time = midnight - timedelta(seconds=PREPARATION_TIME)
        
        wait_seconds = (target_start_time - now).total_seconds()
        
        logger.info("=" * 60)
        logger.info("⏰ 자정 예약 타이밍 계산")
        logger.info("=" * 60)
        logger.info(f"현재 시각: {now.strftime('%H:%M:%S')}")
        logger.info(f"자정 시각: {midnight.strftime('%H:%M:%S')}")
        logger.info(f"준비 시간: {PREPARATION_TIME}초")
        logger.info(f"시작 시각: {target_start_time.strftime('%H:%M:%S')} (자정 {PREPARATION_TIME}초 전)")
        logger.info(f"대기 시간: {wait_seconds:.1f}초")
        logger.info("=" * 60)
        
        if wait_seconds > 0:
            logger.info("\n⏳ 시작 시각까지 대기 중...")
            
            # 1분 이상 남았으면 중간 알림
            if wait_seconds > 60:
                while wait_seconds > 60:
                    time.sleep(30)
                    wait_seconds = (target_start_time - datetime.now()).total_seconds()
                    remaining_minutes = int(wait_seconds / 60)
                    logger.info(f"⏰ {remaining_minutes}분 {int(wait_seconds % 60)}초 남음...")
            
            # 마지막 1분
            if wait_seconds > 0:
                logger.info(f"⏰ 마지막 {int(wait_seconds)}초...")
                time.sleep(max(0, wait_seconds))
            
            logger.info("\n" + "=" * 60)
            logger.info("🚀 준비 작업 시작! (자정 30초 전)")
            logger.info("=" * 60)
        else:
            logger.warning("⚠️  이미 시작 시각이 지났습니다. 즉시 시작합니다.")
    
    def wait_for_exact_midnight(self):
        """정확히 자정까지 대기 (준비 완료 후)"""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        
        # 이미 자정이 지났으면 리턴
        if now >= midnight:
            logger.info("✅ 자정 도달!")
            return
        
        wait_seconds = (midnight - now).total_seconds()
        
        if wait_seconds > 10:
            logger.warning(f"⚠️  자정까지 {wait_seconds:.1f}초 남음 (준비가 너무 빨리 끝남)")
            logger.info("자정까지 대기...")
            time.sleep(wait_seconds)
        elif wait_seconds > 0:
            logger.info(f"⏰ 자정까지 {wait_seconds:.1f}초...")
            time.sleep(wait_seconds)
        
        logger.info("\n" + "=" * 60)
        logger.info("🎯 자정! 예약 시작!")
        logger.info("=" * 60)

    def run_mode_1(self):
        """1번 모드 실행 (즉시 내일 예약)"""
        try:
            logger.info("=" * 60)
            logger.info("🎯 내일 타석 즉시 예약 (1번 모드)")
            logger.info("=" * 60)
            
            if not self.setup_driver():
                return False
            
            if not self.naver_login():
                return False
            
            success, booking_info = self.book_tomorrow_slot()
            
            self.send_kakao_notification(success, booking_info)
            
            return success
            
        finally:
            if self.driver:
                time.sleep(3)
                self.driver.quit()

    def run_mode_2(self):
        """2번 모드 실행 (자정 대기)"""
        try:
            logger.info("=" * 60)
            logger.info("⏰ 매일 자정 자동 예약 (2번 모드)")
            logger.info("=" * 60)
            
            # 자정 30초 전까지 대기
            self.wait_until_midnight()
            
            # 준비 작업 시작 (자정 30초 전부터)
            logger.info("\n📋 준비 작업 시작...")
            prep_start = datetime.now()
            
            if not self.setup_driver():
                return False
            logger.info(f"✅ ChromeDriver 준비 완료 ({(datetime.now() - prep_start).total_seconds():.1f}초)")
            
            if not self.naver_login():
                return False
            logger.info(f"✅ 로그인 완료 ({(datetime.now() - prep_start).total_seconds():.1f}초)")
            
            prep_time = (datetime.now() - prep_start).total_seconds()
            logger.info(f"\n✅ 준비 완료! (총 소요: {prep_time:.1f}초)")
            
            # 정확히 자정까지 대기
            self.wait_for_exact_midnight()
            
            # 자정! 예약 실행
            success, booking_info = self.book_tomorrow_slot()
            
            # 카카오톡 알림
            self.send_kakao_notification(success, booking_info)
            
            return success
            
        finally:
            if self.driver:
                time.sleep(3)
                self.driver.quit()

    def run_mode_0(self):
        """0번 모드 실행 (가장 빠른 타석)"""
        try:
            logger.info("=" * 60)
            logger.info("🚀 가장 빠른 타석 예약 (0번 모드)")
            logger.info("=" * 60)
            
            if not self.setup_driver():
                return False
            
            if not self.naver_login():
                return False
            
            success, booking_info = self.book_earliest_slot()
            
            self.send_kakao_notification(success, booking_info)
            
            return success
            
        finally:
            if self.driver:
                time.sleep(3)
                self.driver.quit()


def main():
    """메인 실행 함수"""
    print("=" * 60)
    print("🏌️  메이저골프아카데미 타석 예약 프로그램")
    print("=" * 60)
    print()
    print("예약 모드를 선택하세요:")
    print("0️⃣  가장 빠른 타석 즉시 예약 (오늘/내일/모레)")
    print("1️⃣  내일 타석 즉시 예약 (우선순위: 11→7→8→9→10번)")
    print("2️⃣  매일 자정에 내일 타석 자동 예약")
    print()
    
    try:
        # config.json 로드
        if not os.path.exists('config.json'):
            logger.error("❌ config.json 파일이 없습니다!")
            logger.error("config.json 파일을 생성하고 다음 내용을 입력하세요:")
            print("""
{
    "user_id": "네이버ID",
    "user_pw": "네이버비밀번호",
    "headless": false,
    "kakao_api_key": "카카오톡 REST API 키 (선택사항)"
}
            """)
            return
        
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 필수 값 확인
        if not config.get('user_id') or not config.get('user_pw'):
            logger.error("❌ config.json에 user_id와 user_pw를 입력하세요!")
            return
        
        mode = input("모드 선택 (0/1/2): ").strip()
        
        if mode not in ['0', '1', '2']:
            print("❌ 잘못된 입력입니다. 0, 1, 2 중 하나를 선택하세요.")
            return
        
        booking_bot = GolfBookingBot(config)
        
        if mode == '0':
            booking_bot.run_mode_0()
        elif mode == '1':
            booking_bot.run_mode_1()
        elif mode == '2':
            booking_bot.run_mode_2()
            
    except KeyboardInterrupt:
        print("\n\n프로그램을 종료합니다.")
    except Exception as e:
        logger.error(f"❌ 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
