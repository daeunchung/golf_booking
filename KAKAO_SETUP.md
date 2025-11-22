# 카카오톡 알림 설정 가이드

## 📱 카카오톡 "나에게 보내기" 설정 방법

### 1단계: 카카오 개발자 계정 만들기

1. [카카오 디벨로퍼](https://developers.kakao.com/) 접속
2. 우측 상단 "로그인" 클릭
3. 카카오 계정으로 로그인

### 2단계: 애플리케이션 등록

1. 로그인 후 "내 애플리케이션" 메뉴 클릭
2. "애플리케이션 추가하기" 클릭
3. 정보 입력:
   - 앱 이름: `골프예약알림` (원하는 이름)
   - 사업자명: 개인 이름
   - "저장" 클릭

### 3단계: REST API 키 확인

1. 생성한 애플리케이션 클릭
2. "앱 키" 탭에서 **REST API 키** 복사
   ```
   예: 1234567890abcdef1234567890abcdef
   ```

### 4단계: 플랫폼 설정
cl궁
1. 좌측 메뉴에서 "플랫폼" 클릭
2. "Web 플랫폼 등록" 클릭
3. 사이트 도메인: `http://localhost` 입력
4. "저장" 클릭

### 5단계: Redirect URI 설정

1. 좌측 메뉴에서 "카카오 로그인" 클릭
2. "활성화 설정" → ON
3. "Redirect URI" 섹션에서 "Redirect URI 등록" 클릭
4. URI 입력: `https://localhost` 또는 `http://localhost`
5. "저장" 클릭

### 6단계: 동의 항목 설정

1. 좌측 메뉴에서 "동의 항목" 클릭
2. "카카오톡 메시지 전송" 항목 찾기
3. 설정:
   - 동의 단계: **선택 동의**
   - 상태: **ON**
4. "저장" 클릭

### 7단계: Python으로 인증하기

#### 방법 A: 자동 설정 스크립트 사용 (권장)

```bash
# 카카오 알림 설정 실행
python kakao_notification.py
```

실행하면:
1. REST API 키 입력 요청
2. 인증 URL 출력 → 브라우저에서 열기
3. 카카오 로그인 및 동의
4. 리다이렉트된 URL의 `code` 값 복사
5. 터미널에 `code` 값 입력
6. 자동으로 토큰 저장 (`kakao_token.json`)

#### 방법 B: 수동 설정

```python
from kakao_notification import setup_kakao_notifier

# REST API 키로 설정
setup_kakao_notifier("YOUR_REST_API_KEY")
```

### 8단계: config.json 설정

```json
{
  "enable_notification": true,
  "notification_type": "kakao",
  "kakao_rest_api_key": "복사한_REST_API_키"
}
```

## 🧪 테스트

```python
from kakao_notification import KakaoNotifier

notifier = KakaoNotifier("YOUR_REST_API_KEY")
notifier.send_message("테스트 메시지입니다!")
```

성공하면 카카오톡으로 메시지가 도착합니다! 📱

## 🔧 문제 해결

### 1. "invalid_grant" 오류
**원인**: 인증 코드가 만료되었거나 잘못됨
**해결**: 
- 인증 URL을 다시 열어서 새로운 code를 받으세요
- code는 1회용이므로 빠르게 입력해야 합니다

### 2. "KOE320" 오류
**원인**: 동의 항목 설정 누락
**해결**:
- 카카오 디벨로퍼 → 동의항목 → "카카오톡 메시지 전송" ON

### 3. "redirect_uri_mismatch" 오류
**원인**: Redirect URI가 일치하지 않음
**해결**:
- 카카오 디벨로퍼에서 등록한 URI와 코드의 URI가 동일한지 확인
- 기본값: `https://localhost`

### 4. 토큰 만료
**원인**: 액세스 토큰 유효기간 만료 (보통 6시간)
**해결**:
- 자동으로 리프레시 토큰으로 갱신됩니다
- 리프레시 토큰도 만료되면 재인증 필요

## 📋 전체 흐름 요약

```
1. 카카오 디벨로퍼 가입
   ↓
2. 앱 만들기 + REST API 키 받기
   ↓
3. 플랫폼/Redirect URI/동의항목 설정
   ↓
4. Python으로 인증 (최초 1회)
   ↓
5. 토큰 저장 (kakao_token.json)
   ↓
6. 메시지 전송 가능! 🎉
```

## 💡 추가 팁

### 메시지 템플릿 커스터마이징

```python
notifier.send_message(
    text="🏌️ 골프 예약 성공!\n\n시간: 19:00\n장소: 메이저골프아카데미 중계점",
    link_url="https://map.naver.com/...",
    link_title="예약 확인하기"
)
```

### 토큰 파일 위치
- 기본: `kakao_token.json` (프로그램과 같은 폴더)
- 이 파일은 자동으로 관리되므로 건드리지 마세요

### 보안
- REST API 키는 공개 저장소에 올리지 마세요
- `.gitignore`에 추가:
  ```
  config.json
  kakao_token.json
  ```

## 📞 참고 링크

- [카카오 디벨로퍼](https://developers.kakao.com/)
- [메시지 API 문서](https://developers.kakao.com/docs/latest/ko/message/rest-api)
- [나에게 보내기 가이드](https://developers.kakao.com/docs/latest/ko/message/js-link#default-template-msg)
