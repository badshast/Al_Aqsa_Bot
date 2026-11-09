import os
import time
import requests
import google.generativeai as genai
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# 1. Configuration & Secure API Keys from Environment Variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel("gemini-1.5-flash")

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
PAGE_ID = "me"  # Current Facebook Page ID

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

GOOGLE_SHEET_WEBHOOK_URL = os.getenv(
    "GOOGLE_SHEET_WEBHOOK_URL",
    "https://script.googleusercontent.com/macros/echo?user_content_key=AUkAhnSGYPfqwVvHJObAJqSvGdJUAypVstMQ4pWUTnF9tlY_VUOeTHNTwPWEoFxAHbGOWY9wtmNrF-Wne7diHqfKD75dMzlQYmkDsoGcPd7xy4Nj58YWQQR-got41G6GewooI2T8fknAU__h90wf2K_sdSu-Sw-JKs085A7Xa9XfKFnZf3kcp_Lr_x8RM-rJJGDOtwcSW--sd4Bq69J73wKXTYXs56ehuD_0wFNMRCpP2eoHVCcwuK2-iSfTZ-3VmMGs-Nj4ORfSDlikN3x_hU5Rw7mdc3vAoQ&lib=M8Z7ms9C7gwd7yQ7wvKCVENyo-8z-9mm1"
)

def generate_ai_post(topic_type="admission"):
    """Generate engaging Facebook post or caption using Gemini AI"""
    if topic_type == "admission":
        prompt = (
            "আল আকসা কম্পিউটার (নতুন বাস টার্মিনাল, লামা-আলীকদম কাউন্টারের পাশে, ২য় তলা, পুরাতন কমার্স কলেজ, চকরিয়া, কক্সবাজার)-এর জন্য একটি আকর্ষণীয় ফেসবুক পোস্ট লেখো। "
            "এখানে কম্পিউটার অফিস অ্যাপ্লিকেশন, গ্রাফিক ডিজাইন, ফ্রিল্যান্সিং (২/৩ অংশ প্রফিট শেয়ারিং), ফরেক্স ট্রেডিং এবং ১৮-৪৫ বছর বয়সীদের জন্য ১০,০০০+ টাকা ভাতার সরকারি ফ্রি কোর্স চলছে। "
            "পোস্টের সাথে ইমোজি এবং নিচে যোগাযোগের নম্বর (01725259074, 01832465790) ও ঠিকানা স্পষ্টভাবে উল্লেখ করবে।"
        )
    else:
        prompt = (
            "আল আকসা কম্পিউটার, চকরিয়া-এর পেজের জন্য একটি সাপ্তাহিক প্রশ্নোত্তর ও মোটিভেশনাল পোস্ট লেখো, "
            "যেখানে স্টুডেন্টদের ক্যারিয়ার গাইডলাইন এবং আমাদের কোর্সের সুবিধাগুলো সংক্ষেপে সুন্দরভাবে তুলে ধরা হবে।"
        )
    
    try:
        response = ai_model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return "আল আকসা কম্পিউটারে নতুন ব্যাচে ভর্তি চলছে! আজই যোগাযোগ করুন: 01725259074।"

def publish_facebook_post(message_text):
    """Publish post automatically to Facebook Page"""
    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/feed"
    payload = {
        "message": message_text,
        "access_token": PAGE_ACCESS_TOKEN
    }
    try:
        res = requests.post(url, data=payload)
        return res.json()
    except Exception as e:
        print(f"FB Post Error: {e}")
        return None

def send_telegram_video_request():
    """Request lab video or success story from Admin via Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    msg = (
        "🎬 **অটো-রিলস ও সাকসেস স্টোরি রিকোয়েস্ট!**\n\n"
        "স্যার, আল আকসা কম্পিউটার পেজে আজকের রিলস বা সাকসেস স্টোরি আপলোড করার সময় হয়েছে।\n"
        "অনুগ্রহ করে কম্পিউটার ল্যাব বা ক্লাসের **৩-৪ সেকেন্ডের একটি ছোট ভিডিও ক্লিপ বা সফল শিক্ষার্থীর ছবি** এখানে সরাসরি সেন্ড করুন, আমি ক্যাপশন লিখে পেজে আপলোড করে দিচ্ছি!"
    )
    payload = {"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def job_scheduler_loop():
    """Background scheduler to check and send posts and Telegram requests"""
    print("--- Al Aqsa Social Media Scheduler & Video Requester Running ---")
    
    last_admission_post = time.time()
    last_video_request = time.time()
    
    while True:
        current_time = time.time()
        
        # 1. Auto Admission Post every 3 days (259200 seconds)
        if current_time - last_admission_post >= 259200:
            post_content = generate_ai_post("admission")
            publish_facebook_post(post_content)
            last_admission_post = current_time
            print("Auto Admission Post Published to Facebook Page!")

        # 2. Request video on Telegram every 4 days (345600 seconds)
        if current_time - last_video_request >= 345600:
            send_telegram_video_request()
            last_video_request = current_time
            print("Telegram Video Request Sent to Sir!")

        time.sleep(3600) # Check every 1 hour

if __name__ == "__main__":
    job_scheduler_loop()