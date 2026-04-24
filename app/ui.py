"""
واجهة المستخدم الرئيسية - واجهة بسيطة لإرسال المطالبات
"""
import customtkinter as ctk
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import threading
from typing import Optional
import pandas as pd

from .settings_manager import SettingsManager
from .database_handler import DatabaseHandler
from .ai_agent import AIAgent
# from ..utils.voice_recognition import VoiceRecognition


class SimpleDBApp:
    """التطبيق الرئيسي - واجهة بسيطة"""
    
    def __init__(self):
        # إعداد المظهر
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # المكونات الأساسية
        self.settings = SettingsManager()
        self.db_handler = DatabaseHandler()
        self.ai_agent = None
        # self.voice_recognition = VoiceRecognition()
        
        # إعداد النافذة الرئيسية
        self.root = ctk.CTk()
        self.root.title("DB-AI-Agent - وكيل قاعدة البيانات الذكي")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # متغيرات الواجهة
        self.is_recording = False
        self.current_query = ""
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        """إعداد واجهة المستخدم"""
        # الإطار الرئيسي
        main_frame = ctk.CTkFrame(self.root)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # العنوان
        title_label = ctk.CTkLabel(
            main_frame, 
            text="🤖 وكيل قاعدة البيانات الذكي", 
            font=ctk.CTkFont(size=24, weight="bold")
        )
        title_label.pack(pady=(20, 30))
        
        # إطار الإعدادات السريعة
        self.setup_quick_settings(main_frame)
        
        # إطار الإدخال
        self.setup_input_frame(main_frame)
        
        # إطار النتائج
        self.setup_results_frame(main_frame)
        
        # شريط الحالة
        self.setup_status_bar()
    
    def setup_quick_settings(self, parent):
        """إعداد الإعدادات السريعة"""
        settings_frame = ctk.CTkFrame(parent)
        settings_frame.pack(fill="x", pady=(0, 20))
        
        # عنوان الإعدادات
        settings_title = ctk.CTkLabel(settings_frame, text="الإعدادات السريعة", font=ctk.CTkFont(size=16, weight="bold"))
        settings_title.pack(pady=(10, 5))
        
        # صف الإعدادات
        settings_row = ctk.CTkFrame(settings_frame)
        settings_row.pack(fill="x", padx=20, pady=(0, 15))
        
        # مفتاح API
        api_frame = ctk.CTkFrame(settings_row)
        api_frame.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(api_frame, text="مفتاح OpenRouter API:").pack(anchor="w", padx=10, pady=(10, 5))
        self.api_key_entry = ctk.CTkEntry(api_frame, placeholder_text="أدخل مفتاح API", show="*")
        self.api_key_entry.pack(fill="x", padx=10, pady=(0, 10))
        
        # نوع قاعدة البيانات
        db_frame = ctk.CTkFrame(settings_row)
        db_frame.pack(side="right", padx=(10, 0))
        
        ctk.CTkLabel(db_frame, text="نوع قاعدة البيانات:").pack(anchor="w", padx=10, pady=(10, 5))
        self.db_type_var = ctk.StringVar(value="sqlite")
        self.db_type_menu = ctk.CTkOptionMenu(
            db_frame, 
            values=["sqlite", "mysql", "postgresql"],
            variable=self.db_type_var,
            command=self.on_db_type_change
        )
        self.db_type_menu.pack(padx=10, pady=(0, 10))
        
        # أزرار الإعدادات
        buttons_frame = ctk.CTkFrame(settings_frame)
        buttons_frame.pack(fill="x", padx=20, pady=(0, 15))
        
        self.connect_btn = ctk.CTkButton(buttons_frame, text="🔗 اتصال", command=self.connect_database)
        self.connect_btn.pack(side="left", padx=(0, 10))
        
        self.refresh_schema_btn = ctk.CTkButton(buttons_frame, text="🔄 تحديث المخطط", command=self.refresh_schema)
        self.refresh_schema_btn.pack(side="left", padx=(0, 10))
        
        self.settings_btn = ctk.CTkButton(buttons_frame, text="⚙️ إعدادات متقدمة", command=self.open_advanced_settings)
        self.settings_btn.pack(side="right")
    
    def setup_input_frame(self, parent):
        """إعداد إطار الإدخال"""
        input_frame = ctk.CTkFrame(parent)
        input_frame.pack(fill="x", pady=(0, 20))
        
        # عنوان الإدخال
        input_title = ctk.CTkLabel(input_frame, text="أدخل طلبك باللغة الطبيعية", font=ctk.CTkFont(size=16, weight="bold"))
        input_title.pack(pady=(15, 10))
        
        # صندوق النص
        self.query_textbox = ctk.CTkTextbox(input_frame, height=100, font=ctk.CTkFont(size=14))
        self.query_textbox.pack(fill="x", padx=20, pady=(0, 15))
        
        # أزرار الإدخال
        input_buttons = ctk.CTkFrame(input_frame)
        input_buttons.pack(fill="x", padx=20, pady=(0, 15))
        
        self.execute_btn = ctk.CTkButton(
            input_buttons, 
            text="🚀 تنفيذ", 
            command=self.execute_query,
            font=ctk.CTkFont(size=14, weight="bold"),
            height=40
        )
        self.execute_btn.pack(side="left", padx=(0, 10))
        
        # self.voice_btn = ctk.CTkButton(
        #     input_buttons, 
        #     text="🎤 تسجيل صوتي", 
        #     command=self.toggle_voice_recording,
        #     height=40
        # )
        # self.voice_btn.pack(side="left", padx=(0, 10))
        
        self.clear_btn = ctk.CTkButton(input_buttons, text="🗑️ مسح", command=self.clear_input)
        self.clear_btn.pack(side="right")
    
    def setup_results_frame(self, parent):
        """إعداد إطار النتائج"""
        results_frame = ctk.CTkFrame(parent)
        results_frame.pack(fill="both", expand=True)
        
        # عنوان النتائج
        results_title = ctk.CTkLabel(results_frame, text="النتائج", font=ctk.CTkFont(size=16, weight="bold"))
        results_title.pack(pady=(15, 10))
        
        # إطار النتائج مع تبويبات
        self.results_notebook = ttk.Notebook(results_frame)
        self.results_notebook.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        # تبويب البيانات
        self.data_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.data_frame, text="البيانات")
        
        # تبويب SQL
        self.sql_frame = ttk.Frame(self.results_notebook)
        self.results_notebook.add(self.sql_frame, text="استعلام SQL")
        
        # إعداد عرض البيانات
        self.setup_data_display()
        
        # إعداد عرض SQL
        self.setup_sql_display()
    
    def setup_data_display(self):
        """إعداد عرض البيانات"""
        # جدول البيانات
        self.data_tree = ttk.Treeview(self.data_frame)
        self.data_tree.pack(fill="both", expand=True, padx=10, pady=10)
        
        # شريط التمرير للجدول
        data_scrollbar_y = ttk.Scrollbar(self.data_frame, orient="vertical", command=self.data_tree.yview)
        data_scrollbar_y.pack(side="right", fill="y")
        self.data_tree.configure(yscrollcommand=data_scrollbar_y.set)
        
        data_scrollbar_x = ttk.Scrollbar(self.data_frame, orient="horizontal", command=self.data_tree.xview)
        data_scrollbar_x.pack(side="bottom", fill="x")
        self.data_tree.configure(xscrollcommand=data_scrollbar_x.set)
    
    def setup_sql_display(self):
        """إعداد عرض SQL"""
        self.sql_textbox = tk.Text(self.sql_frame, wrap=tk.WORD, font=("Courier", 12))
        self.sql_textbox.pack(fill="both", expand=True, padx=10, pady=10)
        
        # شريط التمرير لـ SQL
        sql_scrollbar = ttk.Scrollbar(self.sql_frame, orient="vertical", command=self.sql_textbox.yview)
        sql_scrollbar.pack(side="right", fill="y")
        self.sql_textbox.configure(yscrollcommand=sql_scrollbar.set)
    
    def setup_status_bar(self):
        """إعداد شريط الحالة"""
        self.status_frame = ctk.CTkFrame(self.root)
        self.status_frame.pack(fill="x", side="bottom", padx=20, pady=(0, 20))
        
        self.status_label = ctk.CTkLabel(self.status_frame, text="جاهز للاستخدام")
        self.status_label.pack(side="left", padx=20, pady=10)
        
        self.connection_status = ctk.CTkLabel(self.status_frame, text="❌ غير متصل")
        self.connection_status.pack(side="right", padx=20, pady=10)
    
    def load_settings(self):
        """تحميل الإعدادات"""
        # تحميل مفتاح API
        api_key = self.settings.get_api_key()
        if api_key:
            self.api_key_entry.insert(0, api_key)
        
        # تحميل نوع قاعدة البيانات
        db_type = self.settings.get("database.type", "sqlite")
        self.db_type_var.set(db_type)
        
        # محاولة الاتصال التلقائي إذا كانت الإعدادات موجودة
        if self.settings.is_configured():
            self.connect_database()
    
    def on_db_type_change(self, value):
        """عند تغيير نوع قاعدة البيانات"""
        self.settings.set("database.type", value)
        self.settings.save_settings()
    
    def connect_database(self):
        """الاتصال بقاعدة البيانات"""
        def connect_thread():
            self.update_status("جاري الاتصال...")
            
            # حفظ مفتاح API
            api_key = self.api_key_entry.get().strip()
            if api_key:
                self.settings.set_api_key(api_key)
                self.settings.save_settings()
                self.ai_agent = AIAgent(api_key)
            
            # الحصول على نص الاتصال
            if self.db_type_var.get() == "sqlite":
                file_path = filedialog.askopenfilename(
                    title="اختر ملف قاعدة البيانات SQLite",
                    filetypes=[("SQLite files", "*.db *.sqlite *.sqlite3"), ("All files", "*.*")]
                )
                if file_path:
                    self.settings.set("database.sqlite_file", file_path)
                    self.settings.save_settings()
                else:
                    self.update_status("تم إلغاء الاتصال")
                    return
            
            connection_string = self.settings.get_database_connection_string()
            if not connection_string:
                self.update_status("❌ إعدادات قاعدة البيانات غير مكتملة")
                return
            
            # محاولة الاتصال
            success, message = self.db_handler.connect(connection_string)
            
            if success:
                self.connection_status.configure(text="✅ متصل")
                self.update_status("تم الاتصال بنجاح")
                # فحص المخطط تلقائياً
                self.refresh_schema()
            else:
                self.connection_status.configure(text="❌ غير متصل")
                self.update_status(f"❌ فشل الاتصال: {message}")
                messagebox.showerror("خطأ في الاتصال", message)
        
        threading.Thread(target=connect_thread, daemon=True).start()
    
    def refresh_schema(self):
        """تحديث مخطط قاعدة البيانات"""
        def refresh_thread():
            self.update_status("جاري تحديث المخطط...")
            success, message = self.db_handler.inspect_schema()
            
            if success:
                self.update_status(f"✅ {message}")
            else:
                self.update_status(f"❌ {message}")
                messagebox.showerror("خطأ", message)
        
        if self.db_handler.is_connected:
            threading.Thread(target=refresh_thread, daemon=True).start()
        else:
            messagebox.showwarning("تحذير", "يجب الاتصال بقاعدة البيانات أولاً")
    
    def execute_query(self):
        """تنفيذ الاستعلام"""
        user_request = self.query_textbox.get("1.0", tk.END).strip()
        
        if not user_request:
            messagebox.showwarning("تحذير", "يرجى إدخال طلب")
            return
        
        if not self.db_handler.is_connected:
            messagebox.showerror("خطأ", "يجب الاتصال بقاعدة البيانات أولاً")
            return
        
        if not self.ai_agent:
            messagebox.showerror("خطأ", "يرجى إدخال مفتاح OpenRouter API")
            return
        
        def execute_thread():
            self.update_status("جاري تحويل الطلب إلى SQL...")
            
            # الحصول على مخطط قاعدة البيانات
            schema = self.db_handler.get_schema_text()
            
            # تحويل الطلب إلى SQL
            success, sql_query, error = self.ai_agent.generate_sql(user_request, schema)
            
            if not success:
                self.update_status(f"❌ خطأ في الذكاء الاصطناعي: {error}")
                messagebox.showerror("خطأ في الذكاء الاصطناعي", error)
                return
            
            # عرض SQL
            self.sql_textbox.delete("1.0", tk.END)
            self.sql_textbox.insert("1.0", sql_query)
            
            # التحقق من الاستعلامات المدمرة
            if self.db_handler.is_destructive_query(sql_query):
                result = messagebox.askyesno(
                    "تأكيد التنفيذ", 
                    f"هذا الاستعلام قد يغير البيانات:\n\n{sql_query}\n\nهل تريد المتابعة؟"
                )
                if not result:
                    self.update_status("تم إلغاء التنفيذ")
                    return
            
            # تنفيذ الاستعلام
            self.update_status("جاري تنفيذ الاستعلام...")
            success, result, message = self.db_handler.execute_query(sql_query)
            
            if success:
                self.update_status(f"✅ {message}")
                
                # عرض النتائج
                if isinstance(result, pd.DataFrame) and not result.empty:
                    self.display_dataframe(result)
                    self.results_notebook.select(0)  # التبديل إلى تبويب البيانات
                else:
                    self.clear_data_display()
                    if isinstance(result, int):
                        messagebox.showinfo("نتيجة", f"تم تنفيذ الاستعلام بنجاح\nعدد الصفوف المتأثرة: {result}")
            else:
                self.update_status(f"❌ خطأ في التنفيذ: {message}")
                messagebox.showerror("خطأ في التنفيذ", message)
        
        threading.Thread(target=execute_thread, daemon=True).start()
    
    def display_dataframe(self, df):
        """عرض DataFrame في الجدول"""
        # مسح البيانات السابقة
        self.clear_data_display()
        
        # إعداد الأعمدة
        columns = list(df.columns)
        self.data_tree["columns"] = columns
        self.data_tree["show"] = "headings"
        
        # إعداد رؤوس الأعمدة
        for col in columns:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=150)
        
        # إدراج البيانات
        for index, row in df.iterrows():
            self.data_tree.insert("", "end", values=list(row))
    
    def clear_data_display(self):
        """مسح عرض البيانات"""
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)
    
    # Voice recording methods disabled for now
    # def toggle_voice_recording(self):
    #     """تبديل تسجيل الصوت"""
    #     pass
    
    def clear_input(self):
        """مسح الإدخال"""
        self.query_textbox.delete("1.0", tk.END)
        self.update_status("تم مسح الإدخال")
    
    def open_advanced_settings(self):
        """فتح الإعدادات المتقدمة"""
        messagebox.showinfo("قريباً", "الإعدادات المتقدمة ستكون متوفرة قريباً")
    
    def update_status(self, message):
        """تحديث شريط الحالة"""
        self.status_label.configure(text=message)
        self.root.update_idletasks()
    
    def run(self):
        """تشغيل التطبيق"""
        self.root.mainloop()


if __name__ == "__main__":
    app = SimpleDBApp()
    app.run()
