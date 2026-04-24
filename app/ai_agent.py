# -*- coding: utf-8 -*-
import json
import os
import sys
from typing import Tuple

# Force UTF-8 at system level
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LC_ALL'] = 'C.UTF-8'
os.environ['LANG'] = 'C.UTF-8'

# Patch urllib3 to handle UTF-8 properly
import urllib3
from urllib3.poolmanager import PoolManager
from urllib3._collections import HTTPHeaderDict

# Store original method
_original_urlopen = PoolManager.urlopen

def _patched_urlopen(self, method, url, *args, **kwargs):
    # Force UTF-8 encoding for all requests
    if 'body' in kwargs and kwargs['body']:
        if isinstance(kwargs['body'], str):
            kwargs['body'] = kwargs['body'].encode('utf-8')
        elif isinstance(kwargs['body'], bytes):
            # Ensure it's valid UTF-8
            try:
                kwargs['body'].decode('utf-8')
            except UnicodeDecodeError:
                kwargs['body'] = kwargs['body'].decode('latin-1').encode('utf-8')
    
    # Ensure headers specify UTF-8
    if 'headers' in kwargs:
        if isinstance(kwargs['headers'], dict):
            kwargs['headers'] = HTTPHeaderDict(kwargs['headers'])
        if 'content-type' in kwargs['headers']:
            ct = kwargs['headers']['content-type']
            if 'charset' not in ct.lower():
                kwargs['headers']['content-type'] = ct + '; charset=utf-8'
    
    return _original_urlopen(self, method, url, *args, **kwargs)

# Apply the patch
PoolManager.urlopen = _patched_urlopen

# Now import requests after patching
import requests
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class AIAgent:
    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json; charset=utf-8",
            "HTTP-Referer": "http://localhost:8080",
            "X-Title": "DB-AI-Agent",
            "Accept": "application/json; charset=utf-8",
            "Accept-Charset": "utf-8",
            "User-Agent": "DB-AI-Agent/1.0"
        }
    
    def set_model(self, model: str):
        """تغيير نموذج الذكاء الاصطناعي"""
        self.model = model
    
    def set_api_key(self, api_key: str):
        """تغيير مفتاح API"""
        self.api_key = api_key
        self.headers["Authorization"] = f"Bearer {api_key}"
    
    def generate_sql(self, user_request: str, schema: str) -> Tuple[bool, str, str]:
        """تحويل طلب المستخدم باللغة الطبيعية إلى استعلام SQL"""
        if not self.api_key:
            return False, "", "مفتاح API غير موجود"
        
        system_message = """You are an SQL expert. Convert the user's natural language request to a single executable SQL query based on the provided database schema.

Rules:
1. Return ONLY SQL code, no explanations
2. Use only table and column names from the schema
3. Ensure the query is syntactically correct
4. If unclear, write a simple SELECT query

Database schema:
""" + schema

        user_message = f"User request: {user_request}"
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ],
            "max_tokens": 500,
            "temperature": 0.1
        }
        
        try:
            # Convert payload to UTF-8 JSON bytes manually
            json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            # Use raw requests.post with explicit UTF-8 data
            response = requests.post(
                self.base_url,
                data=json_data,
                headers=self.headers,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    sql_query = result['choices'][0]['message']['content'].strip()
                    sql_query = self._clean_sql_response(sql_query)
                    return True, sql_query, ""
                else:
                    return False, "", "لم يتم الحصول على رد من الذكاء الاصطناعي"
            
            elif response.status_code == 401:
                return False, "", "مفتاح API غير صحيح"
            elif response.status_code == 429:
                return False, "", "تم تجاوز حد الاستخدام"
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}'
                return False, "", f"خطأ من الخادم: {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "", "انتهت مهلة الاتصال"
        except requests.exceptions.ConnectionError:
            return False, "", "خطأ في الاتصال بالإنترنت"
        except Exception as e:
            print(f"DEBUG - Exception type: {type(e).__name__}")
            print(f"DEBUG - Exception message: {str(e)}")
            import traceback
            traceback.print_exc()
            return False, "", f"خطأ غير متوقع: {str(e)}"
    
    def _clean_sql_response(self, response: str) -> str:
        """تنظيف رد الذكاء الاصطناعي للحصول على SQL فقط"""
        # إزالة علامات الكود إذا وجدت
        if "```sql" in response:
            response = response.split("```sql")[1].split("```")[0]
        elif "```" in response:
            response = response.split("```")[1].split("```")[0]
        
        # إزالة المسافات الزائدة والأسطر الفارغة
        lines = [line.strip() for line in response.split('\n') if line.strip()]
        
        # إزالة التعليقات
        sql_lines = []
        for line in lines:
            if not line.startswith('--') and not line.startswith('#'):
                sql_lines.append(line)
        
        return ' '.join(sql_lines).strip()
    
    def test_connection(self) -> Tuple[bool, str]:
        """اختبار الاتصال مع OpenRouter API"""
        if not self.api_key:
            return False, "مفتاح API غير موجود"
        
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": "Test"}],
            "max_tokens": 5
        }
        
        try:
            # Use same method as generate_sql for consistency
            json_data = json.dumps(payload, ensure_ascii=False).encode('utf-8')
            
            response = requests.post(
                self.base_url,
                data=json_data,
                headers=self.headers,
                timeout=10
            )
            
            print(f"DEBUG - Status Code: {response.status_code}")
            print(f"DEBUG - Response: {response.text[:200]}")
            
            if response.status_code == 200:
                return True, "الاتصال ناجح"
            elif response.status_code == 401:
                return False, "مفتاح API غير صحيح"
            elif response.status_code == 429:
                return False, "تم تجاوز حد الاستخدام"
            else:
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', f'HTTP {response.status_code}')
                except:
                    error_msg = f'HTTP {response.status_code}'
                return False, f"خطأ من الخادم: {error_msg}"
                
        except Exception as e:
            print(f"DEBUG - Exception: {str(e)}")
            return False, f"خطأ في الاتصال: {str(e)}"
    
    def get_available_models(self) -> list:
        """الحصول على قائمة النماذج المتاحة"""
        return [
            "anthropic/claude-3.5-sonnet",
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "google/gemini-pro-1.5",
            "meta-llama/llama-3.1-405b-instruct",
            "meta-llama/llama-3.1-70b-instruct",
            "mistralai/mistral-large"
        ]
