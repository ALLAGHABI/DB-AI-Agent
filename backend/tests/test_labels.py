from app.reports.labels import humanize, label_columns


def test_common_business_columns_in_arabic():
    assert humanize("total_amount", "ar") == "قيمة المبيعات"
    assert humanize("city", "ar") == "المدينة"
    assert humanize("status", "ar") == "الحالة"
    assert humanize("order_date", "ar") == "تاريخ الطلب"
    assert humanize("quantity", "ar") == "الكمية"
    assert humanize("subscribers", "ar") == "المشتركون"


def test_common_business_columns_in_english():
    assert humanize("total_amount", "en") == "Sales value"
    assert humanize("city", "en") == "City"
    assert humanize("stock_quantity", "en") == "Stock quantity"


def test_camel_and_kebab_are_split():
    assert humanize("orderDate", "ar") == "تاريخ الطلب"
    assert humanize("unit-price", "en") == "Unit price"


def test_reference_columns_drop_the_id_suffix():
    assert humanize("customer_id", "ar") == "العميل"
    assert humanize("product_id", "en") == "Product"


def test_unknown_columns_are_prettified_not_left_raw():
    assert humanize("warehouse_code", "en") == "Warehouse code"
    assert humanize("col_x7", "ar") == "Col x7"          # لا نعرفها — تُجمَّل فقط


def test_arabic_column_names_are_left_alone():
    assert humanize("المدينة", "ar") == "المدينة"
    assert humanize("إجمالي المبيعات", "en") == "إجمالي المبيعات"


def test_label_columns_map_and_user_overrides_win():
    labels = label_columns(["total_amount", "city"], "ar",
                           overrides={"city": "الفرع"})
    assert labels == {"total_amount": "قيمة المبيعات", "city": "الفرع"}


def test_blank_override_falls_back_to_auto():
    labels = label_columns(["city"], "ar", overrides={"city": "   "})
    assert labels["city"] == "المدينة"
