# -*- coding: utf-8 -*-
"""
مدير قاعدة البيانات - يتعامل مع أنواع مختلفة من قواعد البيانات
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

from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError
import pandas as pd
from typing import Tuple, List, Dict, Any, Optional
import json

class DatabaseHandler:
    """مدير قاعدة البيانات"""
    
    def __init__(self):
        self.engine = None
        self.schema_cache = {}
        self.schema_file = "data/schema_cache.json"
        self.is_connected = False
        self._ensure_data_directory()
    
    def _ensure_data_directory(self):
        """إنشاء مجلد البيانات إذا لم يكن موجوداً"""
        data_dir = os.path.dirname(self.schema_file)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir)
    
    def connect(self, connection_string: str) -> Tuple[bool, str]:
        """الاتصال بقاعدة البيانات"""
        try:
            # للتحقق من وجود ملف SQLite قبل الاتصال
            if connection_string.startswith('sqlite:///'):
                sqlite_path = connection_string.replace('sqlite:///', '')
                if not os.path.exists(sqlite_path):
                    return False, f"ملف قاعدة البيانات غير موجود: {sqlite_path}"
            
            self.engine = create_engine(connection_string)
            # اختبار الاتصال
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()  # التأكد من وجود بيانات
            
            self.is_connected = True
            return True, "تم الاتصال بنجاح"
            
        except SQLAlchemyError as e:
            self.is_connected = False
            return False, f"فشل الاتصال: {str(e)}"
        except Exception as e:
            self.is_connected = False
            return False, f"خطأ غير متوقع: {str(e)}"
    
    def disconnect(self):
        """قطع الاتصال مع قاعدة البيانات"""
        if self.engine:
            self.engine.dispose()
            self.engine = None
        self.is_connected = False
    
    def test_connection(self) -> bool:
        """اختبار الاتصال الحالي"""
        if not self.engine:
            return False
        
        try:
            with self.engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except Exception:
            self.is_connected = False
            return False
    
    def inspect_schema(self) -> Tuple[bool, str]:
        """فحص وحفظ مخطط قاعدة البيانات"""
        if not self.is_connected or not self.engine:
            return False, "لا يوجد اتصال بقاعدة البيانات"
        
        try:
            inspector = inspect(self.engine)
            schema = {}
            
            # الحصول على جميع الجداول
            table_names = inspector.get_table_names()
            
            for table_name in table_names:
                columns = inspector.get_columns(table_name)
                schema[table_name] = {
                    'columns': [
                        {
                            'name': col['name'],
                            'type': str(col['type']),
                            'nullable': col['nullable'],
                            'default': str(col['default']) if col['default'] else None
                        }
                        for col in columns
                    ]
                }
                
                # الحصول على المفاتيح الأساسية
                try:
                    pk_constraint = inspector.get_pk_constraint(table_name)
                    schema[table_name]['primary_keys'] = pk_constraint.get('constrained_columns', [])
                except Exception:
                    schema[table_name]['primary_keys'] = []
                
                # الحصول على المفاتيح الخارجية
                try:
                    foreign_keys = inspector.get_foreign_keys(table_name)
                    schema[table_name]['foreign_keys'] = [
                        {
                            'constrained_columns': fk['constrained_columns'],
                            'referred_table': fk['referred_table'],
                            'referred_columns': fk['referred_columns']
                        }
                        for fk in foreign_keys
                    ]
                except Exception:
                    schema[table_name]['foreign_keys'] = []
            
            self.schema_cache = schema
            self._save_schema_cache()
            
            return True, f"تم فحص {len(table_names)} جدول بنجاح"
            
        except Exception as e:
            return False, f"خطأ في فحص المخطط: {str(e)}"
    
    def _save_schema_cache(self):
        """حفظ مخطط قاعدة البيانات في ملف"""
        try:
            with open(self.schema_file, 'w', encoding='utf-8') as f:
                json.dump(self.schema_cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"خطأ في حفظ المخطط: {e}")
    
    def _load_schema_cache(self):
        """تحميل مخطط قاعدة البيانات من الملف"""
        if os.path.exists(self.schema_file):
            try:
                with open(self.schema_file, 'r', encoding='utf-8') as f:
                    self.schema_cache = json.load(f)
            except Exception as e:
                print(f"خطأ في تحميل المخطط: {e}")
                self.schema_cache = {}
    
    def get_schema_text(self) -> str:
        """الحصول على وصف نصي لمخطط قاعدة البيانات"""
        if not self.schema_cache:
            self._load_schema_cache()
        
        if not self.schema_cache:
            return "لا يوجد مخطط محفوظ. يرجى تحديث المخطط أولاً."
        
        schema_text = "مخطط قاعدة البيانات:\n\n"
        
        for table_name, table_info in self.schema_cache.items():
            schema_text += f"الجدول: {table_name}\n"
            
            # الأعمدة
            schema_text += "الأعمدة:\n"
            for col in table_info['columns']:
                nullable = "يقبل NULL" if col['nullable'] else "لا يقبل NULL"
                default = f" (افتراضي: {col['default']})" if col['default'] else ""
                schema_text += f"  - {col['name']}: {col['type']} ({nullable}){default}\n"
            
            # المفاتيح الأساسية
            if table_info.get('primary_keys'):
                schema_text += f"المفاتيح الأساسية: {', '.join(table_info['primary_keys'])}\n"
            
            # المفاتيح الخارجية
            if table_info.get('foreign_keys'):
                schema_text += "المفاتيح الخارجية:\n"
                for fk in table_info['foreign_keys']:
                    schema_text += f"  - {', '.join(fk['constrained_columns'])} -> {fk['referred_table']}.{', '.join(fk['referred_columns'])}\n"
            
            schema_text += "\n"
        
        return schema_text
    
    def execute_query(self, query: str) -> Tuple[bool, Any, str]:
        """تنفيذ استعلام SQL"""
        if not self.is_connected or not self.engine:
            return False, None, "لا يوجد اتصال بقاعدة البيانات"
        
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query))
                
                # إذا كان الاستعلام SELECT، إرجاع البيانات
                if query.strip().upper().startswith('SELECT'):
                    # تحويل النتيجة إلى DataFrame للعرض الأفضل
                    df = pd.DataFrame(result.fetchall(), columns=result.keys())
                    return True, df, "تم تنفيذ الاستعلام بنجاح"
                else:
                    # للاستعلامات الأخرى، إرجاع عدد الصفوف المتأثرة
                    conn.commit()
                    affected_rows = result.rowcount
                    return True, affected_rows, f"تم تنفيذ الاستعلام بنجاح. تأثر {affected_rows} صف"
                    
        except SQLAlchemyError as e:
            return False, None, f"خطأ في تنفيذ الاستعلام: {str(e)}"
        except Exception as e:
            return False, None, f"خطأ غير متوقع: {str(e)}"
    
    def is_destructive_query(self, query: str) -> bool:
        """التحقق من أن الاستعلام قد يكون مدمراً"""
        query_upper = query.strip().upper()
        destructive_keywords = ['UPDATE', 'DELETE', 'INSERT', 'DROP', 'ALTER', 'TRUNCATE', 'CREATE']
        
        for keyword in destructive_keywords:
            if query_upper.startswith(keyword):
                return True
        
        return False
    
    def get_table_names(self) -> List[str]:
        """الحصول على أسماء الجداول"""
        if not self.schema_cache:
            self._load_schema_cache()
        
        return list(self.schema_cache.keys())
    
    def get_table_info(self, table_name: str) -> Optional[Dict]:
        """الحصول على معلومات جدول محدد"""
        if not self.schema_cache:
            self._load_schema_cache()
        
        return self.schema_cache.get(table_name)
    
    def refresh_schema(self) -> Tuple[bool, str]:
        """تحديث مخطط قاعدة البيانات"""
        return self.inspect_schema()
