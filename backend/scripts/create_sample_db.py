#!/usr/bin/env python3
"""
إنشاء قاعدة بيانات SQLite تجريبية مع بيانات وهمية
"""
import sqlite3
import random
from datetime import datetime, timedelta

def create_sample_database():
    """إنشاء قاعدة بيانات تجريبية"""
    
    # الاتصال بقاعدة البيانات (سيتم إنشاؤها إذا لم تكن موجودة)
    conn = sqlite3.connect('data/sample_store.db')
    cursor = conn.cursor()
    
    # إنشاء جدول العملاء
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS customers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE,
        phone TEXT,
        city TEXT,
        registration_date DATE,
        is_active BOOLEAN DEFAULT 1
    )
    ''')
    
    # إنشاء جدول الفئات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS categories (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT
    )
    ''')
    
    # إنشاء جدول المنتجات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category_id INTEGER,
        price DECIMAL(10,2),
        stock_quantity INTEGER,
        description TEXT,
        created_date DATE,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    ''')
    
    # إنشاء جدول الطلبات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER,
        order_date DATE,
        total_amount DECIMAL(10,2),
        status TEXT DEFAULT 'pending',
        shipping_address TEXT,
        FOREIGN KEY (customer_id) REFERENCES customers (id)
    )
    ''')
    
    # إنشاء جدول تفاصيل الطلبات
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        product_id INTEGER,
        quantity INTEGER,
        unit_price DECIMAL(10,2),
        FOREIGN KEY (order_id) REFERENCES orders (id),
        FOREIGN KEY (product_id) REFERENCES products (id)
    )
    ''')
    
    # إدراج بيانات العملاء
    customers_data = [
        ('أحمد محمد', 'ahmed@email.com', '0501234567', 'الرياض', '2023-01-15', 1),
        ('فاطمة علي', 'fatima@email.com', '0509876543', 'جدة', '2023-02-20', 1),
        ('خالد سعد', 'khaled@email.com', '0555555555', 'الدمام', '2023-03-10', 1),
        ('نورا حسن', 'nora@email.com', '0544444444', 'الرياض', '2023-04-05', 1),
        ('سعد الغامدي', 'saad@email.com', '0533333333', 'مكة', '2023-05-12', 1),
        ('مريم القحطاني', 'mariam@email.com', '0522222222', 'المدينة', '2023-06-18', 1),
        ('عبدالله النجار', 'abdullah@email.com', '0511111111', 'الطائف', '2023-07-25', 1),
        ('هند الشهري', 'hind@email.com', '0566666666', 'أبها', '2023-08-30', 1),
        ('محمد الزهراني', 'mohammed@email.com', '0577777777', 'جازان', '2023-09-15', 0),
        ('سارة العتيبي', 'sara@email.com', '0588888888', 'حائل', '2023-10-20', 1)
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO customers (name, email, phone, city, registration_date, is_active)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', customers_data)
    
    # إدراج بيانات الفئات
    categories_data = [
        ('إلكترونيات', 'أجهزة إلكترونية ومعدات تقنية'),
        ('ملابس', 'ملابس رجالية ونسائية وأطفال'),
        ('كتب', 'كتب ومجلات ومواد تعليمية'),
        ('رياضة', 'معدات رياضية وأدوات لياقة'),
        ('منزل ومطبخ', 'أدوات منزلية ومطبخية'),
        ('جمال وعناية', 'منتجات تجميل وعناية شخصية')
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO categories (name, description)
    VALUES (?, ?)
    ''', categories_data)
    
    # إدراج بيانات المنتجات
    products_data = [
        ('آيفون 15', 1, 4999.00, 25, 'هاتف ذكي من آبل', '2023-01-01'),
        ('لابتوب ديل', 1, 2500.00, 15, 'لابتوب للأعمال', '2023-01-05'),
        ('سماعات بلوتوث', 1, 299.00, 50, 'سماعات لاسلكية', '2023-01-10'),
        ('قميص قطني', 2, 89.00, 100, 'قميص رجالي قطني', '2023-01-15'),
        ('فستان صيفي', 2, 150.00, 75, 'فستان نسائي للصيف', '2023-01-20'),
        ('كتاب البرمجة', 3, 75.00, 30, 'كتاب تعلم البرمجة', '2023-02-01'),
        ('رواية عربية', 3, 45.00, 40, 'رواية أدبية', '2023-02-05'),
        ('دمبل 5 كيلو', 4, 120.00, 20, 'دمبل للتمارين', '2023-02-10'),
        ('حبل قفز', 4, 35.00, 60, 'حبل للتمارين الرياضية', '2023-02-15'),
        ('مقلاة تيفال', 5, 180.00, 35, 'مقلاة غير لاصقة', '2023-03-01'),
        ('خلاط كهربائي', 5, 250.00, 25, 'خلاط متعدد الاستخدامات', '2023-03-05'),
        ('كريم مرطب', 6, 65.00, 80, 'كريم للبشرة الجافة', '2023-03-10'),
        ('شامبو طبيعي', 6, 55.00, 90, 'شامبو للشعر الدهني', '2023-03-15')
    ]
    
    cursor.executemany('''
    INSERT OR IGNORE INTO products (name, category_id, price, stock_quantity, description, created_date)
    VALUES (?, ?, ?, ?, ?, ?)
    ''', products_data)
    
    # إنشاء طلبات وهمية
    orders_data = []
    order_items_data = []
    
    # إنشاء 20 طلب وهمي
    for i in range(1, 21):
        customer_id = random.randint(1, 10)
        order_date = datetime.now() - timedelta(days=random.randint(1, 90))
        status = random.choice(['pending', 'processing', 'shipped', 'delivered', 'cancelled'])
        shipping_address = f'عنوان العميل {customer_id}'
        
        # حساب إجمالي الطلب
        num_items = random.randint(1, 4)
        total_amount = 0
        current_order_items = []
        
        for j in range(num_items):
            product_id = random.randint(1, 13)
            quantity = random.randint(1, 3)
            # الحصول على سعر المنتج (سنستخدم سعر ثابت للبساطة)
            unit_price = random.uniform(50, 500)
            total_amount += unit_price * quantity
            
            current_order_items.append((i, product_id, quantity, round(unit_price, 2)))
        
        orders_data.append((customer_id, order_date.strftime('%Y-%m-%d'), round(total_amount, 2), status, shipping_address))
        order_items_data.extend(current_order_items)
    
    cursor.executemany('''
    INSERT OR IGNORE INTO orders (customer_id, order_date, total_amount, status, shipping_address)
    VALUES (?, ?, ?, ?, ?)
    ''', orders_data)
    
    cursor.executemany('''
    INSERT OR IGNORE INTO order_items (order_id, product_id, quantity, unit_price)
    VALUES (?, ?, ?, ?)
    ''', order_items_data)
    
    # حفظ التغييرات
    conn.commit()
    conn.close()
    
    print("✅ تم إنشاء قاعدة البيانات التجريبية بنجاح!")
    print("📍 مسار الملف: data/sample_store.db")
    print("\n📊 البيانات المُدرجة:")
    print("- 10 عملاء")
    print("- 6 فئات منتجات")
    print("- 13 منتج")
    print("- 20 طلب مع تفاصيلها")

if __name__ == "__main__":
    create_sample_database()
