import os
import requests
import time
from groq import Groq
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId

load_dotenv()

# 1. Configure Groq AI
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
else:
    groq_client = None

MONGO_URI = os.getenv("MONGO_URI")
POST_ACCESS_TOKEN = os.getenv("POST_ACCESS_TOKEN") 
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")
PAGE_ID = "me"

if MONGO_URI:
    mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
    db = mongo_client.get_database("alaqsa_db")
    pending_posts_col = db.get_collection("pending_posts")
else:
    pending_posts_col = None

def generate_post_for_approval():
    """Groq AI দিয়ে পোস্ট তৈরি করে টেলিগ্রামে পাঠাবে"""
    print(">>> POST GENERATION STARTED (GROQ) <<<")
    if not groq_client or pending_posts_col is None:
        send_telegram_message("❌ Groq বা MongoDB কানেক্টেড নেই।")
        return

    try:
        prompt = """তুমি আল আকসা কম্পিউটার (চকরিয়া, কক্সবাজার)-এর একজন প্রফেশনাল কন্টেন্ট রাইটার। 
        ফেসবুক পেজের জন্য একটি অত্যন্ত আকর্ষণীয় এবং প্রফেশনাল পোস্ট লিখো। 
        পোস্টের বিষয়বস্তু: কম্পিউটার অফিস অ্যাপ্লিকেশন, গ্রাফিক ডিজাইন বা ফ্রিল্যান্সিং কোর্সের যেকোনো একটি।
        পোস্টে অবশ্যই থাকতে হবে:
        ১. একটি আকর্ষণীয় হুক (প্রথম লাইন)।
        ২. কোর্সের সুবিধা (বুলেট পয়েন্টে)।
        ৩. একটি শক্তিশালী Call to Action (যেমন: আজই ভর্তি হোন, সিট সীমিত)।
        ৪. ৫টি রিলেভেন্ট হ্যাশট্যাগ। 
        ভাষা হবে একদম সাবলীল, উৎসাহব্যঞ্জক এবং প্রফেশনাল বাংলা।"""
        
        print(">>> CALLING GROQ API <<<")
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b", # Groq-এর সচল মডেল
            temperature=0.7,
            max_tokens=1024
        )
        
        post_text = response.choices[0].message.content.strip()
        print(f">>> GROQ REPLIED: {post_text[:50]}... <<<")
        
        result = pending_posts_col.insert_one({"text": post_text, "status": "pending", "timestamp": time.time()})
        post_id = str(result.inserted_id)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        
        # মার্কডাউন ছাড়া পাঠানো হচ্ছে যাতে AI-এর লেখা টেলিগ্রামে ব্লক না হয়
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": f"📝 নতুন পোস্ট তৈরি হয়েছে:\n\n{post_text}",
            "reply_markup": {
                "inline_keyboard": [[
                    {"text": "Approve ✅", "callback_data": f"approve_{post_id}"},
                    {"text": "Reject ❌", "callback_data": f"reject_{post_id}"}
                ]]
            }
        }
        
        print(">>> SENDING TO TELEGRAM <<<")
        tg_res = requests.post(url, json=payload)
        print(f">>> TELEGRAM RESPONSE: {tg_res.status_code} <<<")
        
    except Exception as e:
        print(f"❌ ERROR IN GENERATION: {e}")
        send_telegram_message(f"❌ পোস্ট তৈরি করতে সমস্যা হয়েছে: {e}")

def approve_and_publish_post(post_id, chat_id, message_id):
    """Approve করলে ফেসবুকে পোস্ট করবে"""
    if pending_posts_col is None: return
    post = pending_posts_col.find_one({"_id": ObjectId(post_id)})
    
    if post and post["status"] == "pending":
        post_text = post["text"]
        url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/feed"
        
        payload = {"message": post_text, "access_token": POST_ACCESS_TOKEN}
        res = requests.post(url, json=payload)
        
        if res.status_code == 200:
            pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "approved"}})
            edit_telegram_message(chat_id, message_id, f"✅ পোস্ট সফলভাবে ফেসবুকে পাবলিশ হয়েছে!\n\n{post_text[:100]}...")
        else:
            send_telegram_message(f"❌ ফেসবুকে পোস্ট করতে সমস্যা: {res.text}")

def reject_post(post_id, chat_id, message_id):
    if pending_posts_col is None: return
    pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "rejected"}})
    edit_telegram_message(chat_id, message_id, "❌ পোস্টটি বাতিল করা হয়েছে।")

def edit_telegram_message(chat_id, message_id, new_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageText"
    payload = {"chat_id": chat_id, "message_id": message_id, "text": new_text}
    requests.post(url, json=payload)

def send_telegram_message(message_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message_text}
    requests.post(url, json=payload)
