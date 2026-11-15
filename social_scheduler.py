import os
import requests
import time
from groq import Groq
from dotenv import load_dotenv
import pymongo
from bson.objectid import ObjectId

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

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
    if not groq_client or pending_posts_col is None:
        send_telegram_message("❌ Groq বা MongoDB কানেক্টেড নেই।")
        return
    try:
        prompt = "তুমি আল আকসা কম্পিউটারের সেলস ম্যানেজার। ফেসবুক পেজের জন্য একটি আকর্ষণীয় পোস্ট লিখো। কম্পিউটার, গ্রাফিক ডিজাইন বা ফ্রিল্যান্সিং কোর্সের ওপর ২ প্যারাগ্রাফের পোস্ট হবে। সাথে ৫টি রিলেভেন্ট হ্যাশট্যাগ দাও। একদম প্রফেশনাল বাংলায় লিখবে।"
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b",
            temperature=0.7
        )
        post_text = response.choices[0].message.content.strip()
        
        result = pending_posts_col.insert_one({"text": post_text, "type": "text", "status": "pending", "timestamp": time.time()})
        post_id = str(result.inserted_id)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": f"📝 নতুন টেক্সট পোস্ট:\n\n{post_text}",
            "reply_markup": {"inline_keyboard": [[{"text": "Approve ✅", "callback_data": f"approve_{post_id}"}, {"text": "Reject ❌", "callback_data": f"reject_{post_id}"}]]}
        }
        requests.post(url, json=payload)
    except Exception as e:
        send_telegram_message(f"❌ পোস্ট তৈরি করতে সমস্যা: {e}")

def handle_telegram_photo(photo_file_id):
    if not groq_client or pending_posts_col is None: return
    try:
        prompt = "তুমি আল আকসা কম্পিউটারের সেলস ম্যানেজার। এই ছবির সাথে ফেসবুকের জন্য একটি আকর্ষণীয় ক্যাপশন লিখো। ছবিটি আল আকসা কম্পিউটারের একটি ডিজাইন। ২ প্যারাগ্রাফের পোস্ট হবে। সাথে ৫টি রিলেভেন্ট হ্যাশট্যাগ দাও। প্রফেশনাল বাংলায় লিখবে।"
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b",
            temperature=0.7
        )
        caption = response.choices[0].message.content.strip()
        
        result = pending_posts_col.insert_one({"file_id": photo_file_id, "text": caption, "type": "photo", "status": "pending", "timestamp": time.time()})
        post_id = str(result.inserted_id)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "photo": photo_file_id,
            "caption": caption[:1000],
            "reply_markup": {"inline_keyboard": [[{"text": "Approve ✅", "callback_data": f"approve_{post_id}"}, {"text": "Reject ❌", "callback_data": f"reject_{post_id}"}]]}
        }
        requests.post(url, json=payload)
    except Exception as e:
        send_telegram_message(f"❌ ছবির ক্যাপশন তৈরি করতে সমস্যা: {e}")

def approve_and_publish_post(post_id, chat_id, message_id):
    if pending_posts_col is None: return
    post = pending_posts_col.find_one({"_id": ObjectId(post_id)})
    
    if post and post["status"] == "pending":
        post_text = post["text"]
        
        if post["type"] == "photo":
            file_id = post["file_id"]
            file_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}").json()
            
            if "result" not in file_res:
                send_telegram_message("❌ টেলিগ্রাম থেকে ফাইলটি ডাউনলোড করা যাচ্ছে না।")
                return
                
            file_path = file_res['result']['file_path']
            img_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
            img_bytes = requests.get(img_url).content
            
            url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/photos"
            payload = {"message": post_text, "access_token": POST_ACCESS_TOKEN}
            files = {"source": ("image.jpg", img_bytes)}
            
            print(">>> POSTING PHOTO TO FACEBOOK <<<")
            res = requests.post(url, data=payload, files=files)
            print(f">>> FB PHOTO RESPONSE: {res.status_code} - {res.text}")
            
        else:
            url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/feed"
            payload = {"message": post_text, "access_token": POST_ACCESS_TOKEN}
            
            print(">>> POSTING TEXT TO FACEBOOK <<<")
            res = requests.post(url, json=payload)
            print(f">>> FB TEXT RESPONSE: {res.status_code} - {res.text}")
        
        if res.status_code == 200:
            pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "approved"}})
            edit_telegram_message(chat_id, message_id, f"✅ পোস্ট সফলভাবে ফেসবুকে পাবলিশ হয়েছে!")
        else:
            send_telegram_message(f"❌ ফেসবুক এরর: {res.text}")

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
