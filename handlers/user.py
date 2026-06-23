from aiogram import Router, F, Bot, BaseMiddleware
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, TelegramObject
from aiogram.filters import CommandStart, CommandObject, Command
# استيراد الكيبورد من الملف الأول
from keyboard.reply import get_main_keyboard
from typing import Callable, Dict, Any, Awaitable
from aiogram.fsm.context import FSMContext
from buttons.balance import router as balance_router
from buttons.buyingashare import router as buyingashare_router
from buttons.gift import router as gift_router
from database.db import add_user, get_user, add_referral_bonus, transfer_balance, save_support_ticket, get_user_by_message
from subscribed import is_subscribed

router = Router()

ADMIN_CHANNEL_ID = -1004431587195

ADMIN_ID = [176782168]

from aiogram.fsm.state import StatesGroup, State

class GiftStates(StatesGroup):
    waiting_for_receiver_id = State()  # انتظار آيدي الشخص المستلم
    waiting_for_amount = State()       # انتظار المبلغ

from aiogram.fsm.state import StatesGroup, State


# حالات الآدمن عند الرد من القناة
class AdminReplyStates(StatesGroup):
    waiting_for_admin_reply = State()



class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        
        # 1. التأكد من أن الحدث يحتوي على مستخدم (تجنباً للأخطاء)
        if not event.from_user:
            return await handler(event, data)
            
        user_id = event.from_user.id
        bot = data['bot'] # الطريقة الصحيحة لجلب كائن البوت داخل الميدل وير
        
        # 2. استثناء الآدمن من الاشتراك الإجباري دائماً لكي لا ينقفل البوت عليك
        if user_id in ADMIN_ID:
            return await handler(event, data)

        # 3. الفحص من دالة الاشتراك
        if not await is_subscribed(user_id, bot):
            # بناء كيبورد شفاف بدلاً من رابط نصي جاف
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📢 اشترك في القناة هنا", url="https://t.me/SanabelAlJabalOfficial")],
            ])
            
            # التأكد أن الحدث عبارة عن رسالة ونصنع رد عليها
            if isinstance(event, Message):
                await event.answer(
                    "⚠️ <b>عذراً عزيزي، يجب عليك الاشتراك في قناة البوت أولاً لتتمكن من استخدامه!</b>",
                    reply_markup=markup,
                    parse_mode="HTML"
                )
            return # إيقاف التمرير (لن يتم تنفيذ أي كود بعده للمستخدم غير المشترك)
            
        # إذا كان مشتركاً، يتم تمرير الحدث للكود الطبيعي للبوت
        return await handler(event, data)

# ربط الميدل وير بالراوتر (أو بالديسباتشر dispatcher مباشرة ليطبق على كل البوت)
router.message.middleware(SubscriptionMiddleware())

router.include_router(balance_router)
router.include_router(buyingashare_router)
router.include_router(gift_router)

# معالج أمر البدء /start
@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):
    user_id = message.from_user.id
    username = message.from_user.username
    
    # 1. فحص هل المستخدم موجود مسبقاً
    existing_user = await get_user(user_id)
    
    inviter_id = None
    # 2. إذا كان مستخدم جديد تماماً ودخل عبر رابط إحالة
    if not existing_user and command.args:
        try:
            potential_inviter = int(command.args)
            if potential_inviter != user_id:  # التأكد أنه لا يدعو نفسه
                inviter_id = potential_inviter
        except ValueError:
            pass
            
    # 3. تسجيل المستخدم في النظام (مع تمرير الداعي إن وُجد)
    await add_user(tg_id=user_id, username=username, inviter_id=inviter_id)
    
    # 4. زيادة عداد إحالات الشخص الداعي إذا كان المستخدم جديداً بالفعل
    if not existing_user and inviter_id:
        await add_referral_bonus(inviter_id=inviter_id, new_user_id=user_id)
            
    await message.answer(
        f"أهلاً بك يا {message.from_user.full_name} في بوت المساهمة الاستثماري! 🚀\n"
        "تم تسجيل حسابك بنجاح.\n\n"
        "الرجاء اختيار أحد الخيارات من القائمة أدناه:",
        reply_markup=get_main_keyboard()
    )
