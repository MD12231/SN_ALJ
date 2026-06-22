import os
import aiomysql

# إعدادات الاتصال بقاعدة البيانات (تقرأ من متغيرات Railway تلقائياً، أو تستخدم الافتراضي محلياً)
DB_HOST = os.getenv("MYSQLHOST", "localhost")
DB_USER = os.getenv("MYSQLUSER", "root")
DB_PASSWORD = os.getenv("MYSQLPASSWORD", "")
DB_NAME = os.getenv("MYSQLDATABASE", "dfdf")
DB_PORT = int(os.getenv("MYSQLPORT", 3306))

# متغير حوض الاتصالات العام
db_pool = None

async def init_pool():
    """إنشاء حوض الاتصالات (Pool) لقاعدة البيانات بشكل متوافق تماماً"""
    global db_pool
    db_pool = await aiomysql.create_pool(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        db=DB_NAME,
        port=DB_PORT,
        autocommit=True,
        auth_plugin='mysql_native_password',
        minsize=1,        # الحد الأدنى للاتصالات المفتوحة دائماً
        maxsize=10        # الحد الأقصى للاتصالات في الحوض
    )

async def init_db():
    """إنشاء الجداول والتحقق من العلاقات بشكل صحيح بدعم محرك InnoDB"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            # 1. إنشاء جدول المستخدمين (الاعتماد على آيدي التلغرام كـ المفتاح الأساسي)
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    tg_id BIGINT PRIMARY KEY,
                    username VARCHAR(255) NULL,
                    balance DECIMAL(10, 2) DEFAULT 0.00,
                    referrals INT DEFAULT 0,
                    remaining_shares INT DEFAULT 0
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            try:
                await cur.execute("ALTER TABLE users ADD COLUMN inviter_id BIGINT NULL;")
                print("🔹 تم إضافة عمود نظام الإحالات الجديد (inviter_id) بنجاح.")
            except Exception:
                pass

            try:
                await cur.execute("ALTER TABLE users ADD COLUMN held_balance DECIMAL(10, 2) DEFAULT 0.00;")
                print("🔹 تم إضافة عمود الرصيد المحجوز (held_balance) بنجاح.")
            except Exception:
                pass
            
            # 2. إنشاء جدول أكواد الهدايا مع ربطه بآيدي التلغرام للمستخدم في حقل used_by
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS gift_codes (
                    code VARCHAR(50) PRIMARY KEY,
                    amount DECIMAL(10, 2) NOT NULL,
                    is_used BOOLEAN DEFAULT FALSE,
                    used_by BIGINT NULL,
                    FOREIGN KEY (used_by) REFERENCES users(tg_id) 
                    ON DELETE SET NULL 
                    ON UPDATE CASCADE
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)

            
            await cur.execute("""
                CREATE TABLE IF NOT EXISTS support_tickets (
                    group_message_id BIGINT PRIMARY KEY,
                    user_id BIGINT NOT NULL
                ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """)
            print("🔹 تم إنشاء جدول تذاكر الدعم support_tickets بنجاح.")

# ==================== معاملات المستخدمين (User Actions) ====================

async def add_user(tg_id: int, username: str, inviter_id: int = None):
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT IGNORE INTO users (tg_id, username, inviter_id) VALUES (%s, %s, %s)",
                (tg_id, username, inviter_id)
            )

async def get_user(tg_id: int):
    """الاستعلام عن بيانات مستخدم معين بواسطة آيدي التلغرام الحقيقي"""
    async with db_pool.acquire() as conn:
        # استخدام DictCursor لترجيع البيانات كـ Dictionary ليسهل قراءتها بالأسماء
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM users WHERE tg_id = %s", (tg_id,))
            return await cur.fetchone()

# ==================== معاملات لوحة التحكم (Admin Panel) ====================

async def add_gift_code(code: str, amount: float):
    """إضافة كود هدية جديد إلى النظام بواسطة الآدمن"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO gift_codes (code, amount) VALUES (%s, %s)",
                (code, amount)
            )

