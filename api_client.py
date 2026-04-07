import requests
import os
import json
import logging
from openai import OpenAI

logger = logging.getLogger(__name__)

class APIClient:
    def __init__(self, bizinfo_key, kstartup_key, openai_key=None):
        self.bizinfo_key = bizinfo_key
        self.kstartup_key = kstartup_key
        
        # OpenAI API 키 확인 및 클라이언트 초기화
        # 환경변수에서 직접 가져오거나 인자로 받은 키를 사용
        self.openai_key = openai_key or os.getenv("OPENAI_API_KEY")
        
        if self.openai_key:
            try:
                # OpenAI 공식 라이브러리 규격에 맞춰 클라이언트 초기화
                self.openai_client = OpenAI(api_key=self.openai_key)
                logger.info("OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            logger.warning("OpenAI API key not found. Summarization feature will be disabled.")
            self.openai_client = None

    def fetch_bizinfo(self, hashtags=None, search_cnt=50):
        """기업마당 지원사업 공고 조회"""
        url = "https://www.bizinfo.go.kr/uss/rss/bizinfoApi.do"
        params = {
            "crtfcKey": self.bizinfo_key,
            "dataType": "json",
            "searchCnt": search_cnt
        }
        if hashtags:
            params["hashtags"] = hashtags
            
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                items = data.get('jsonArray', [])
                if not items and 'item' in data:
                    items = data['item']
                return items
            else:
                logger.error(f"Bizinfo API error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"Bizinfo API request failed: {e}")
            return []

    def fetch_kstartup(self, page=1, per_page=20, filters=None):
        """K-Startup 지원사업 공고 조회"""
        url = "http://apis.data.go.kr/B552735/kisedKstartupService01/getAnnouncementInformation01"
        params = {
            "serviceKey": self.kstartup_key,
            "page": page,
            "perPage": per_page,
            "returnType": "json"
        }
        if filters:
            for k, v in filters.items():
                params[f"cond[{k}]"] = v
                
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', [])
            else:
                logger.error(f"K-Startup API error: {response.status_code}")
                return []
        except Exception as e:
            logger.error(f"K-Startup API request failed: {e}")
            return []

    def summarize_announcement(self, title, content):
        """AI를 이용한 공고 내용 요약"""
        if not self.openai_client:
            return "현재 요약 기능을 사용할 수 없습니다. (OpenAI API 키 설정 확인 필요)"
            
        try:
            # 텍스트가 너무 길면 토큰 제한에 걸릴 수 있으므로 적절히 자름
            clean_content = content[:2000] if content else "내용 없음"
            
            prompt = f"""
            당신은 정부지원사업 전문가입니다. 다음 공고 내용을 분석하여 핵심 정보를 3줄로 요약해주세요.
            
            [공고명]: {title}
            [상세내용]: {clean_content}
            
            반드시 다음 형식을 지켜주세요:
            1. 지원대상: (요약)
            2. 지원내용: (요약)
            3. 신청기간: (요약)
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "정부지원사업 공고를 요약하는 전문가입니다. 한국어로 답변하세요."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5,
                max_tokens=500
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI summary request failed: {e}")
            return f"요약 생성 중 오류가 발생했습니다: {str(e)}"