# معالجة الضغط على الأزرار

@router.message(Command("cancel"))
async def cancel_handler(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:
        await message.answer("لا توجد عملية نشطة لإلغائها حالياً.")
        return

    await state.clear() # مسح الحالة الحالية وإلغاء انتظار المبلغ
    await message.answer("تم إلغاء العملية الحالية بنجاح والتراجع.")


@router.message(F.text == "👤 حسابي")
async def show_profile(message: Message):
    
    user_id = message.from_user.id
    
    # جلب بيانات المستخدم الفعلية من قاعدة البيانات
    user_data = await get_user(user_id)
    
    if user_data:
        user_info = (
            f"👤 تفاصيل حسابك الاستثماري:\n\n"
            f"🔹 الاسم: {message.from_user.full_name}\n"
            f"🔹 المعرف (ID): {user_data['tg_id']}\n"
            f"💰 الرصيد الحالي: {user_data['balance']}$\n"
            f"👥 عدد الإحالات: {user_data['referrals']}\n"
            f"📈 الأسهم المملوكة: {user_data['remaining_shares']} / 50 سهم\n\n"
            f"🔹 حالة الحساب: نشط ✅"
        )
    else:
        user_info = "❌ لم يتم العثور على بياناتك، يرجى إرسال /start لتفعيل الحساب."

    await message.answer(user_info, parse_mode="Markdown")


@router.message(F.text == "👥 الاحالات")
async def show_referrals(message: Message, bot: Bot):
    user_id = message.from_user.id
    
    # 1. جلب بيانات المستخدم لمعرفة عدد إحالاته الحالية
    user_data = await get_user(user_id)
    current_referrals = user_data['referrals'] if user_data else 0
    
    # 2. جلب يوزر نيم البوت تلقائياً لإنشاء الرابط
    bot_username = (await bot.get_me()).username
    referral_link = f"https://t.me/{bot_username}?start={user_id}"
    
    # 3. صياغة الرسالة وعرض إجمالي الإحالات
    response = (
        f"👥 نظام الإحالات والمكافآت:\n\n"
        f"📊 إحصائياتك الحالية:\n"
        f"🔹 عدد الأشخاص الذين دعوتهم: {current_referrals} عضو\n\n"
        f"🔗 شارك رابط الإحالة الخاص بك مع أصدقائك أو في المجموعات للحصول على عمولة:\n"
        f"{referral_link}"
    )
    
    await message.answer(response)

@router.message(F.text == "💬 غروب المساهمين")
async def shareholders_group(message: Message, bot: Bot):
    user_id = message.from_user.id
    SHAREHOLDERS_GROUP_ID = -1003714323428  # آيدي مجموعتك الفعلي
    
    try:
        # 1. جلب بيانات المستخدم من قاعدة البيانات
        user_data = await get_user(user_id)
        
        # 2. التحقق من امتلاكه للأسهم
        if user_data and user_data['remaining_shares'] > 0:
            
            # 🛑 [الحماية] فحص هل المستخدم عضو الحالي في المجموعة؟
            try:
                member_check = await bot.get_chat_member(chat_id=SHAREHOLDERS_GROUP_ID, user_id=user_id)
                
                # إذا كانت حالته (عضو، مشرف، أو مالك) فهذا يعني أنه داخل المجموعة حالياً
                if member_check.status in ['member', 'administrator', 'creator']:
                    await message.answer(
                        "ℹ️ <b>أنت منضم بالفعل إلى مجموعة المساهمين!</b>\n\n"
                        "لا يمكن توليد روابط إضافية طالما أنك متواجد داخل المجموعة منعاً للتسريب.",
                        parse_mode="HTML"
                    )
                    return # إيقاف التنفيذ وعدم توليد رابط جديد
            except Exception:
                # إذا حدث خطأ (مثلاً العضو ليس في المجموعة أو غادرها)، سيكمل الكود لتوليد الرابط بأمان
                pass

            # 3. إنشاء رابط دعوة مؤقت (لأنه ليس داخل المجموعة حالياً)
            invite_link = await bot.create_chat_invite_link(
                chat_id=SHAREHOLDERS_GROUP_ID,
                member_limit=1,
                name=f"رابط مساهمة محمي لـ {user_id}"
            )
            
            markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔗 اضغط هنا للانضمام للمجموعة", url=invite_link.invite_link)]
            ])
            
            await message.answer(
                f"🎉 <b>أهلاً بك عزيزي المساهم!</b>\n\n"
                f"بما أنك تمتلك <b>{user_data['remaining_shares']} سهم</b>، إليك رابط الانضمام للمجموعة.\n\n"
                f"⚠️ <i>ملاحظة: الرابط يعمل لمرة واحدة فقط وسيتم قفل التوليد بمجرد دخولك!</i>",
                reply_markup=markup,
                parse_mode="HTML"
            )
            
        else:
            await message.answer(
                "❌ <b>عذراً عزيزي!</b>\n\n"
                "هذه المجموعة مخصصة <u>للمساهمين فقط</u> الذين يملكون أسهماً مستثمرة في البوت.",
                parse_mode="HTML"
            )
            
    except Exception as e:
        print(f"🚨 خطأ في نظام التحقق والروابط: {e}")
        await message.answer("❌ عذراً، حدث خطأ داخلي. يرجى المحاولة لاحقاً.")


