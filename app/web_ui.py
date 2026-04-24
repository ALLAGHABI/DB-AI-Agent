# -*- coding: utf-8 -*-
"""
واجهة الويب للتطبيق
"""
import os
import sys
import locale

# ضبط التشفير قبل استيراد Flask
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    pass

from flask import Flask, render_template, request, jsonify, redirect, url_for
import json
from .settings_manager import SettingsManager
from .database_handler import DatabaseHandler
from .ai_agent import AIAgent


class WebApp:
    """تطبيق الويب الرئيسي"""
    
    def __init__(self):
        self.app = Flask(__name__, template_folder='../templates', static_folder='../static')
        self.app.secret_key = 'db-ai-agent-secret-key'
        
        # المكونات الأساسية
        self.settings = SettingsManager()
        self.db_handler = DatabaseHandler()
        self.ai_agent = None
        
        # إعداد المسارات
        self.setup_routes()
    
    def setup_routes(self):
        """إعداد مسارات التطبيق"""
        
        @self.app.route('/')
        def index():
            """الصفحة الرئيسية"""
            return render_template('index.html')
        
        @self.app.route('/api/test_ai', methods=['POST'])
        def test_ai_connection():
            """اختبار الاتصال مع OpenRouter API"""
            data = request.get_json()
            api_key = data.get('api_key', '').strip()
            model = data.get('model', 'anthropic/claude-3.5-sonnet')
            
            if not api_key:
                return jsonify({'success': False, 'message': 'يرجى إدخال مفتاح API'})
            
            # إنشاء وكيل ذكاء اصطناعي مؤقت للاختبار
            test_agent = AIAgent(api_key, model)
            success, message = test_agent.test_connection()
            
            if success:
                # حفظ مفتاح API إذا كان الاتصال ناجحاً
                self.settings.set_api_key(api_key)
                self.settings.save_settings()
                self.ai_agent = test_agent
                return jsonify({
                    'success': True, 
                    'message': message,
                    'model': model,
                    'api_status': 'connected'
                })
            else:
                return jsonify({
                    'success': False, 
                    'message': message,
                    'api_status': 'failed'
                })
            
            return jsonify({'success': success, 'message': message})
        
        @self.app.route('/api/connect', methods=['POST'])
        def connect_database():
            """الاتصال بقاعدة البيانات"""
            data = request.get_json()
            
            # حفظ الإعدادات
            if 'api_key' in data and data['api_key']:
                self.settings.set_api_key(data['api_key'])
            
            if 'db_type' in data:
                self.settings.set('database.type', data['db_type'])
                
                if data['db_type'] == 'sqlite' and 'sqlite_file' in data:
                    sqlite_file = data['sqlite_file'].strip()
                    if not sqlite_file:
                        return jsonify({'success': False, 'message': 'يرجى تحديد ملف قاعدة البيانات'})
                    
                    # إذا كان المسار نسبي، جعله مطلق
                    if not os.path.isabs(sqlite_file):
                        # إذا كان اسم ملف فقط، ابحث عنه في المجلد الحالي ومجلد data
                        if '/' not in sqlite_file and '\\' not in sqlite_file:
                            possible_paths = [
                                sqlite_file,
                                f'data/{sqlite_file}',
                                os.path.join(os.getcwd(), sqlite_file),
                                os.path.join(os.getcwd(), 'data', sqlite_file)
                            ]
                            
                            found_path = None
                            for path in possible_paths:
                                if os.path.exists(path):
                                    found_path = os.path.abspath(path)
                                    break
                            
                            if found_path:
                                sqlite_file = found_path
                            else:
                                return jsonify({'success': False, 'message': f'ملف قاعدة البيانات غير موجود: {sqlite_file}'})
                        else:
                            sqlite_file = os.path.abspath(sqlite_file)
                    
                    # التحقق من وجود الملف
                    if not os.path.exists(sqlite_file):
                        return jsonify({'success': False, 'message': f'ملف قاعدة البيانات غير موجود: {sqlite_file}'})
                    
                    self.settings.set('database.sqlite_file', sqlite_file)
                elif data['db_type'] in ['mysql', 'postgresql']:
                    self.settings.set('database.host', data.get('host', ''))
                    self.settings.set('database.port', data.get('port', ''))
                    self.settings.set('database.database', data.get('database', ''))
                    self.settings.set('database.username', data.get('username', ''))
                    if 'password' in data:
                        self.settings.set_database_password(data['password'])
            
            self.settings.save_settings()
            
            # محاولة الاتصال
            connection_string = self.settings.get_database_connection_string()
            if not connection_string:
                return jsonify({'success': False, 'message': 'إعدادات قاعدة البيانات غير مكتملة'})
            
            success, message = self.db_handler.connect(connection_string)
            
            if success:
                # إنشاء وكيل الذكاء الاصطناعي
                api_key = self.settings.get_api_key()
                if api_key:
                    self.ai_agent = AIAgent(api_key)
                
                # فحص المخطط
                schema_success, schema_message = self.db_handler.inspect_schema()
                if schema_success:
                    message += f" - {schema_message}"
            
            return jsonify({'success': success, 'message': message})
        
        @self.app.route('/api/browse_file', methods=['POST'])
        def browse_file():
            """تصفح الملفات (محاكاة - في الواقع سيتم تنفيذها من جانب العميل)"""
            # هذا endpoint للمساعدة في تصفح الملفات
            # في تطبيق ويب حقيقي، يجب استخدام file input من HTML
            import glob
            
            # البحث عن ملفات SQLite في المجلد الحالي
            db_files = []
            for pattern in ['*.db', '*.sqlite', '*.sqlite3']:
                db_files.extend(glob.glob(f'data/{pattern}'))
                db_files.extend(glob.glob(pattern))
            
            return jsonify({
                'success': True,
                'files': db_files,
                'current_dir': os.getcwd()
            })
        
        @self.app.route('/api/execute', methods=['POST'])
        def execute_query():
            """تنفيذ الاستعلام"""
            data = request.get_json()
            user_request = data.get('query', '').strip()
            ai_model = data.get('ai_model', 'anthropic/claude-3.5-sonnet')
            
            if not user_request:
                return jsonify({'success': False, 'message': 'يرجى إدخال طلب'})
            
            if not self.db_handler.is_connected:
                return jsonify({'success': False, 'message': 'يجب الاتصال بقاعدة البيانات أولاً'})
            
            if not self.ai_agent:
                return jsonify({'success': False, 'message': 'يرجى إدخال مفتاح OpenRouter API'})
            
            # تحديث نموذج الذكاء الاصطناعي
            self.ai_agent.set_model(ai_model)
            
            # تحويل الطلب إلى SQL
            schema = self.db_handler.get_schema_text()
            success, sql_query, error = self.ai_agent.generate_sql(user_request, schema)
            
            if not success:
                return jsonify({'success': False, 'message': f'خطأ في الذكاء الاصطناعي: {error}'})
            
            # تنفيذ الاستعلام
            exec_success, result, exec_message = self.db_handler.execute_query(sql_query)
            
            response_data = {
                'success': exec_success,
                'message': exec_message,
                'sql_query': sql_query,
                'is_destructive': self.db_handler.is_destructive_query(sql_query)
            }
            
            if exec_success and hasattr(result, 'to_dict'):
                # إذا كانت النتيجة DataFrame
                # تحويل البيانات باستخدام json.loads(json.dumps(...)) لضمان توافق الأنواع
                try:
                    # تحويل القيم إلى قاموس
                    records = result.to_dict('records')
                    # استخدام json.dumps مع default=str لمعالجة التواريخ والأنواع غير المدعومة
                    safe_records = json.loads(json.dumps(records, default=str))
                    
                    response_data['data'] = safe_records
                    response_data['columns'] = [str(c) for c in result.columns] # تأكد من أن أسماء الأعمدة نصوص
                except Exception as e:
                    print(f"Error serializing data: {e}")
                    # محاولة بديلة بسيطة
                    response_data['data'] = result.astype(str).to_dict('records')
                    response_data['columns'] = list(result.columns)
                    
            elif exec_success and isinstance(result, int):
                response_data['affected_rows'] = result
            
            return jsonify(response_data)
        
        @self.app.route('/api/status')
        def get_status():
            """الحصول على حالة التطبيق"""
            return jsonify({
                'db_connected': self.db_handler.is_connected,
                'ai_configured': self.ai_agent is not None,
                'db_type': self.settings.get('database.type', 'sqlite'),
                'tables': self.db_handler.get_table_names() if self.db_handler.is_connected else []
            })
        
        @self.app.route('/api/refresh_schema', methods=['POST'])
        def refresh_schema():
            """تحديث مخطط قاعدة البيانات"""
            if not self.db_handler.is_connected:
                return jsonify({'success': False, 'message': 'يجب الاتصال بقاعدة البيانات أولاً'})
            
            success, message = self.db_handler.refresh_schema()
            return jsonify({'success': success, 'message': message})
        
        @self.app.route('/api/settings', methods=['GET'])
        def get_settings():
            """الحصول على الإعدادات المحفوظة"""
            return jsonify({
                'api_key': self.settings.get_api_key(),
                'db_type': self.settings.get('database.type', 'sqlite'),
                'sqlite_file': self.settings.get('database.sqlite_file', ''),
                'ai_model': self.settings.get('ai.model', 'anthropic/claude-3.5-sonnet')
            })
    
    def run(self, debug=True, port=5000):
        """تشغيل التطبيق"""
        self.app.run(debug=debug, port=port, host='0.0.0.0')