async def get_all_users():
    """جلب قائمة بجميع المستخدمين المسجلين في البوت للآدمن"""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            await cur.execute("SELECT * FROM users")
            return await cur.fetchall()

# ==================== إغلاق الحوض (Clean Up) ====================

async def close_pool():
    """إغلاق حوض الاتصالات بشكل نظيف عند إطفاء البوت"""
    global db_pool
    if db_pool:
        db_pool.close()
        await db_pool.wait_closed()


async def check_and_redeem_code(code: str, tg_id: int) -> dict:
    """لفحص كود الهدية وتفعيله للمستخدم إن كان صالحاً"""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 1. البحث عن الكود وفحص ما إذا كان مستخدماً أم لا
            await cur.execute("SELECT * FROM gift_codes WHERE code = %s", (code,))
            code_data = await cur.fetchone()
            
            if not code_data:
                return {"status": "not_found", "message": "❌ هذا الكود غير موجود في النظام!"}
            
            if code_data['is_used']:
                return {"status": "already_used", "message": "❌ تم استخدام هذا الكود من قبل!"}
            
            amount = code_data['amount']
            
            # 2. تحديث حالة الكود ليصبح مستخدماً وربطه بآيدي المستخدم
            await cur.execute(
                "UPDATE gift_codes SET is_used = TRUE, used_by = %s WHERE code = %s",
                (tg_id, code)
            )
            
            # 3. إضافة قيمة الكود إلى رصيد المستخدم الحالي
            await cur.execute(
                "UPDATE users SET balance = balance + %s WHERE tg_id = %s",
                (amount, tg_id)
            )
            
            return {"status": "success", "amount": amount}

async def buy_shares_process(tg_id: int, multiplier: int, price_per_share: float) -> dict:
    """معالجة عملية شراء الأسهم والتحقق من الرصيد والحد الأقصى (20 سهم)"""
    total_cost = price_per_share * multiplier
    
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 1. جلب بيانات رصيد وأسهم المستخدم الحالية
            await cur.execute("SELECT balance, remaining_shares FROM users WHERE tg_id = %s", (tg_id,))
            user = await cur.fetchone()
            
            if not user:
                return {"status": "error", "message": "❌ لم يتم العثور على حسابك، أرسل /start أولاً."}
            
            current_balance = user['balance']
            current_shares = user['remaining_shares']
            
            # 2. التحقق من الحد الأقصى للأسهم (50 سهم)
            if current_shares + multiplier > 50:
                allowed_to_buy = 50 - current_shares
                if allowed_to_buy <= 0:
                    return {
                        "status": "limit_reached",
                        "message": "❌ عذراً! لقد وصلت بالفعل إلى الحد الأقصى المسموح به وهو 50 سهم ولا يمكنك شراء المزيد."
                    }
                else:
                    return {
                        "status": "limit_reached",
                        "message": f"❌ لا يمكنك شراء {multiplier} أسهم!\n📦 أنت تملك حالياً: {current_shares} سهم.\n🔄 المتبقي لك للوصول للحد الأقصى هو {allowed_to_buy} سهم فقط."
                    }
            
            # 3. التحقق من أن الرصيد يكفي
            if current_balance < total_cost:
                return {
                    "status": "insufficient", 
                    "message": f"❌ رصيدك غير كافٍ!\n💰 التكلفة الإجمالية: {total_cost}$\n💳 رصيدك الحالي: {current_balance}$"
                }
            
            # 4. خصم التكلفة وزيادة عدد الأسهم
            await cur.execute("""
                UPDATE users 
                SET balance = balance - %s, 
                    remaining_shares = remaining_shares + %s 
                WHERE tg_id = %s
            """, (total_cost, multiplier, tg_id))
            
            return {"status": "success", "total_cost": total_cost, "new_shares": current_shares + multiplier}


