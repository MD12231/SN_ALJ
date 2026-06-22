import database.db as db  # استيراد ملف قاعدة البيانات
from aiogram import Router, F, Bot
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, ReplyKeyboardRemove)
from keyboard.reply import deposit, withdraw, withdrawanddeposit

# تعريف الراوتر لمرة واحدة فقط لكل الملف
router = Router()

# آيدي القناة الخاصة بالإدارة (تأكد من تعديله للآيدي الحقيقي الخاص بك)
ADMIN_CHANNEL_ID = -1004499883886
DEBOSIT_ADMIN = -1004364930823

# تعريف حالات الشحن (FSM)
class DepositStates(StatesGroup):
    waiting_for_tx_number = State()
    waiting_for_amount = State()

class WithdrawStates(StatesGroup):
    waiting_for_tx_number = State()
    waiting_for_amount = State()

# ==================== أقسام المستخدم (User Handlers) ====================

# 1. عرض الرصيد
@router.message(F.text == "💰 رصيدي")
async def show_balance(message: Message):
    user_id = message.from_user.id
    user_data = await db.get_user(user_id)
    
    if user_data:
        balance = user_data['balance']
    else:
        balance = 0.00
        await db.add_user(tg_id=user_id, username=message.from_user.username)
       
    await message.answer(
        f"💳 رصيدك الحالي هو: {balance}", 
        reply_markup=withdrawanddeposit(),
        parse_mode="Markdown"
    )

# 2. بدء خطوة الشحن
@router.message(F.text == "شحن رصيد في البوت")
async def show_deposit_methods(message: Message):
    await message.answer("اختر طريقة الشحن:", reply_markup=deposit())
#---------------------------shamcach
# 🔁 دالة شحن شام كاش
# 🔁 شحن شام كاش
@router.message(F.text == "شحن رصيد عن طريق شام كاش")
async def deposit_sham_cash(message: Message, state: FSMContext):
    await state.update_data(method="شام كاش")
    
    instructions = (
        "🇸🇾 <b>الشحن عبر شام كاش:</b>\n\n"
        "📱 يرجى التحويل إلى الكود التالي: <code>920328c12c97b30bbde4d5af415d11b2</code>\n"
        "📝 بعد إتمام التحويل بنجاح، أرسل لي <b>رقم العملية أو كود التحويل</b> هنا:"
    )
    # نقوم بإرسال رسالة عادية لإخفاء الكيبورد حتى يكتب المستخدم براحته
    await message.answer(instructions, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DepositStates.waiting_for_tx_number)


# 🔁 شحن USDT TRC20
@router.message(F.text == "شحن رصيد عن طريق usdt trc20")
async def deposit_usdt_trc20(message: Message, state: FSMContext):
    await state.update_data(method="USDT TRC20")
    
    instructions = (
        "🪙 <b>الشحن عبر USDT (TRC-20):</b>\n\n"
        "💳 عنوان المحفظة:\n<code>TTieavhJZVUU8njifsQooMJYABgCnxACSX</code>\n\n"
        "⚠️ تأكد من اختيار شبكة <b>TRC20</b> لتفادي ضياع الأموال.\n"
        "📝 بعد التحويل، أرسل هنا <b>رقم العملية (TxID)</b>:"
    )
    await message.answer(instructions, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DepositStates.waiting_for_tx_number)


# 🔁 شحن USDT BEP20
@router.message(F.text == "شحن رصيد عن طريق usdt pep20")
async def deposit_usdt_bep20(message: Message, state: FSMContext):
    await state.update_data(method="USDT BEP20")
    
    instructions = (
        "🪙 <b>الشحن عبر USDT (BEP-20 / BNB Smart Chain):</b>\n\n"
        "💳 عنوان المحفظة:\n<code>0x76b345dE0251628532Ae31040E37F7c513306736</code>\n\n"
        "⚠️ تأكد من اختيار شبكة <b>BEP20</b> لتفادي ضياع الأموال.\n"
        "📝 بعد التحويل، أرسل هنا <b>رقم العملية (TxID)</b>:"
    )
    await message.answer(instructions, parse_mode="HTML", reply_markup=ReplyKeyboardRemove())
    await state.set_state(DepositStates.waiting_for_tx_number)



