from aiogram import Router, F, Bot
from aiogram.types import Message
from aiogram.filters import Command
from keyboard.reply import get_main_keyboard, get_admin_keyboard  # استيراد الكيبورد الجديد
import database.db as db
from aiogram.fsm.context import FSMContext
import asyncio

router = Router()

from aiogram.fsm.state import StatesGroup, State

# حالات إضافة الرصيد من قبل الآدمن
class AdminAddBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

# حالات حذف الرصيد من قبل الآدمن
class AdminRemoveBalanceStates(StatesGroup):
    waiting_for_user_id = State()
    waiting_for_amount = State()

class BroadcastStates(StatesGroup):
    waiting_for_message = State()  # انتظار الرسالة (نص، صورة، فيديو إلخ)

# ايدي الآدمن الخاص بك (ضع ايديك الحقيقي هنا)
ADMIN_ID = 7100531076,8935105840,7448760922

# 1. فتح لوحة التحكم عند إرسال الكلمة السرية Admin0 أو أمر /admin
@router.message(F.text == "Admin0")
@router.message(Command("admin"))
async def open_admin_panel(message: Message):
    if message.from_user.id not in ADMIN_ID:
        await message.answer("⚠️ عذراً، هذا الأمر مخصص لإدارة البوت فقط.")
        return
        
    await message.answer(
        "⚙️ أهلاً بك في لوحة تحكم الآدمن\n"
        "الرجاء اختيار الإجراء المطلوب من الأزرار أدناه:",
        reply_markup=get_admin_keyboard()
    )

# 2. زر عرض كل المستخدمين من كيبورد الآدمن
@router.message(F.text == "👥 عرض كل المستخدمين")
async def admin_get_users(message: Message):
    # 1. التأكد من أن مرسل الأمر هو الآدمن (تأكد أن ADMIN_ID قائمة أو عدل الشرط)
    if message.from_user.id not in ADMIN_ID:
        return
        
    try:
        # 2. جلب قائمة المستخدمين
        users = await db.get_all_users() # أو get_all_users() مباشرة حسب ملفاتك
        
        if not users:
            await message.answer("📁 لا يوجد مستخدمين مسجلين في النظام بعد.")
            return
            
        response = "<b>👥 قائمة المستخدمين وتفاصيل أسهمهم:</b>\n\n"
        
        # 3. بناء نص الرسالة باستخدام HTML لتفادي مشاكل الـ Username
        for user in users:
            # تنظيف اليوزر لضمان عدم وجود كود HTML بداخل الاسم
            username = user['username'] if user['username'] else "لا يوجد يوزر"
            username_text = f"@{username}" if user['username'] else username
            
            response += (
                f"<b>🆔 الآيدي:</b> <code>{user['tg_id']}</code>\n"
                f"<b>👤 الحساب:</b> {username_text}\n"
                f"<b>💰 الرصيد:</b> {user['balance']}\n"
                f"<b>📈 الأسهم المشتراة:</b> {user['remaining_shares']} / 20 سهم\n"
                f"<b>👥 الإحالات:</b> {user['referrals']}\n"
                f"---------------------------\n"
            )
            
        # 4. إرسال التقرير باستخدام HTML
        await message.answer(response, parse_mode="HTML")

    except Exception as e:
        # في حال حدوث أي خطأ آخر، البوت سيخبرك به في الشات بدلاً من التجاهل
        await message.answer(f"❌ حدث خطأ أثناء جلب البيانات:\n<code>{e}</code>", parse_mode="HTML")