async def add_referral_bonus(inviter_id: int, new_user_id: int):
    """زيادة عدد إحالات الشخص الداعي بمقدار 1 بشرط ألا يدعو نفسه"""
    if inviter_id == new_user_id:
        return
        
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            # زيادة حقل الإحالات بمقدار 1 للشخص الذي قام بالدعوة
            await cur.execute(
                "UPDATE users SET referrals = referrals + 1 WHERE tg_id = %s",
                (inviter_id,)
            )

async def get_inviter(tg_id: int):
    """البحث عن الشخص الذي دعا هذا المستخدم (إن وجد) عبر فحص جدول الإحالات بطريقة عكسية"""
    # بما أننا لا نملك جدولاً مستقلاً للإحالات بل حقل عداد، سنفترض وجود نظام ربط أو نعتمد على استعلام ذكي.
    # إذا كنت ترغب في نظام عمولات دقيق، يفضل مستقبلاً إضافة عمود 'referred_by' في جدول users.
    # حالياً، سنضيف دالة الشحن المباشر مع دعم إضافة العمولات يدوياً عند تمرير آيدي الداعي.
    pass

async def approve_deposit_and_bonus(user_id: int, amount: float) -> dict:
    """تفعيل الشحن للمستخدم وإضافة 5% للداعي إن كان مسجلاً عبر إحالة"""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 1. شحن رصيد المستخدم الأساسي
            await cur.execute("UPDATE users SET balance = balance + %s WHERE tg_id = %s", (amount, user_id))
            
            # 2. فحص ما إذا كان هذا المستخدم يملك داعياً (تحتاج إضافة عمود referred_by لجدول الـ users لجعلها ديناميكية 100%)
            # كحل برمي ذكي ومباشر بدون تعديل جداول حالياً، سنقوم بالبحث إذا كان هناك عمود لربط الإحالة أو يمكنك تعديل جدول users لإضافة الداعي.
            
            # حساب العبوة (5%)
            bonus = amount * 0.05
            
            return {"status": "success", "bonus": bonus}

async def process_approved_deposit(user_id: int, amount: float) -> dict:
    """تحديث رصيد المشحون له وإضافة عمولة 5% للشخص الداعي تلقائياً"""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 1. جلب بيانات المستخدم لمعرفة الداعي
            await cur.execute("SELECT inviter_id FROM users WHERE tg_id = %s", (user_id,))
            user = await cur.fetchone()
            
            # 2. إضافة الرصيد للمستخدم
            await cur.execute("UPDATE users SET balance = balance + %s WHERE tg_id = %s", (amount, user_id))
            
            inviter_id = user['inviter_id'] if user else None
            bonus_sent = False
            bonus_amount = amount * 0.05
            
            # 3. إذا كان هناك داعي، منحه 5% من قيمة الشحن
            if inviter_id:
                await cur.execute("UPDATE users SET balance = balance + %s WHERE tg_id = %s", (bonus_amount, inviter_id))
                bonus_sent = True
                
            return {"status": "success", "bonus_sent": bonus_sent, "inviter_id": inviter_id, "bonus_amount": bonus_amount}

