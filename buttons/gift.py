from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import database.db as db

router = Router()

# تعريف حالة انتظار كود الهدية
class GiftCodeStates(StatesGroup):
    waiting_for_code = State()

# 1. عند الضغط على الزر: نطلب الكود ونفتح حالة الانتظار
@router.message(F.text == "🎁 كود هدية")
async def gift_code_request(message: Message, state: FSMContext):
    await message.answer("🎁 يرجى إرسال كود الهدية الخاص بك الآن لتفعيل المكافأة:")
    await state.set_state(GiftCodeStates.waiting_for_code)

# 2. استقبال الكود من المستخدم وفحصه (يعمل فقط عندما يكون المستخدم في حالة الانتظار)
@router.message(GiftCodeStates.waiting_for_code)
async def process_gift_code(message: Message, state: FSMContext):
    user_code = message.text.strip()
    user_id = message.from_user.id
    
    # استدعاء دالة الفحص من الداتابيز
    result = await db.check_and_redeem_code(code=user_code, tg_id=user_id)
    
    if result["status"] == "success":
        await message.answer(
            f"🎉 مبروك! تم تفعيل الكود بنجاح.\n"
            f"💰 تم إضافة {result['amount']}$ إلى رصيدك الحالي.",
            parse_mode="Markdown"
        )
    else:
        # إرسال رسالة الخطأ القادمة من قاعدة البيانات (غير موجود أو مستعمل)
        await message.answer(result["message"])
    
    # إنهاء الحالة لإرجاع المستخدم للوضع الطبيعي وتفعيل الأزرار العادية
    await state.clear()