# 4. استقبال رقم العملية
@router.message(DepositStates.waiting_for_tx_number)
async def process_tx_number(message: Message, state: FSMContext):
    await state.update_data(tx_number=message.text.strip())
    await message.answer("💰 الآن، يرجى إرسال المبلغ المراد شحنه (أرقام فقط):")
    await state.set_state(DepositStates.waiting_for_amount)

# 5. استقبال المبلغ وإرسال الطلب لقناة الإدارة
# 5. استقبال المبلغ وإرسال الطلب لقناة الإدارة
@router.message(DepositStates.waiting_for_amount)
async def process_deposit_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ يجب أن يكون المبلغ أكبر من الصفر!\nأعد إدخال المبلغ:")
            return
    except ValueError:
        await message.answer("⚠️ عذراً، يجب إرسال المبلغ كأرقام فقط!\nأعد إدخال المبلغ:")
        return

    user_data = await state.get_data()
    
    # ✅ تم تصحيح الأقواس هنا من [ ] إلى ( ) لإنهاء مشكلة توقف البوت
    method = user_data.get('method', 'غير محدد')
    tx_number = user_data.get('tx_number', 'غير محدد')
    
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ قبول", callback_data=f"dep_confirm:{user_id}:{amount}"),
            InlineKeyboardButton(text="❌ رفض", callback_data=f"dep_cancel:{user_id}")
        ]
    ])
    
    # تم إزالة النجوم (*) من حول {method} لأنك تستخدم parse_mode="HTML" والنجوم تخص الماركداون وقد تسبب مشاكل
    admin_msg = (
        f"📥 <b>طلب شحن رصيد جديد مالي</b>\n\n"
        f"👤 <b>المستخدم:</b> {message.from_user.full_name} ({username})\n"
        f"🆔 <b>آيدي المستخدم:</b> {user_id}\n"
        f"💳 <b>طريقة الشحن:</b> {method}\n"
        f"🔢 <b>رقم العملية:</b> <code>{tx_number}</code>\n"
        f"💵 <b>المبلغ المطلوب:</b> {amount}\n\n"
        f"الرجاء مراجعة العملية والضغط على الإجراء المناسب:"
    )
    
    try:
        # تأكد أن ADMIN_CHANNEL_ID معرف في الأعلى بشكل صحيح كـ رقم int (مثال: 1234567890-)
        await bot.send_message(
            chat_id=DEBOSIT_ADMIN, 
            text=admin_msg, 
            reply_markup=inline_kb, 
            parse_mode="HTML"  
        )
        
        # إذا نجح الإرسال، يتم إشعار المستخدم وإغلاق الحالة
        await message.answer("✅ تم إرسال طلب الشحن الخاص بك إلى الإدارة.\nسيتم فحص العملية وتحديث رصيدك فور الموافقة عليها! ⏳")
        await state.clear()
        
    except Exception as e:
        print(f"🚨 خطأ قاتل في دالة process_deposit_amount أثناء الإرسال: {e}")
        await message.answer("❌ عذراً، حدث خطأ داخلي أثناء إرسال طلبك إلى قناة الإدارة.\nيرجى التواصل مع الدعم الفني لحل المشكلة.")

