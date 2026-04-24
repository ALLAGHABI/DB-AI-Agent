#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اختبار مباشر لـ OpenRouter API لتحديد المشكلة
"""
import requests
import json
import sys

def test_openrouter_api():
    """اختبار مباشر للـ API"""
    
    # طلب مفتاح API من المستخدم
    api_key = "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"
    
    if not api_key:
        print("❌ لم يتم إدخال مفتاح API")
        return False
    
    # إعداد الطلب
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8080",
        "X-Title": "DB-AI-Agent"
    }
    
    payload = {
        "model": "anthropic/claude-3.5-sonnet",
        "messages": [
            {"role": "user", "content": "Hello, respond with just 'OK'"}
        ],
        "max_tokens": 10
    }
    
    print("🔄 جاري اختبار الاتصال...")
    
    try:
        # الطريقة الأولى: استخدام json parameter
        print("\n1️⃣ اختبار باستخدام json parameter:")
        response1 = requests.post(url, headers=headers, json=payload, timeout=30)
        print(f"Status Code: {response1.status_code}")
        print(f"Response: {response1.text[:200]}")
        
        if response1.status_code == 200:
            print("✅ نجح الاتصال بالطريقة الأولى")
            return True
        
        # الطريقة الثانية: استخدام data مع json.dumps
        print("\n2️⃣ اختبار باستخدام data parameter:")
        json_data = json.dumps(payload)
        response2 = requests.post(url, headers=headers, data=json_data, timeout=30)
        print(f"Status Code: {response2.status_code}")
        print(f"Response: {response2.text[:200]}")
        
        if response2.status_code == 200:
            print("✅ نجح الاتصال بالطريقة الثانية")
            return True
        
        # الطريقة الثالثة: استخدام session
        print("\n3️⃣ اختبار باستخدام Session:")
        session = requests.Session()
        session.headers.update(headers)
        response3 = session.post(url, json=payload, timeout=30)
        print(f"Status Code: {response3.status_code}")
        print(f"Response: {response3.text[:200]}")
        
        if response3.status_code == 200:
            print("✅ نجح الاتصال بالطريقة الثالثة")
            return True
        
        # تحليل الأخطاء
        print("\n❌ فشل جميع الطرق:")
        if response1.status_code == 401:
            print("- مفتاح API غير صحيح أو منتهي الصلاحية")
        elif response1.status_code == 429:
            print("- تم تجاوز حد الاستخدام")
        elif response1.status_code == 403:
            print("- ممنوع الوصول - تحقق من صلاحيات المفتاح")
        else:
            print(f"- خطأ غير متوقع: {response1.status_code}")
            
        return False
        
    except requests.exceptions.ConnectionError:
        print("❌ خطأ في الاتصال بالإنترنت")
        return False
    except requests.exceptions.Timeout:
        print("❌ انتهت مهلة الاتصال")
        return False
    except Exception as e:
        print(f"❌ خطأ غير متوقع: {e}")
        return False

if __name__ == "__main__":
    print("🧪 اختبار OpenRouter API")
    print("=" * 50)
    
    success = test_openrouter_api()
    
    if success:
        print("\n🎉 الاختبار نجح! المشكلة ليست في الاتصال بالـ API")
    else:
        print("\n💡 المشكلة في:")
        print("1. مفتاح API غير صحيح")
        print("2. عدم وجود رصيد في الحساب")
        print("3. مشكلة في الشبكة")
        print("4. مشكلة في إعدادات OpenRouter")
