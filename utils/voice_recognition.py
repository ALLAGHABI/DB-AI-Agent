"""
التعرف على الصوت - تحويل الصوت إلى نص
"""
import speech_recognition as sr
from typing import Tuple, Optional
import threading
import time


class VoiceRecognition:
    """مدير التعرف على الصوت"""
    
    def __init__(self, language: str = "ar-SA"):
        self.language = language
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.is_recording = False
        self.recording_thread = None
        self.result_callback = None
        
        # إعداد الميكروفون
        try:
            self.microphone = sr.Microphone()
            # ضبط مستوى الضوضاء المحيطة
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
        except Exception as e:
            print(f"خطأ في إعداد الميكروفون: {e}")
    
    def set_language(self, language: str):
        """تغيير لغة التعرف على الصوت"""
        self.language = language
    
    def is_microphone_available(self) -> bool:
        """التحقق من توفر الميكروفون"""
        return self.microphone is not None
    
    def record_audio(self, timeout: int = 5, phrase_time_limit: int = 10) -> Tuple[bool, str]:
        """
        تسجيل الصوت وتحويله إلى نص
        
        Args:
            timeout: مهلة انتظار بدء الكلام (ثواني)
            phrase_time_limit: الحد الأقصى لمدة التسجيل (ثواني)
            
        Returns:
            Tuple[bool, str]: (نجح, النص المُعرَّف عليه أو رسالة خطأ)
        """
        if not self.is_microphone_available():
            return False, "الميكروفون غير متوفر"
        
        try:
            with self.microphone as source:
                print("استمع...")
                # تسجيل الصوت
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
            
            print("جاري التعرف على الصوت...")
            
            # تحويل الصوت إلى نص باستخدام Google Speech Recognition
            try:
                text = self.recognizer.recognize_google(audio, language=self.language)
                return True, text
            except sr.UnknownValueError:
                return False, "لم يتم فهم الصوت بوضوح"
            except sr.RequestError as e:
                return False, f"خطأ في خدمة التعرف على الصوت: {e}"
                
        except sr.WaitTimeoutError:
            return False, "انتهت مهلة انتظار الصوت"
        except Exception as e:
            return False, f"خطأ في التسجيل: {str(e)}"
    
    def start_continuous_recording(self, callback_function):
        """
        بدء التسجيل المستمر (غير مستخدم حالياً)
        """
        if self.is_recording:
            return False, "التسجيل قيد التشغيل بالفعل"
        
        if not self.is_microphone_available():
            return False, "الميكروفون غير متوفر"
        
        self.result_callback = callback_function
        self.is_recording = True
        
        def recording_loop():
            while self.is_recording:
                try:
                    success, result = self.record_audio(timeout=1, phrase_time_limit=5)
                    if success and result.strip():
                        if self.result_callback:
                            self.result_callback(result)
                except Exception as e:
                    print(f"خطأ في التسجيل المستمر: {e}")
                    time.sleep(1)
        
        self.recording_thread = threading.Thread(target=recording_loop)
        self.recording_thread.daemon = True
        self.recording_thread.start()
        
        return True, "بدأ التسجيل المستمر"
    
    def stop_continuous_recording(self):
        """إيقاف التسجيل المستمر"""
        self.is_recording = False
        if self.recording_thread:
            self.recording_thread.join(timeout=2)
        return True, "تم إيقاف التسجيل"
    
    def test_microphone(self) -> Tuple[bool, str]:
        """اختبار الميكروفون"""
        if not self.is_microphone_available():
            return False, "الميكروفون غير متوفر"
        
        try:
            with self.microphone as source:
                # اختبار بسيط للتأكد من عمل الميكروفون
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            return True, "الميكروفون يعمل بشكل طبيعي"
        except Exception as e:
            return False, f"خطأ في اختبار الميكروفون: {str(e)}"
    
    def get_supported_languages(self) -> list:
        """الحصول على قائمة اللغات المدعومة"""
        return [
            ("ar-SA", "العربية (السعودية)"),
            ("ar-EG", "العربية (مصر)"),
            ("en-US", "English (US)"),
            ("en-GB", "English (UK)"),
            ("fr-FR", "Français"),
            ("de-DE", "Deutsch"),
            ("es-ES", "Español"),
            ("it-IT", "Italiano"),
            ("pt-BR", "Português (Brasil)"),
            ("ru-RU", "Русский"),
            ("zh-CN", "中文 (简体)"),
            ("ja-JP", "日本語"),
            ("ko-KR", "한국어")
        ]
