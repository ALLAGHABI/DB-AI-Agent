"""تسميات وصفية للأعمدة — التقرير التنفيذي يتحدث لغة الأعمال لا لغة الجداول.

`total_amount` تصير "قيمة المبيعات"، و`city` تصير "المدينة".
ما لا نعرفه نجمّله (shipping_address → "Shipping address")، والمستخدم يملك
الكلمة الأخيرة عبر تسميات يكتبها بنفسه.
"""
import re

# مفردات الأعمال الشائعة — المفتاح كلمة كاملة بعد التطبيع
_DICTIONARY: dict[str, tuple[str, str]] = {
    # (عربي، إنجليزي)
    "id": ("المعرف", "ID"),
    "name": ("الاسم", "Name"),
    "title": ("العنوان", "Title"),
    "description": ("الوصف", "Description"),
    "email": ("البريد الإلكتروني", "Email"),
    "phone": ("الهاتف", "Phone"),
    "address": ("العنوان", "Address"),
    "city": ("المدينة", "City"),
    "country": ("الدولة", "Country"),
    "region": ("المنطقة", "Region"),
    "branch": ("الفرع", "Branch"),
    "department": ("القسم", "Department"),
    "status": ("الحالة", "Status"),
    "type": ("النوع", "Type"),
    "category": ("الفئة", "Category"),
    "customer": ("العميل", "Customer"),
    "customers": ("العملاء", "Customers"),
    "client": ("العميل", "Client"),
    "user": ("المستخدم", "User"),
    "users": ("المستخدمون", "Users"),
    "subscriber": ("المشترك", "Subscriber"),
    "subscribers": ("المشتركون", "Subscribers"),
    "employee": ("الموظف", "Employee"),
    "product": ("المنتج", "Product"),
    "products": ("المنتجات", "Products"),
    "order": ("الطلب", "Order"),
    "orders": ("الطلبات", "Orders"),
    "invoice": ("الفاتورة", "Invoice"),
    "payment": ("الدفع", "Payment"),
    "amount": ("القيمة", "Amount"),
    "total": ("الإجمالي", "Total"),
    "price": ("السعر", "Price"),
    "cost": ("التكلفة", "Cost"),
    "revenue": ("الإيراد", "Revenue"),
    "sales": ("المبيعات", "Sales"),
    "profit": ("الربح", "Profit"),
    "salary": ("الراتب", "Salary"),
    "balance": ("الرصيد", "Balance"),
    "discount": ("الخصم", "Discount"),
    "tax": ("الضريبة", "Tax"),
    "quantity": ("الكمية", "Quantity"),
    "qty": ("الكمية", "Quantity"),
    "count": ("العدد", "Count"),
    "stock": ("المخزون", "Stock"),
    "units": ("الوحدات", "Units"),
    "date": ("التاريخ", "Date"),
    "time": ("الوقت", "Time"),
    "created": ("الإنشاء", "Created"),
    "updated": ("التحديث", "Updated"),
    "registration": ("التسجيل", "Registration"),
    "shipping": ("الشحن", "Shipping"),
    "delivery": ("التسليم", "Delivery"),
    "active": ("نشط", "Active"),
    "rating": ("التقييم", "Rating"),
    "score": ("النتيجة", "Score"),
    "age": ("العمر", "Age"),
    "gender": ("الجنس", "Gender"),
    "note": ("الملاحظة", "Note"),
    "notes": ("الملاحظات", "Notes"),
}

# صياغات مركّبة شائعة تُقرأ أفضل ككل
_PHRASES: dict[tuple[str, ...], tuple[str, str]] = {
    ("total", "amount"): ("قيمة المبيعات", "Sales value"),
    ("unit", "price"): ("سعر الوحدة", "Unit price"),
    ("order", "date"): ("تاريخ الطلب", "Order date"),
    ("created", "date"): ("تاريخ الإنشاء", "Created date"),
    ("created", "at"): ("تاريخ الإنشاء", "Created at"),
    ("registration", "date"): ("تاريخ التسجيل", "Registration date"),
    ("shipping", "address"): ("عنوان الشحن", "Shipping address"),
    ("stock", "quantity"): ("الكمية بالمخزون", "Stock quantity"),
    ("is", "active"): ("نشط", "Active"),
    ("first", "name"): ("الاسم الأول", "First name"),
    ("last", "name"): ("اسم العائلة", "Last name"),
}

_ARABIC = re.compile(r"[؀-ۿ]")


def _words(name: str) -> list[str]:
    """يفصل snake_case وcamelCase وkebab-case إلى كلمات صغيرة."""
    spaced = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", str(name))
    parts = re.split(r"[\s_\-.]+", spaced)
    return [p.lower() for p in parts if p]


def humanize(name: str, language: str = "en") -> str:
    """تسمية وصفية لعمود واحد."""
    raw = str(name).strip()
    if _ARABIC.search(raw):
        return raw                       # الاسم عربي أصلاً — يُترك كما هو

    words = _words(raw)
    if not words:
        return raw
    idx = 0 if language == "ar" else 1

    phrase = _PHRASES.get(tuple(words))
    if phrase:
        return phrase[idx]

    # تجاهل لاحقة id في الأعمدة المرجعية: customer_id → العميل
    if len(words) > 1 and words[-1] == "id":
        core = tuple(words[:-1])
        phrase = _PHRASES.get(core)
        if phrase:
            return phrase[idx]
        if len(core) == 1 and core[0] in _DICTIONARY:
            return _DICTIONARY[core[0]][idx]
        words = list(core)

    known = [_DICTIONARY[w][idx] for w in words if w in _DICTIONARY]
    if len(known) == len(words):
        return " ".join(known) if language != "ar" else " ".join(known)
    if len(words) == 1 and words[0] in _DICTIONARY:
        return _DICTIONARY[words[0]][idx]

    # لا نعرفها — نجمّل الاسم الأصلي
    pretty = " ".join(words)
    return pretty[:1].upper() + pretty[1:]


def label_columns(names: list[str], language: str = "en",
                  overrides: dict | None = None) -> dict:
    """خريطة اسم العمود → تسميته الوصفية، مع أولوية لما يكتبه المستخدم."""
    overrides = overrides or {}
    out = {}
    for name in names:
        custom = str(overrides.get(name, "")).strip()
        out[str(name)] = custom or humanize(name, language)
    return out
