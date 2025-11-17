#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
카카오톡 알림 모듈
"""

import requests
import json
import logging

logger = logging.getLogger(__name__)


class KakaoNotifier:
    """카카오톡 메시지 알림 클래스"""
    
    def __init__(self, rest_api_key, redirect_uri="https://localhost"):
        """
        카카오톡 알림 초기화
        
        Args:
            rest_api_key: 카카오 REST API 키
            redirect_uri: 리다이렉트 URI (기본값: https://localhost)
        """
        self.rest_api_key = rest_api_key
        self.redirect_uri = redirect_uri
        self.token_file = "kakao_token.json"
        self.access_token = None
        self.refresh_token = None
        
        # 저장된 토큰 로드
        self.load_tokens()
    
    def get_authorization_url(self):
        """인증 URL 생성"""
        auth_url = (
            f"https://kauth.kakao.com/oauth/authorize?"
            f"client_id={self.rest_api_key}&"
            f"redirect_uri={self.redirect_uri}&"
            f"response_type=code"
        )
        return auth_url
    
    def get_tokens(self, authorization_code):
        """
        인증 코드로 토큰 발급
        
        Args:
            authorization_code: 카카오 인증 코드
        """
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "authorization_code",
            "client_id": self.rest_api_key,
            "redirect_uri": self.redirect_uri,
            "code": authorization_code,
        }
        
        try:
            response = requests.post(url, data=data)
            tokens = response.json()
            
            if "access_token" in tokens:
                self.access_token = tokens["access_token"]
                self.refresh_token = tokens.get("refresh_token")
                
                # 토큰 저장
                self.save_tokens()
                logger.info("✅ 카카오 토큰 발급 성공")
                return True
            else:
                logger.error(f"❌ 토큰 발급 실패: {tokens}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 토큰 발급 오류: {str(e)}")
            return False
    
    def refresh_access_token(self):
        """액세스 토큰 갱신"""
        if not self.refresh_token:
            logger.error("❌ 리프레시 토큰이 없습니다")
            return False
        
        url = "https://kauth.kakao.com/oauth/token"
        data = {
            "grant_type": "refresh_token",
            "client_id": self.rest_api_key,
            "refresh_token": self.refresh_token,
        }
        
        try:
            response = requests.post(url, data=data)
            tokens = response.json()
            
            if "access_token" in tokens:
                self.access_token = tokens["access_token"]
                if "refresh_token" in tokens:
                    self.refresh_token = tokens["refresh_token"]
                
                self.save_tokens()
                logger.info("✅ 토큰 갱신 성공")
                return True
            else:
                logger.error(f"❌ 토큰 갱신 실패: {tokens}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 토큰 갱신 오류: {str(e)}")
            return False
    
    def save_tokens(self):
        """토큰을 파일에 저장"""
        try:
            tokens = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
            }
            with open(self.token_file, "w") as f:
                json.dump(tokens, f)
            logger.info("✅ 토큰 저장 완료")
        except Exception as e:
            logger.error(f"❌ 토큰 저장 실패: {str(e)}")
    
    def load_tokens(self):
        """파일에서 토큰 로드"""
        try:
            with open(self.token_file, "r") as f:
                tokens = json.load(f)
                self.access_token = tokens.get("access_token")
                self.refresh_token = tokens.get("refresh_token")
                logger.info("✅ 토큰 로드 완료")
                return True
        except FileNotFoundError:
            logger.info("ℹ️  저장된 토큰이 없습니다")
            return False
        except Exception as e:
            logger.error(f"❌ 토큰 로드 실패: {str(e)}")
            return False
    
    def send_message(self, text, link_url=None, link_title=None):
        """
        나에게 메시지 보내기
        
        Args:
            text: 보낼 메시지 텍스트
            link_url: 링크 URL (선택)
            link_title: 링크 제목 (선택)
        """
        if not self.access_token:
            logger.error("❌ 액세스 토큰이 없습니다. 먼저 인증을 진행하세요.")
            return False
        
        url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        
        # 템플릿 생성
        template = {
            "object_type": "text",
            "text": text,
            "link": {
                "web_url": link_url or "https://www.naver.com",
                "mobile_web_url": link_url or "https://www.naver.com",
            },
        }
        
        # 링크 버튼 추가 (선택)
        if link_url and link_title:
            template["buttons"] = [
                {
                    "title": link_title,
                    "link": {
                        "web_url": link_url,
                        "mobile_web_url": link_url,
                    },
                }
            ]
        
        data = {
            "template_object": json.dumps(template)
        }
        
        try:
            response = requests.post(url, headers=headers, data=data)
            result = response.json()
            
            if response.status_code == 200:
                logger.info("✅ 카카오톡 메시지 전송 성공")
                return True
            elif response.status_code == 401:
                # 토큰 만료 - 갱신 시도
                logger.warning("⚠️  토큰 만료, 갱신 시도...")
                if self.refresh_access_token():
                    # 재시도
                    return self.send_message(text, link_url, link_title)
                else:
                    logger.error("❌ 토큰 갱신 실패")
                    return False
            else:
                logger.error(f"❌ 메시지 전송 실패: {result}")
                return False
                
        except Exception as e:
            logger.error(f"❌ 메시지 전송 오류: {str(e)}")
            return False


def setup_kakao_notifier(rest_api_key):
    """
    카카오 알림 초기 설정 (최초 1회만 실행)
    
    Args:
        rest_api_key: 카카오 REST API 키
    """
    print("=" * 60)
    print("카카오톡 알림 설정")
    print("=" * 60)
    print()
    
    notifier = KakaoNotifier(rest_api_key)
    
    # 1. 인증 URL 출력
    auth_url = notifier.get_authorization_url()
    print("1. 아래 URL을 브라우저에서 열어주세요:")
    print(auth_url)
    print()
    
    # 2. 인증 코드 입력 받기
    print("2. 로그인 후 리다이렉트된 URL에서 code 값을 복사하세요.")
    print("   예: https://localhost/?code=XXXXX")
    print()
    auth_code = input("인증 코드(code 값)를 입력하세요: ").strip()
    
    # 3. 토큰 발급
    if notifier.get_tokens(auth_code):
        print()
        print("✅ 카카오톡 알림 설정 완료!")
        print("이제 메시지를 보낼 수 있습니다.")
        
        # 테스트 메시지 전송
        test = input("\n테스트 메시지를 보낼까요? (y/n): ").strip().lower()
        if test == 'y':
            notifier.send_message(
                "🏌️ 골프 자동 예약 프로그램\n\n카카오톡 알림 테스트 성공!"
            )
        
        return True
    else:
        print("❌ 설정 실패")
        return False


if __name__ == "__main__":
    # 테스트 실행
    print("카카오 REST API 키를 입력하세요:")
    api_key = input("> ").strip()
    
    setup_kakao_notifier(api_key)
