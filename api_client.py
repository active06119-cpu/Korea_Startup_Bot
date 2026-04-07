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
        # OpenAI API 키가 있을 때만 클라이언트 초기화
        if openai_key:
            try:
                self.openai_client = OpenAI(api_key=openai_key)
                logger.info("OpenAI client initialized successfully.")
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                self.openai_client = None
        else:
            logger.warning("OpenAI API key not provided. Summarization feature will be disabled.")
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
                # API 응답 구조에 따라 추출 (보통 jsonArray 또는 item 리스트)
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
        """AI를 이용한 공고 내용 요약 (OpenAI 클라이언트가 활성화된 경우에만 작동)"""
        if not self.openai_client:
            return "현재 요약 기능을 사용할 수 없습니다. (OpenAI API 키가 설정되지 않았습니다.)"
            
        try:
            prompt = f"""
            다음 정부지원사업 공고 내용을 핵심 위주로 3줄 요약해줘.
            반드시 한국어로 작성하고, 지원대상, 지원내용, 신청기간이 포함되게 해줘.
            
            공고명: {title}
            내용: {content[:1500]}  # 텍스트가 너무 길면 자름
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "당신은 정부지원사업 전문가입니다."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=300
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"OpenAI summary failed: {e}")
            return "요약을 생성하는 중에 오류가 발생했습니다."
