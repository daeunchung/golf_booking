# 골프 자동 예약 프로그램 설치 및 사용 가이드

## 📋 목차
1. [사전 준비](#사전-준비)
2. [설치 방법](#설치-방법)
3. [설정 방법](#설정-방법)
4. [실행 방법](#실행-방법)
5. [문제 해결](#문제-해결)

## 🔧 사전 준비

### 1. Python 설치 (3.8 이상)
```bash
# Python 버전 확인
python --version
# 또는
python3 --version
```

### 2. Chrome 브라우저 설치
- 최신 버전의 Chrome 브라우저가 설치되어 있어야 합니다.

### 3. ChromeDriver 설치
#### 자동 설치 (권장)
프로그램이 자동으로 ChromeDriver를 설치합니다.

#### 수동 설치
1. Chrome 버전 확인: chrome://version
2. [ChromeDriver 다운로드](https://chromedriver.chromium.org/downloads)
3. PATH에 추가

## 📦 설치 방법

### 1. 프로젝트 폴더 생성
```bash
mkdir golf-booking
cd golf-booking
```

### 2. 파일 복사
다음 파일들을 폴더에 복사:
- golf_auto_booking.py
- config.py
- requirements.txt

### 3. 가상환경 생성 (선택사항이지만 권장)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 4. 패키지 설치
```bash
pip install -r requirements.txt
```

## ⚙️ 설정 방법

### 1. config.py 파일 수정
```python
CONFIG = {
    'user_id': 'your_naver_id',        # 네이버 아이디 입력
    'user_pw': 'your_naver_password',  # 네이버 비밀번호 입력
    'preferred_time': '19:00',          # 원하는 시간대
    'branch': '중계점',                 # 선호 지점
    'booking_time': '23:59:50',        # 예약 시도 시간
}
```

### 2. golf_auto_booking.py 파일 수정
파일의 `schedule_booking()` 함수에서 config 정보 업데이트:
```python
def schedule_booking():
    config = {
        'user_id': '실제_네이버_아이디',
        'user_pw': '실제_네이버_비밀번호',
        'preferred_time': '19:00',
        'branch': '중계점'
    }
    # ...
```

## 🚀 실행 방법

### 방법 1: 즉시 테스트 실행
```bash
# golf_auto_booking.py의 main() 함수에서 다음 줄의 주석 해제:
# schedule_booking()

python golf_auto_booking.py
```

### 방법 2: 스케줄 실행 (매일 자정)
```bash
# 프로그램 실행 (백그라운드)
python golf_auto_booking.py

# 프로그램이 실행되면 매일 23:59:50에 자동으로 예약 시도
```

### 방법 3: 백그라운드 실행 (Linux/macOS)
```bash
nohup python golf_auto_booking.py > booking.log 2>&1 &
```

### 방법 4: Windows 작업 스케줄러 사용
1. 작업 스케줄러 열기
2. "기본 작업 만들기" 클릭
3. 이름: "골프 자동 예약"
4. 트리거: 매일, 23:59:00
5. 작업: 프로그램 시작
6. 프로그램: `python.exe의 전체 경로`
7. 인수: `golf_auto_booking.py의 전체 경로`

## 📊 로그 확인

### 실행 로그
```bash
# 로그 파일 확인
tail -f golf_booking.log
```

### 에러 발생시
- `error_YYYYMMDD_HHMMSS.png` 파일이 생성되어 에러 화면 캡처

## 🔍 문제 해결

### 1. 로그인 실패
**문제:** 네이버 로그인 캡차 발생
**해결:**
```python
# 수동 로그인 방법 사용
# 1. headless 모드 비활성화 (주석 처리)
# chrome_options.add_argument('--headless')

# 2. 프로그램 실행 후 수동으로 로그인
# 3. 로그인 후 자동 진행
```

### 2. 예약 버튼을 찾을 수 없음
**문제:** 페이지 구조가 변경됨
**해결:**
1. Chrome 개발자 도구(F12)로 페이지 구조 확인
2. 선택자(selector) 수정:
```python
# CSS Selector 또는 XPath 수정
booking_tab = driver.find_element(By.CSS_SELECTOR, "새로운_선택자")
```

### 3. 타이밍 문제
**문제:** 페이지 로딩이 느려서 요소를 찾지 못함
**해결:**
```python
# 대기 시간 증가
time.sleep(5)  # 2초 → 5초로 증가

# 또는 명시적 대기 사용
wait = WebDriverWait(driver, 30)  # 20초 → 30초
```

### 4. ChromeDriver 버전 불일치
**문제:** ChromeDriver와 Chrome 버전 불일치
**해결:**
```bash
# webdriver-manager 사용 (자동 버전 관리)
pip install webdriver-manager

# 코드 수정:
from webdriver_manager.chrome import ChromeDriverManager
driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()))
```

### 5. 메모리 부족
**문제:** 장시간 실행시 메모리 누수
**해결:**
```python
# 매 실행마다 드라이버 재시작
# finally 블록에서 확실히 종료
```

## 💡 추가 기능 개선 아이디어

### 1. 알림 기능 추가
```python
# 텔레그램 알림
import telegram
bot = telegram.Bot(token='YOUR_BOT_TOKEN')
bot.send_message(chat_id='YOUR_CHAT_ID', text='예약 성공!')

# 이메일 알림
import smtplib
# 이메일 발송 코드
```

### 2. 재시도 로직 강화
```python
for attempt in range(max_retries):
    try:
        if book_golf_slot():
            break
    except:
        if attempt < max_retries - 1:
            time.sleep(retry_delay)
```

### 3. 여러 시간대 옵션
```python
preferred_times = ['19:00', '20:00', '21:00']
for time_slot in preferred_times:
    if try_booking(time_slot):
        break
```

## ⚠️ 주의사항

1. **네이버 이용약관 준수**: 자동화 프로그램 사용시 이용약관을 확인하세요.
2. **계정 보안**: config.py 파일에 비밀번호가 포함되므로 보안에 주의하세요.
3. **과도한 요청 자제**: 서버에 부담을 주지 않도록 적절한 대기 시간을 설정하세요.
4. **개인 사용 목적**: 이 프로그램은 개인 사용 목적으로만 사용하세요.

## 📞 문의

문제가 계속 발생하면:
1. 로그 파일(`golf_booking.log`) 확인
2. 에러 스크린샷 확인
3. Chrome 개발자 도구로 페이지 구조 분석

## 📝 라이선스

이 프로그램은 개인 사용 목적으로 제공됩니다.
