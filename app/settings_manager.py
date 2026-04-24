# -*- coding: utf-8 -*-
"""
مدير الإعدادات - يتعامل مع حفظ وتشفير الإعدادات
"""
import os
import sys
import locale

# ضبط التشفير
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    pass

from cryptography.fernet import Fernet
import json
from typing import Dict, Any, Optional
import base64


class SettingsManager:
    """مدير الإعدادات للتطبيق"""
    
    def __init__(self, settings_file: str = "data/settings.json"):
        self.settings_file = settings_file
        self.settings = {}
        self._encryption_key = None
        self._ensure_data_directory()
        self.load_settings()
    
    def _ensure_data_directory(self):
        """إنشاء مجلد البيانات إذا لم يكن موجوداً"""
        data_dir = os.path.dirname(self.settings_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def _get_encryption_key(self) -> bytes:
        """الحصول على مفتاح التشفير أو إنشاء واحد جديد"""
        if self._encryption_key is None:
            key_file = "data/.key"
            if os.path.exists(key_file):
                with open(key_file, 'rb') as f:
                    self._encryption_key = f.read()
            else:
                self._encryption_key = Fernet.generate_key()
                with open(key_file, 'wb') as f:
                    f.write(self._encryption_key)
        return self._encryption_key
    
    def _encrypt_value(self, value: str) -> str:
        """تشفير قيمة حساسة"""
        if not value:
            return ""
        key = self._get_encryption_key()
        fernet = Fernet(key)
        encrypted = fernet.encrypt(value.encode())
        return base64.b64encode(encrypted).decode()
    
    def _decrypt_value(self, encrypted_value: str) -> str:
        """فك تشفير قيمة"""
        if not encrypted_value:
            return ""
        try:
            key = self._get_encryption_key()
            fernet = Fernet(key)
            encrypted_bytes = base64.b64decode(encrypted_value.encode())
            decrypted = fernet.decrypt(encrypted_bytes)
            return decrypted.decode()
        except Exception:
            return ""
    
    def load_settings(self):
        """تحميل الإعدادات من الملف"""
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r', encoding='utf-8') as f:
                    self.settings = json.load(f)
            except Exception as e:
                print(f"خطأ في تحميل الإعدادات: {e}")
                self.settings = {}
        else:
            self.settings = self._get_default_settings()
    
    def save_settings(self):
        """حفظ الإعدادات في الملف"""
        try:
            with open(self.settings_file, 'w', encoding='utf-8') as f:
                json.dump(self.settings, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"خطأ في حفظ الإعدادات: {e}")
    
    def _get_default_settings(self) -> Dict[str, Any]:
        """الإعدادات الافتراضية"""
        return {
            "database": {
                "type": "sqlite",
                "host": "",
                "port": "",
                "database": "",
                "username": "",
                "password_encrypted": "",
                "sqlite_file": ""
            },
            "ai": {
                "api_key_encrypted": "",
                "model": "mistralai/mistral-7b-instruct",
                "available_models": [
                    "mistralai/mistral-7b-instruct",
                    "google/gemini-pro",
                    "anthropic/claude-3-haiku",
                    "openai/gpt-3.5-turbo",
                    "openai/gpt-4"
                ]
            },
            "ui": {
                "theme": "dark",
                "language": "ar"
            },
            "voice": {
                "enabled": True,
                "language": "ar-SA"
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """الحصول على قيمة إعداد"""
        keys = key.split('.')
        value = self.settings
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        return value
    
    def set(self, key: str, value: Any):
        """تعيين قيمة إعداد"""
        keys = key.split('.')
        current = self.settings
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
        current[keys[-1]] = value
    
    def get_database_password(self) -> str:
        """الحصول على كلمة مرور قاعدة البيانات المفكوكة التشفير"""
        encrypted = self.get("database.password_encrypted", "")
        return self._decrypt_value(encrypted)
    
    def set_database_password(self, password: str):
        """تعيين كلمة مرور قاعدة البيانات مع التشفير"""
        encrypted = self._encrypt_value(password)
        self.set("database.password_encrypted", encrypted)
    
    def get_api_key(self) -> str:
        """الحصول على مفتاح API المفكوك التشفير"""
        encrypted = self.get("ai.api_key_encrypted", "")
        return self._decrypt_value(encrypted)
    
    def set_api_key(self, api_key: str):
        """تعيين مفتاح API مع التشفير"""
        encrypted = self._encrypt_value(api_key)
        self.set("ai.api_key_encrypted", encrypted)
    
    def get_database_connection_string(self) -> Optional[str]:
        """إنشاء نص الاتصال بقاعدة البيانات"""
        db_type = self.get("database.type")
        
        if db_type == "sqlite":
            sqlite_file = self.get("database.sqlite_file")
            if sqlite_file:
                return f"sqlite:///{sqlite_file}"
        
        elif db_type in ["mysql", "postgresql"]:
            host = self.get("database.host")
            port = self.get("database.port")
            database = self.get("database.database")
            username = self.get("database.username")
            password = self.get_database_password()
            
            if all([host, database, username]):
                if db_type == "mysql":
                    port = port or 3306
                    return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
                elif db_type == "postgresql":
                    port = port or 5432
                    return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        return None
    
    def is_configured(self) -> bool:
        """التحقق من أن التطبيق مكون بشكل صحيح"""
        has_db = self.get_database_connection_string() is not None
        has_api_key = bool(self.get_api_key())
        return has_db and has_api_key