# ==================== أقسام التحكم بالقناة (Admin Callbacks) ====================
# معالجة قبول الشحن وتحديث الداتابيز وتوزيع عمولة الـ 5%
@router.callback_query(F.data.startswith("dep_confirm:"))
async def approve_deposit(callback: CallbackQuery, bot: Bot):
    # إلغاء تعليق وتدوير الزر فوراً في التلغرام 🚨
    await callback.answer()
    
    data_parts = callback.data.split(":")
    user_id = int(data_parts[1])
    amount = float(data_parts[2])
    
    try:
        # معالجة الشحن في قاعدة البيانات
        result = await db.process_approved_deposit(user_id=user_id, amount=amount)
    except Exception as e:
        await callback.message.reply(f"❌ حدث خطأ داخلي في قاعدة البيانات أثناء معالجة الطلب:\n{str(e)}", parse_mode="Markdown")
        return
    
    # تحديث نص رسالة الإدارة
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"🟢 تم قبول العملية بنجاح بواسطة: @{callback.from_user.username}"
    )
    
    # إشعار المستخدم المشحون له
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 تمت الموافقة على طلب الشحن الخاص بك!\n💰 تم إضافة {amount} إلى رصيدك بنجاح."
        )
    except Exception:
        pass
        
    # إشعار الداعي (العمولة) في حال كان هناك نظام إحالة صالح
    if result and result.get("bonus_sent") and result.get("inviter_id"):
        try:
            await bot.send_message(
                chat_id=int(result["inviter_id"]),
                text=f"🎁 مكافأة إحالة جديدة!\n"
                     f"بما أن صديقك قام بشحن رصيده، حصلت تلقائياً على عمولة 5% بقيمة {result['bonus_amount']}$ تم إضافتها لحسابك."
            )
        except Exception:
            pass

# معالجة رفض طلب الشحن
@router.callback_query(F.data.startswith("dep_cancel:"))
async def reject_deposit(callback: CallbackQuery, bot: Bot):
    data_parts = callback.data.split(":")
    user_id = int(data_parts[1])
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"🔴 تم رفض هذه العملية بواسطة: @{callback.from_user.username}"
    )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ عذراً، تم رفض طلب شحن الرصيد الخاص بك من قبل الإدارة.\nيرجى التأكد من بيانات التحويل ورقم السند والمحاولة مجدداً أو مراسلة الدعم."
        )
    except Exception:
        pass

    await callback.answer("❌ تم رفض الطلب بنجاح.")














# 2. بدء خطوة السحب
@router.message(F.text == "سحب رصيد من البوت")
async def show_withdraw_methods(message: Message):
    # تأكد من استيراد دالة withdraw() التي تعرض لوحة مفاتيح طرق السحب
    await message.answer("اختر طريقة السحب:", reply_markup=withdraw())


# 3. اختيار الطريقة وافتتاح حالة الـ FSM
@router.message(F.text.startswith("سحب رصيد عن طريق"))
async def choose_method(message: Message, state: FSMContext):
    method = message.text.replace("سحب رصيد عن طريق ", "").strip()
    await state.update_data(method=method)
    
    await message.answer(f"⚙️ لقد اخترت السحب عبر: {method}\n\n📝 الرجاء إرسال كود أو عنوان الاستقبال (مثلاً: رقم المحفظة):")
    await state.set_state(WithdrawStates.waiting_for_tx_number)


# 4. استقبال رقم أو عنوان العملية
@router.message(WithdrawStates.waiting_for_tx_number)
async def process_tx_number(message: Message, state: FSMContext):
    await state.update_data(tx_number=message.text.strip())
    await message.answer("💰 الآن، يرجى إرسال المبلغ المراد سحبه (أرقام فقط):")
    await state.set_state(WithdrawStates.waiting_for_amount)