@router.message(F.text == "🌐 التواصل الاجتماعي")
async def social_media(message: Message):
    await message.answer(
        "🌐 تابعنا على منصات التواصل الاجتماعي لمعرفة آخر التحديثات والأخبار.\n"
        "https://www.facebook.com/share/18hEhrMVxE/"
        )


@router.message(F.text == "ℹ️ من نحن")
async def about_us(message: Message):
    await message.answer(
        "ℹ️ من نحن:\n\n"
        "سنابل الجبل: مبادرة تنموية تجمع طاقات شباب وشابات السويداء في الداخل والاغتراب.\n" 
        "نعمل بقلبٍ واحد على تطوير مشاريع زراعية وصناعية مستدامة،\n" 
        "لنبني جسراً بين عراقة الأرض وطموحات المستقبل، ونقدم أثراً ملموساً يخدم أهلنا ويؤسس لغدٍ أفضل",
        parse_mode="Markdown"
    )

@router.message(F.text == "القائمة الرئيسية")
async def menu(message: Message):
    await message.answer(
        "القائمة الرئيسية",
        reply_markup=get_main_keyboard()
    )




# 1. عند الضغط على زر "إهداء رصيد"
@router.message(F.text == "إهداء رصيد")
async def start_gift_process(message: Message, state: FSMContext):
    await message.answer("🎁 <b>نظام إهداء الرصيد:</b>\n\nيرجى إرسال <b>الآيدي (ID)</b> الخاص بالمستفيد الذي تود إهداء الرصيد له:")
    await state.set_state(GiftStates.waiting_for_receiver_id)