# 3. زر إضافة كود هدية (يرشد الآدمن لطريقة الكتابة الصحيحة)
@router.message(F.text == "➕ إضافة كود هدية")
async def admin_add_code_hint(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    await message.answer(
        "قم بإرسال الأمر بالشكل التالي لإضافة الكود:\n\n"
        "/addcode [الرمز] [القيمة]\n\n"
        "مثال:\n/addcode VIP2026 100",
        parse_mode="Markdown"
    )

# 4. معالجة أمر الإضافة الفعلي /addcode
@router.message(Command("addcode"))
async def admin_add_code_process(message: Message):
    if message.from_user.id not in ADMIN_ID:
        return
    try:
        args = message.text.split()
        code = args[1]
        amount = float(args[2])
        
        await db.add_gift_code(code, amount)
        await message.answer(f"✅ تم إضافة كود الهدية بنجاح!\n🔹 الكود: {code}\n🔹 القيمة: {amount}$", parse_mode="Markdown")
    except (IndexError, ValueError):
        await message.answer("⚠️ خطأ في الصيغة! استخدم:\n/addcode [الرمز] [القيمة]")

# 5. زر العودة للقائمة الرئيسية للآدمن لرؤية البوت كمستخدم عادي
@router.message(F.text == "🔙 العودة للقائمة الرئيسية")
async def back_to_main(message: Message):
    await message.answer(
        "🔄 تم العودة للقائمة الرئيسية لبوت المستخدمين:",
        reply_markup=get_main_keyboard()
    )


@router.message(F.text == "إضافة رصيد لمستخدم")
async def admin_add_balance_start(message: Message, state: FSMContext):
    # حماية: التأكد من أن المرسل هو الآدمن
    if message.from_user.id not in ADMIN_ID:
        return

    await message.answer("📥 <b>[قسم الإدارة] - إضافة رصيد:</b>\n\nيرجى إرسال <b>آيدي (ID)</b> المستخدم المراد إضافة الرصيد له:")
    await state.set_state(AdminAddBalanceStates.waiting_for_user_id)


@router.message(AdminAddBalanceStates.waiting_for_user_id)
async def admin_add_balance_user(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ يجب إرسال الآيدي كأرقام فقط!\nأعد المحاولة:")
        return

    target_id = int(text)
    
    # التحقق من وجود المستخدم في الداتابيز
    user_exists = await db.get_user(target_id)
    if not user_exists:
        await message.answer("❌ هذا الآيدي غير مسجل في البوت مطلقاً!\nتأكد من الرقم وأعد إرساله:")
        return

    await state.update_data(target_id=target_id)
    await message.answer(f"👤 تم تحديد المستخدم بنجاح.\n💰 الآن أرسل <b>المبلغ</b> المراد إضافته لحسابه (أرقام فقط):")
    await state.set_state(AdminAddBalanceStates.waiting_for_amount)


@router.message(AdminAddBalanceStates.waiting_for_amount)
async def admin_add_balance_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ يجب أن يكون المبلغ أكبر من الصفر!\nأعد إدخال المبلغ:")
            return
    except ValueError:
        await message.answer("⚠️ عذراً، يجب إرسال المبلغ كأرقام فقط!\nأعد إدخال المبلغ:")
        return

    user_data = await state.get_data()
    target_id = user_data.get('target_id')

    # تنفيذ الإضافة في قاعدة البيانات
    await db.admin_modify_balance(user_id=target_id, amount=amount, operation="add")

    # إشعار الآدمن بالنجاح
    await message.answer(f"✅ تم إضافة <b>{amount}$</b> بنجاح إلى حساب المستخدم ذو الآيدي: <code>{target_id}</code>")

    # إشعار المستخدم تلقائياً بأن الإدارة شحنت له رصيد 🎉
    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"💰 <b>إشعار شحن رصيد:</b>\n\n"
                 f"قام المسؤول بإضافة <b>{amount}</b> إلى رصيدك بنجاح! 🚀",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للمستخدم (ربما حظر البوت): {e}")

    await state.clear()


# ==================== ❌ قسم حذف رصيد من مستخدم ====================

@router.message(F.text == "حذف رصيد لمستخدم") # أو النص المكتوب على زر الحذف لديك
async def admin_remove_balance_start(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_ID:
        return

    await message.answer("📤 <b>[قسم الإدارة] - سحب/حذف رصيد:</b>\n\nيرجى إرسال <b>آيدي (ID)</b> المستخدم المراد خصم الرصيد منه:")
    await state.set_state(AdminRemoveBalanceStates.waiting_for_user_id)


@router.message(AdminRemoveBalanceStates.waiting_for_user_id)
async def admin_remove_balance_user(message: Message, state: FSMContext):
    text = message.text.strip()
    if not text.isdigit():
        await message.answer("⚠️ يجب إرسال الآيدي كأرقام فقط!\nأعد المحاولة:")
        return

    target_id = int(text)
    user_exists = await db.get_user(target_id)
    if not user_exists:
        await message.answer("❌ هذا الآيدي غير مسجل في البوت مطلقاً!\nتأكد من الرقم وأعد إرساله:")
        return

    await state.update_data(target_id=target_id)
    await message.answer(f"👤 تم تحديد المستخدم بنجاح.\n📉 الآن أرسل <b>المبلغ</b> المراد خصمه/حذفه من حسابه (أرقام فقط):")
    await state.set_state(AdminRemoveBalanceStates.waiting_for_amount)

@router.message(AdminRemoveBalanceStates.waiting_for_amount)
async def admin_remove_balance_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ يجب أن يكون المبلغ أكبر من الصفر!\nأعد إدخال المبلغ:")
            return
    except ValueError:
        await message.answer("⚠️ عذراً، يجب إرسال المبلغ كأرقام فقط!\nأعد إدخال المبلغ:")
        return

    user_data = await state.get_data()
    target_id = user_data.get('target_id')

    # تنفيذ الخصم في قاعدة البيانات
    await db.admin_modify_balance(user_id=target_id, amount=amount, operation="remove")

    # إشعار الآدمن بالنجاح
    await message.answer(f"📉 تم خصم <b>{amount}$</b> بنجاح من حساب المستخدم ذو الآيدي: <code>{target_id}</code>")

    # إشعار المستخدم تلقائياً بالخصم
    try:
        await bot.send_message(
            chat_id=target_id,
            text=f"⚠️ <b>تحديث مالي:</b>\n\n"
                 f"تم خصم/تعديل مبلغ <b>{amount}$</b> من رصيدك بواسطة الإدارة.",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للمستخدم: {e}")

    await state.clear()

@router.message(F.text == "إذاعة")
async def start_broadcast(message: Message, state: FSMContext):
    # حماية: التأكد من أن المرسل هو الآدمن
    if message.from_user.id not in ADMIN_ID:
        return

    await message.answer(
        "📢 <b>[قسم الإدارة] - إنشاء إذاعة عامة:</b>\n\n"
        "يرجى إرسال الرسالة التي تريد نشرها الآن لجميع المستخدمين.\n"
        "<i>(يمكنك إرسال: نص عادي، صورة، فيديو، متحركة، أو حتى عمل Forward من قناة)</i>"
    )
    await state.set_state(BroadcastStates.waiting_for_message)


# 2. استقبال الرسالة وإذاعتها للجميع بشكل ذكي وآمن 🚀
@router.message(BroadcastStates.waiting_for_message)
async def process_broadcast_message(message: Message, state: FSMContext, bot: Bot):
    if message.from_user.id not in ADMIN_ID:
        await state.clear()
        return

    # إشعار الآدمن ببدء العملية فوراً لأن الإذاعة قد تأخذ بعض الوقت بناءً على عدد المشتركين
    status_msg = await message.answer("⏳ جاري بدء الإذاعة وإرسال الرسالة لجميع المشتركين، يرجى الانتظار...")
    
    # جلب جميع آيديهات المستخدمين المسجلين في البوت من الداتابيز
    all_users = await db.get_all_users_ids()
    
    success_count = 0
    failed_count = 0

    # تنظيف الحالة فوراً لمنع تداخل الحالات أثناء الإرسال
    await state.clear()

    # البدء في إرسال الرسالة للمستخدمين فرداً فرداً
    for user_id in all_users:
        # حماية: تخطي إرسال الرسالة للآدمن نفسه إذا أردت (أو تركه يستلمها للتأكد)
        try:
            # استخدام دالة copy_of لنسخ أي نوع رسالة (نص، صورة، ألبوم، إلخ) بنفس التنسيق والأزرار الأصلية
            await message.copy_to(chat_id=user_id)
            success_count += 1
            
            # حماية من حظر التليغرام (Rate Limit): نضع تأخير بسيط جداً بعد كل مجموعة رسائل
            if success_count % 30 == 0:
                await asyncio.sleep(1)
                
        except Exception:
            # في حال قام المستخدم بحظر البوت (Blocked) أو الحساب محذوف
            failed_count += 1

    # تحديث رسالة الحالة للآدمن بعد اكتمال الإذاعة بنجاح
    await status_msg.edit_text(
        f"✅ <b>تم انتهاء الإذاعة بنجاح!</b>\n\n"
        f"🟢 استلمها بنجاح: <code>{success_count}</code> مستخدم.\n"
        f"🔴 فشل الإرسال إلى: <code>{failed_count}</code> مستخدم (قاموا بحظر البوت أو حساباتهم معطلة)."
    )