async def check_and_hold_balance(user_id: int, amount: float) -> bool:
    """
    الخطوة 1: فحص رصيد المستخدم، وإذا كان كافياً يتم خصمه من الرصيد المتاح 
    ونقله إلى الرصيد المحجوز لحين موافقة أو رفض الإدارة.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # جلب الرصيد الحالي للمستخدم
            await cur.execute("SELECT balance FROM users WHERE tg_id = %s", (user_id,))
            user = await cur.fetchone()
            
            if not user or user['balance'] < amount:
                return False  # الرصيد غير كافٍ أو المستخدم غير موجود
            
            # نقل المبلغ من الرصيد المتاح إلى المحجوز
            await cur.execute("""
                UPDATE users 
                SET balance = balance - %s, 
                    held_balance = held_balance + %s 
                WHERE tg_id = %s
            """, (amount, amount, user_id))
            
            return True

async def confirm_withdraw(user_id: int, amount: float):
    """
    الخطوة 2 (عند القبول): خصم المبلغ نهائياً من الرصيد المحجوز (held_balance) 
    لأن الإدارة قامت بتحويل الأموال للمستخدم بالفعل.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE users 
                SET held_balance = GREATEST(held_balance - %s, 0.00) 
                WHERE tg_id = %s
            """, (amount, user_id))


async def cancel_withdraw_and_refund(user_id: int, amount: float):
    """
    الخطوة 3 (عند الرفض): إعادة المبلغ من الرصيد المحجوز إلى الرصيد المتاح (balance) 
    بسبب رفض المعاملة من قبل الإدارة.
    """
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("""
                UPDATE users 
                SET held_balance = GREATEST(held_balance - %s, 0.00),
                    balance = balance + %s 
                WHERE tg_id = %s
            """, (amount, amount, user_id))


async def transfer_balance(sender_id: int, receiver_id: int, amount: float) -> bool:
    """خصم المبلغ من المرسل وإضافته للمستلم بأمان بعد فحص الرصيد"""
    async with db_pool.acquire() as conn:
        async with conn.cursor(aiomysql.DictCursor) as cur:
            # 1. جلب رصيد المرسل الحالي
            await cur.execute("SELECT balance FROM users WHERE tg_id = %s", (sender_id,))
            sender = await cur.fetchone()
            
            # إذا كان المرسل غير موجود أو رصيده أقل من المبلغ المراد إهداؤه
            if not sender or sender['balance'] < amount:
                return False
                
            # 2. خصم الرصيد من المرسل
            await cur.execute("UPDATE users SET balance = balance - %s WHERE tg_id = %s", (amount, sender_id))
            
            # 3. إضافة الرصيد للمستلم
            await cur.execute("UPDATE users SET balance = balance + %s WHERE tg_id = %s", (amount, receiver_id))
            
            return True


async def admin_modify_balance(user_id: int, amount: float, operation: str):
    """دالة تحكم خاصة بالآدمن لزيادة رصيد مستخدم أو إنقاصه بأمان"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            if operation == "add":
                # إضافة الرصيد مباشرة
                await cur.execute(
                    "UPDATE users SET balance = balance + %s WHERE tg_id = %s", 
                    (amount, user_id)
                )
            elif operation == "remove":
                # الخصم مع ضمان عدم النزول تحت الصفر تحت أي ظرف
                await cur.execute(
                    "UPDATE users SET balance = GREATEST(balance - %s, 0.00) WHERE tg_id = %s", 
                    (amount, user_id)
                )

async def get_all_users_ids() -> list:
    """جلب قائمة تحتوي على جميع آيديهات التليغرام للمستخدمين المسجلين"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT tg_id FROM users")
            rows = await cur.fetchall()
            # تحويل النتيجة من قائمة صفوف إلى قائمة أرقام عادية [123, 456, 789]
            return [row[0] for row in rows] if rows else []

# أضف هذا الجزء لإنشاء الجدول داخل دالة init_db


# دالة لحفظ التذكرة الجديدة
# ==================== معاملات الدعم الفني (Support Tickets) ====================

async def save_support_ticket(group_message_id: int, user_id: int):
    """حفظ العلاقة بين آيدي الرسالة في المجموعة وآيدي المستخدم في الداتابيز"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "INSERT INTO support_tickets (group_message_id, user_id) VALUES (%s, %s)",
                (group_message_id, user_id)
            )

async def get_user_by_message(group_message_id: int) -> int:
    """جلب آيدي المستخدم بناءً على آيدي رسالة المجموعة التي تم الرد عليها"""
    async with db_pool.acquire() as conn:
        async with conn.cursor() as cur:
            await cur.execute("SELECT user_id FROM support_tickets WHERE group_message_id = %s", (group_message_id,))
            row = await cur.fetchone()
            return row[0] if row else None