# 5. استقبال المبلغ، التحقق منه، حجزه، وإرسال الطلب للإدارة
@router.message(WithdrawStates.waiting_for_amount)
async def process_withdraw_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            raise ValueError
    except ValueError:
        await message.answer("⚠️ عذراً، يجب إرسال مبلغ صالح (أرقام أكبر من الصفر فقط)!\nأعد إدخال المبلغ:")
        return

    user_id = message.from_user.id

    # 🛑 خطوة حجز المبلغ وفحص الرصيد في قاعدة البيانات
    # يجب أن تصمم دالة تمنع السحب إذا كان الرصيد غير كافٍ وتقوم بخصم/حجز الرصيد مؤقتاً
    has_balance = await db.check_and_hold_balance(user_id=user_id, amount=amount)
    
    if not has_balance:
        await message.answer("❌ رصيدك الحالي غير كافٍ لإتمام عملية السحب!")
        await state.clear()  # إنهاء الحالة لأن الرصيد لا يكفي
        return

    user_data = await state.get_data()
    method = user_data['method']
    tx_number = user_data['tx_number']
    
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    
    # تعديل الـ callback_data لتبدأ بـ with_ بدلاً من dep_ لتمييزها عن الشحن
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ قبول وسحب", callback_data=f"with_confirm:{user_id}:{amount}"),
            InlineKeyboardButton(text="❌ رفض وإرجاع", callback_data=f"with_cancel:{user_id}:{amount}")
        ]
    ])
    
    # تعديل النصوص لتناسب "السحب" بدلاً من "الشحن"
    admin_msg = (
        f"📤 طلب سحب رصيد جديد\n\n"
        f"👤 المستخدم: {message.from_user.full_name} ({username})\n"
        f"🆔 آيدي المستخدم: {user_id}\n"
        f"💳 طريقة السحب: *{method}*\n"
        f"🔢 عنوان/كود الاستقبال: {tx_number}\n"
        f"💵 المبلغ المطلوب: {amount}\n\n"
        f"🚨 تم حجز المبلغ مؤقتاً من حساب المستخدم.\n"
        f"الرجاء مراجعة العملية والضغط على الإجراء المناسب بعد التحويل للمستخدم:"
    )
    
    await bot.send_message(chat_id=ADMIN_CHANNEL_ID, text=admin_msg, reply_markup=inline_kb, parse_mode="Markdown")
    await message.answer("✅ تم تقديم طلب السحب بنجاح وحجز المبلغ من رصيدك.\nجاري مراجعة الطلب من قبل الإدارة وسيتم إشعارك فور تحويل المبلغ! ⏳")
    await state.clear()


# ==================== أقسام التحكم بالقناة (Admin Callbacks) ====================

# معالجة قبول السحب (تأكيد الخصم النهائي)
@router.callback_query(F.data.startswith("with_confirm:"))
async def approve_withdraw(callback: CallbackQuery, bot: Bot):
    data_parts = callback.data.split(":")
    user_id = int(data_parts[1])
    amount = float(data_parts[2])
    
    # دالة لتأكيد الخصم النهائي في قاعدة البيانات (وتحويل الحالة من محجوز إلى مخصوم)
    await db.confirm_withdraw(user_id=user_id, amount=amount)
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"🟢 تم قبول طلب السحب وتحويل المبلغ بواسطة: @{callback.from_user.username}"
    )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"🎉 تمت الموافقة على طلب السحب الخاص بك!\n💵 تم تحويل مبلغ {amount} إلى حسابك بنجاح. شكراً لك!"
        )
    except Exception:
        pass

    await callback.answer("✅ تم تأكيد السحب بنجاح.")


# معالجة رفض طلب السحب (إلغاء الحجز وإعادة المبلغ لرصيد المستخدم)
@router.callback_query(F.data.startswith("with_cancel:"))
async def reject_withdraw(callback: CallbackQuery, bot: Bot):
    data_parts = callback.data.split(":")
    user_id = int(data_parts[1])
    amount = float(data_parts[2]) # استلام المبلغ لإعادته للحساب
    
    # دالة لإلغاء الحجز وإعادة المبلغ لرصيد المستخدم في قاعدة البيانات
    await db.cancel_withdraw_and_refund(user_id=user_id, amount=amount)
    
    await callback.message.edit_text(
        f"{callback.message.text}\n\n"
        f"🔴 تم رفض هذا الطلب وإعادة المبلغ للمستخدم بواسطة: @{callback.from_user.username}"
    )
    
    try:
        await bot.send_message(
            chat_id=user_id,
            text=f"❌ عذراً، تم رفض طلب سحب الرصيد الخاص بك بقيمة {amount}$ من قبل الإدارة.\n"
                 f"💰 تم إعادة المبلغ بالكامل إلى رصيدك في البوت.\n"
                 f"يرجى التأكد من بيانات الاستقبال والمحاولة مجدداً أو مراسلة الدعم."
        )
    except Exception:
        pass

    await callback.answer("❌ تم رفض الطلب وإعادة الرصيد للمستخدم.")

