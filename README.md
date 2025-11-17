# 메이저골프아카데미 타석 자동 예약 프로그램

## 📋 목차
1. [프로그램 소개](#프로그램-소개)
2. [예약 모드 설명](#예약-모드-설명)
3. [사전 준비](#사전-준비)
4. [설치 방법](#설치-방법)
5. [설정 방법](#설정-방법)
6. [실행 방법](#실행-방법)
7. [문제 해결](#문제-해결)

## 프로그램 소개

메이저골프아카데미 타석을 자동으로 예약하는 Python 기반 프로그램입니다.
Selenium을 활용하여 네이버 예약 시스템에 접근하며, 3가지 예약 모드를 제공합니다.

## 예약 모드 설명

### 0번 모드: 가장 빠른 타석 즉시 예약

**로직:**
- 오늘, 내일, 모레 중 예약 가능한 가장 빠른 타석을 찾습니다
- 모든 타석 번호(1-11번)를 순차적으로 검색
- 예약 가능한 첫 번째 타석을 발견하면 즉시 예약

**사용 시나리오:**
- 당장 빨리 예약이 필요할 때
- 타석 번호나 날짜에 상관없이 가장 빠른 시간에 이용하고 싶을 때
- 급하게 예약이 필요한 상황

**실행 방법:**
```bash
python golf_auto_booking.py
# 모드 선택 프롬프트에서 0 입력
```

---

### 1번 모드: 내일 타석 즉시 예약

**로직:**
- 내일(N+1일) 타석만 검색
- 우선순위 타석: 11번 → 7번 → 8번 → 9번 → 10번 순으로 시도
- 우선순위 타석에서 예약 불가시 전체 타석(1-11번) 순차 검색
- 예약 가능한 타석을 찾으면 즉시 예약

**사용 시나리오:**
- 특정 선호 타석(11, 7, 8, 9, 10번)을 먼저 예약하고 싶을 때
- 내일 예약만 필요하고, 지금 바로 예약하고 싶을 때
- 수동으로 예약 타이밍을 조절하고 싶을 때

**실행 방법:**
```bash
python golf_auto_booking.py
# 모드 선택 프롬프트에서 1 입력
```

---

### 2번 모드: 매일 자정 자동 예약

**로직:**
1. 자정 30초 전까지 대기
2. 자정 30초 전부터 준비 작업 시작 (ChromeDriver 초기화, 네이버 로그인)
3. 정확히 자정(00:00:00)에 예약 시작
4. 내일(N+1일) 타석 검색 (1번 모드와 동일한 로직)
5. 우선순위 타석 → 전체 타석 순으로 예약 시도

**사용 시나리오:**
- 매일 정확한 시간(자정)에 자동으로 예약하고 싶을 때
- 경쟁이 치열한 타석을 선점하고 싶을 때
- 예약 오픈 시간에 맞춰 자동 예약이 필요할 때
- 프로그램을 미리 실행해두고 자정까지 대기시키고 싶을 때

**실행 방법:**
```bash
python golf_auto_booking.py
# 모드 선택 프롬프트에서 2 입력
# 프로그램이 자정까지 대기 후 자동 실행
```

**참고사항:**
- 자정 30초 전부터 로그인 등 준비 작업을 미리 수행하여 자정에 즉시 예약 가능
- 백그라운드 실행 권장 (아래 실행 방법 참조)

---

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

### config.json 파일 생성

프로젝트 폴더에 `config.json` 파일을 생성하고 아래 내용을 입력하세요:

```json
{
    "user_id": "네이버_아이디",
    "user_pw": "네이버_비밀번호",
    "headless": false,
    "kakao_api_key": "카카오톡_REST_API_키_선택사항"
}
```

**설정 항목 설명:**
- `user_id`: 네이버 아이디 (필수)
- `user_pw`: 네이버 비밀번호 (필수)
- `headless`: 브라우저 창을 띄우지 않고 실행 (true/false, 기본값: false)
- `kakao_api_key`: 카카오톡으로 예약 결과 알림 받기 (선택사항)

## 🚀 실행 방법

### 기본 실행

```bash
python golf_auto_booking.py
```

실행 후 모드 선택 프롬프트가 나타나면 원하는 모드(0/1/2)를 입력하세요.

### 백그라운드 실행 (2번 모드 권장)

**Linux/macOS:**
```bash
nohup python golf_auto_booking.py > booking.log 2>&1 &
```

**실행 중인 프로그램 확인:**
```bash
# 로그 실시간 확인
tail -f booking.log

# 프로세스 확인
ps aux | grep golf_auto_booking
```

## 📊 로그 확인

프로그램 실행 중 발생하는 모든 로그는 콘솔과 `golf_booking.log` 파일에 기록됩니다.

**로그 확인:**
```bash
# 전체 로그 보기
cat golf_booking.log

# 실시간 로그 확인
tail -f golf_booking.log
```

**에러 발생시:**
- `error_YYYYMMDD_HHMMSS.png` 파일에 에러 화면이 자동 캡처됩니다
- 로그 파일에서 에러 원인을 확인할 수 있습니다

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

## ⚠️ 주의사항

1. **네이버 이용약관 준수**: 자동화 프로그램 사용시 이용약관을 확인하세요.
2. **계정 보안**: config.json 파일에 비밀번호가 포함되므로 보안에 주의하세요.
3. **과도한 요청 자제**: 서버에 부담을 주지 않도록 적절한 대기 시간을 설정하세요.
4. **개인 사용 목적**: 이 프로그램은 개인 사용 목적으로만 사용하세요.

## 📞 문의

문제가 계속 발생하면:
1. 로그 파일(`golf_booking.log`) 확인
2. 에러 스크린샷 확인
3. Chrome 개발자 도구로 페이지 구조 분석

## 📝 라이선스

이 프로그램은 개인 사용 목적으로 제공됩니다.
