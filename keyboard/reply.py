from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

def get_main_keyboard():
    kb = [
        [KeyboardButton(text="💰 رصيدي"), KeyboardButton(text="📈 شراء سهم")],
        [KeyboardButton(text="🎁 كود هدية"), KeyboardButton(text="👤 حسابي")],
        [KeyboardButton(text="👥 الاحالات"), KeyboardButton(text="💬 غروب المساهمين")],
        [KeyboardButton(text="إهداء رصيد")],
        [KeyboardButton(text="🌐 التواصل الاجتماعي"), KeyboardButton(text="🛠️ الدعم")],
        [KeyboardButton(text="ℹ️ من نحن")],
        [KeyboardButton(text="اهلا وسهلا بك")],
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )


def buying():
    kb = [
        [KeyboardButton(text="الاكتتاب الأول")],
        [KeyboardButton(text="الاكتتاب الثاني")],
        [KeyboardButton(text="الاكتتاب الثالث")],
        [KeyboardButton(text="القائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )


def withdrawanddeposit():
    kb = [
        [KeyboardButton(text="شحن رصيد في البوت")],
        [KeyboardButton(text="سحب رصيد من البوت")],
        [KeyboardButton(text="القائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )

def deposit():
    kb = [
        [KeyboardButton(text="شحن رصيد عن طريق شام كاش")],
        [KeyboardButton(text="شحن رصيد عن طريق usdt pep20")],
        [KeyboardButton(text="شحن رصيد عن طريق usdt trc20")],
        [KeyboardButton(text="القائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )


def withdraw():
    kb = [
        [KeyboardButton(text="سحب رصيد عن طريق شام كاش")],
        [KeyboardButton(text="سحب رصيد عن طريق usdt pep20")],
        [KeyboardButton(text="سحب رصيد عن طريق usdt trc20")],
        [KeyboardButton(text="القائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )

def buy11():
    kb = [
        [KeyboardButton(text="شراء السهم مرة")],
        [KeyboardButton(text="شراء السهم مرتين")],
        [KeyboardButton(text="شراء السهم 5 مرات")],
        [KeyboardButton(text="شراء السهم 10 مرات")],
        [KeyboardButton(text="شراء السهم 20 مرة")],
        [KeyboardButton(text="شراء السهم 50 مرة")],
        [KeyboardButton(text="القائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="اختر من القائمة أدناه..."
    )




# كيبورد الآدمن الجديد 🛠️
def get_admin_keyboard():
    kb = [
        [KeyboardButton(text="➕ إضافة كود هدية"), KeyboardButton(text="👥 عرض كل المستخدمين")],
        [KeyboardButton(text="إضافة رصيد لمستخدم"), KeyboardButton(text="حذف رصيد لمستخدم")],
        [KeyboardButton(text="إذاعة")],
        [KeyboardButton(text="🔙 العودة للقائمة الرئيسية")]
    ]
    return ReplyKeyboardMarkup(
        keyboard=kb,
        resize_keyboard=True,
        input_field_placeholder="لوحة تحكم الإدارة..."
    )



