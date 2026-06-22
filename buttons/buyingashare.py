from aiogram import Router, F
from aiogram.types import Message
import database.db as db
# تأكد من استيراد كيبورد buy11 وكيبورد القائمة الرئيسية الخاص بك
from keyboard.reply import buy11, get_main_keyboard , buying

router = Router()


@router.message(lambda c: c.text == "📈 شراء سهم")
async def buy_share(message: Message):
    await message.answer("📊 قسم شراء الأسهم:\nيرجى تحديد عدد الأسهم التي ترغب بالاستثمار بها.", reply_markup= buying())

# سعر السهم الثابت المذكور في رسالتك
SHARE_PRICE = 10

# 1. عند الضغط على "الاكتتاب الأول" تظهر قائمة الـ buy11
@router.message(F.text == "الاكتتاب الأول")
async def buy_share_menu(message: Message):
    await message.answer(
        f"📊 قسم الاكتتاب الأول:\n\n"
        f"🔹 سعر السهم الواحد: {SHARE_PRICE}$\n"
        f"🔹 الحد الأقصى للشراء دفعة واحدة: 50 مرة\n\n"
        f"الرجاء تحديد عدد مرات الشراء من الأزرار أدناه:\n"
        f"مدة الاكتتاب الاول 3 شهور فقط من تاريخ 14/6/2026 الى تاريخ 14/9/2026",
        reply_markup=buy11()
    )

# 2. التقاط عمليات الشراء المختلفة ومعالجتها يدوياً أو ديناميكياً
@router.message(F.text.startswith("شراء السهم"))
async def process_share_buying(message: Message):
    user_id = message.from_user.id
    button_text = message.text
    SHARE_PRICE = 10  # السهم بـ 10
    
    # تحديد كمية الأسهم من نص الزر
    if "50" in button_text: multiplier = 50
    elif "20" in button_text: multiplier = 20
    elif "10" in button_text: multiplier = 10
    elif "5" in button_text: multiplier = 5
    elif "مرتين" in button_text: multiplier = 2
    elif "مرة" in button_text: multiplier = 1
    else: return

    # استدعاء العملية المقيدة من قاعدة البيانات
    result = await db.buy_shares_process(tg_id=user_id, multiplier=multiplier, price_per_share=SHARE_PRICE)
    
    if result["status"] == "success":
        await message.answer(
            f"✅ تمت عملية الشراء بنجاح!\n\n"
            f"📈 تم شراء {multiplier} سهم جديد.\n"
            f"💸 التكلفة المخصومة: {result['total_cost']}$\n"
            f"📦 إجمالي أسهمك الآن: {result['new_shares']} / 50 سهم.",
            parse_mode="Markdown"
        )
    else:
        # إرسال رسائل الرفض (سواء بسبب تخطي الـ 20 سهم أو نقص الرصيد)
        await message.answer(result["message"], parse_mode="Markdown")

# 3. العودة للقائمة الرئيسية من كيبورد الشراء
@router.message(F.text == "القائمة الرئيسية")
async def back_to_home(message: Message):
    await message.answer(
        "🔄 تم العودة إلى القائمة الرئيسية:",
        reply_markup=get_main_keyboard()
    )


@router.message(lambda c: c.text == "الاكتتاب الثاني")
async def buy_share(message: Message):
    await message.answer("قريباً")
    
@router.message(lambda c: c.text == "الاكتتاب الثالث")
async def buy_share(message: Message):
    await message.answer("قريباً",)