# 2. استقبال آيدي المستفيد والتحقق منه
@router.message(GiftStates.waiting_for_receiver_id)
async def process_receiver_id(message: Message, state: FSMContext):
    text = message.text.strip()
    
    # التحقق من أن المدخلات عبارة عن آيدي رقمي
    if not text.isdigit():
        await message.answer("⚠️ عذراً، يجب إرسال الآيدي كأرقام فقط!\nأعد إرسال الآيدي الصحيح:")
        await state.clear()
        return
        
    receiver_id = int(text)
    user_id = message.from_user.id
    
    # حماية: منع المستخدم من إهداء نفسه 🛑
    if receiver_id == user_id:
        await message.answer("❌ لا يمكنك إهداء رصيد لنفسك!\nيرجى إدخال آيدي مستخدم آخر:")
        await state.clear()
        return
        
    # التحقق من وجود المستخدم المستلم في قاعدة البيانات
    receiver_exists = await get_user(receiver_id) # تأكد أن دالة get_user موجودة في db
    if not receiver_exists:
        await message.answer("❌ هذا الآيدي غير مسجل في البوت مسبقاً!\nتأكد من الآيدي وأعد إرساله، أو اطلب من صديقك الدخول للبوت أولاً:")
        await state.clear()
        return

    # حفظ آيدي المستلم والانتقال لطلب المبلغ
    await state.update_data(receiver_id=receiver_id)
    await message.answer("💰 الآن، يرجى إرسال المبلغ المراد إهداؤه (أرقام فقط بالدولار $):")
    await state.set_state(GiftStates.waiting_for_amount)


# 3. استقبال المبلغ وتنفيذ التحويل الفوري في الداتابيز 💳
@router.message(GiftStates.waiting_for_amount)
async def process_gift_amount(message: Message, state: FSMContext, bot: Bot):
    try:
        amount = float(message.text.strip())
        if amount <= 0:
            await message.answer("⚠️ يجب أن يكون المبلغ أكبر من الصفر!\nأعد إدخال المبلغ:")
            return
    except ValueError:
        await message.answer("⚠️ عذراً، يجب إرسال المبلغ كأرقام فقط!\nأعد إدخال المبلغ:")
        return

    user_data = await state.get_data()
    receiver_id = user_data.get('receiver_id')
    sender_id = message.from_user.id
    
    # تنفيذ العملية داخل قاعدة البيانات (فحص رصيد المرسل، خصم منه، إضافة للمستلم)
    success = await transfer_balance(sender_id=sender_id, receiver_id=receiver_id, amount=amount)
    
    if not success:
        await message.answer("❌ رصيدك الحالي غير كافٍ لإتمام عملية الإهداء!")
        await state.clear()
        return

    # إرسال رسالة نجاح للمرسل
    await message.answer(f"✅ تم إهداء {amount}$ بنجاح إلى المستخدم ذو الآيدي: <code>{receiver_id}</code>")
    
    # إرسال إشعار فوري للمستلم يخبره بهديته وبدء حسابه الجديد 🎉
    try:
        sender_name = message.from_user.full_name
        await bot.send_message(
            chat_id=receiver_id,
            text=f"🎁 <b>وصلتك هدية رصيد جديدة!</b>\n\n"
                 f"👤 قام المستخدم: <b>{sender_name}</b> بإهداء رصيد إليك.\n"
                 f"💰 تم إضافة <b>{amount}</b> إلى حسابك بنجاح تلقائياً! 🎉",
            parse_mode="HTML"
        )
    except Exception as e:
        print(f"⚠️ تعذر إرسال إشعار للمستلم (ربما حظر البوت): {e}")

    # إنهاء الحالة وتنظيف الذاكرة
    await state.clear()



class SupportStates(StatesGroup):
    waiting_for_user_msg = State()

# 🚨 تم تعيين آيدي مجموعتك الحقيقي هنا بنجاح
ADMIN_GROUP_ID = -1004434892044

# 1. عند ضغط المستخدم على زر الدعم
@router.message(F.text == "🛠️ الدعم")
async def support_start(message: Message, state: FSMContext):
    await state.clear() # مسح أي حالة معلقة منعاً للتداخل
    await message.answer("🙋‍♂️ <b>قسم الدعم الفني:</b>\n\nاكتب رسالتك أو استفسارك الآن بالتفصيل في رسالة واحدة، وسيتم تحويلها مباشرة للمسؤولين:")
    await state.set_state(SupportStates.waiting_for_user_msg)


