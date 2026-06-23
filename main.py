import asyncio
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, BotCommandScopeDefault
# استيراد الراوتر من ملف المعالجات
from handlers import user
from handlers import admin
from database.db import init_pool, init_db
from logger import logging
from aiogram.fsm.storage.memory import MemoryStorage

# ضع التوكن الخاص ببوتك هنا
BOT_TOKEN = "8779813513:AAGMiBb3wxRuRp3lCG8_esl0OluHbl4Kt38"

async def setup_bot_commands(bot: Bot):
    commands = [
        BotCommand(command="start", description="تشغيل البوت"),
        BotCommand(command="cancel", description="❌ إلغاء العملية الحالية والعودة")
    ]
    # تعيين الأوامر لجميع المستخدمين بشكل افتراضي
    await bot.set_my_commands(commands=commands, scope=BotCommandScopeDefault())
    print("✅ تم تعيين قائمة الأوامر (Menu) بنجاح.")

async def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    print("جاري الاتصال بقاعدة البيانات...")
    try:
        # 3. أول خطوة: إنشاء حوض الاتصالات (Pool)
        await init_pool()
        print("✅ تم إنشاء حوض الاتصالات (Pool) بنجاح.")

        # 4. ثاني خطوة: إنشاء وفحص الجداول الاعتمادية
        await init_db()
        print("✅ تم التحقق من الجداول وإصلاحها بنجاح.")
        
        

    except Exception as db_err:
        print(f"❌ فشل إقلاع قاعدة البيانات: {db_err}")
        return

    # تضمين الراوتر الخاص بالمعالجات في الديسپاتشر الرئيسي
    dp.include_router(user.router)
    dp.include_router(admin.router)

    print("🤖 البوت يعمل الآن بنجاح (مقسم إلى ملفات)...")


    await setup_bot_commands(bot)
    
    # بدء استقبال التحديثات وحذف التحديثات المعلقة القديمة
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