# 2. استقبال رسالة المستخدم وإرسالها للمجموعة وحفظ البيانات في الجدول
@router.message(SupportStates.waiting_for_user_msg)
async def support_process_msg(message: Message, state: FSMContext, bot: Bot):
    user_id = message.from_user.id
    username = f"@{message.from_user.username}" if message.from_user.username else "لا يوجد"
    
    support_msg = (
        f"📩 <b>رسالة دعم فني جديدة</b>\n\n"
        f"👤 <b>المرسل:</b> {message.from_user.full_name} ({username})\n"
        f"🆔 <b>الآيدي:</b> <code>{user_id}</code>\n\n"
        f"📝 <b>نص الرسالة:</b>\n{message.text}\n\n"
        f"<i>(للرد على هذا المستخدم، قم بعمل Reply مباشر على هذه الرسالة واكتب ردك)</i>"
    )
    
    try:
        # إرسال الرسالة للمجموعة والتقاط الرسالة لمعرفة آيديها في المجموعة
        sent_msg = await bot.send_message(chat_id=ADMIN_GROUP_ID, text=support_msg, parse_mode="HTML")
        
        # حفظ البيانات في جدول الـ support_tickets بالداتابيز لربط الرسالة بالمستخدم
        await save_support_ticket(group_message_id=sent_msg.message_id, user_id=user_id)
        
        await message.answer("✅ تم إرسال رسالتك إلى الدعم الفني بنجاح.\nسيأتيك الرد هنا فوراً بمجرد مراجعتها! ⏳")
        await state.clear()
        
    except Exception as e:
        print(f"🚨 خطأ أثناء إرسال الرسالة للمجموعة: {e}")
        await message.answer("❌ عذراً، حدث خطأ داخلي أثناء إرسال رسالتك.")


# 3. مراقبة الردود (Reply) بالإزاحة لليسار داخل مجموعة الإدارة ونقلها للمستخدم تلقائياً 🚀
@router.message(F.chat.id == ADMIN_GROUP_ID, F.reply_to_message)
async def admin_reply_handler(message: Message, bot: Bot):
    # جلب آيدي الرسالة الأصلية التي قام الآدمن بعمل Reply عليها
    replied_msg_id = message.reply_to_message.message_id
    
    # البحث في قاعدة البيانات لمعرفة آيدي المستخدم المرتبط بهذه الرسالة
    try:
        target_user_id = await get_user_by_message(replied_msg_id)
    except Exception as e:
        print(f"🚨 خطأ أثناء جلب بيانات التذكرة من الداتابيز: {e}")
        return
    
    # إذا لم يجد المستخدم، فهذا يعني أن الآدمن يعمل Reply على رسالة عادية في المجموعة وليست تذكرة دعم
    if not target_user_id:
        return

    try:
        # إرسال ترويسة تنبيهية للمخدم أولاً على الخاص
        await bot.send_message(
            chat_id=target_user_id, 
            text="🔔 <b>وصلك رد جديد من الدعم الفني:</b>", 
            parse_mode="HTML"
        )
        
        # نسخ رد الآدمن بالكامل وإرساله للمرسل (يدعم نصوص، صور، بصمات، ملصقات)
        await message.copy_to(chat_id=target_user_id)
        
        # وضع تفاعل علامة (✅) على رسالة الآدمن في المجموعة لتأكيد نجاح الإرسال الفوري للآدمن
        try:
            await message.react([{"type": "emoji", "emoji": "✅"}])
        except Exception:
            pass
            
    except Exception as e:
        print(f"🚨 فشل تحويل الرد للمستخدم: {e}")
        await message.reply("❌ لم يتمكن البوت من إرسال الرد للمستخدم، قد يكون قام بحظر البوت أو أن حساب التليغرام معطل.")



