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

# ==========================================
# ১. অটো-পোস্ট জেনারেটর (সিরিয়াল ওয়ার্কফ্লো সহ)
# ==========================================
def generate_post_for_approval():
    if not groq_client or pending_posts_col is None:
        send_telegram_message("❌ Groq বা MongoDB কানেক্টেড নেই।")
        return
    try:
        # কন্টেন্ট সিরিজ (আপনি চাইলে এখানে আরও টপিক যোগ করতে পারেন)
        content_series = [
            "MS Word কি এবং কেন শিখবেন? (বেসিক ধারণা)",
            "MS Word-এর ৫টি দরকারি শর্টকাট (Ctrl+B, Ctrl+I ইত্যাদি)",
            "MS Word-এ পেজ সেটআপ ও প্রিন্ট করার নিয়ম",
            "Excel কি এবং কেন দরকার? (বেসিক ধারণা)",
            "Excel-এ যোগ, বিয়োগ, গুণ ও ভাগ করার ফর্মুলা",
            "Excel-এর ৫টি দরকারি শর্টকাট (Ctrl+C, Ctrl+V, Ctrl+Z ইত্যাদি)",
            "ফ্রিল্যান্সিং শুরু করার প্রথম ধাপ কি?",
            "ফ্রিল্যান্সিংয়ে সফল হওয়ার ৩টি টিপস",
            "কম্পিউটার স্লো হলে কী করবেন?",
            "সাইবার সিকিউরিটি: পাসওয়ার্ড কতদিন পর পর পরিবর্তন করবেন?"
        ]

        # ডাটাবেস থেকে চেক করা সর্বশেষ কোন টপিক পোস্ট হয়েছে
        last_post = pending_posts_col.find_one({"type": "text", "status": "approved"}, sort=[("timestamp", -1)])
        
        next_index = 0
        if last_post and "topic" in last_post:
            last_topic = last_post["topic"]
            if last_topic in content_series:
                last_index = content_series.index(last_topic)
                next_index = (last_index + 1) % len(content_series) # শেষ হয়ে গেলে আবার শুরু থেকে
        
        selected_topic = content_series[next_index]
        print(f">>> AUTO GENERATING TOPIC: {selected_topic} <<<")

        prompt = f"""তুমি আল আকসা কম্পিউটারের সেলস ম্যানেজার। ফেসবুক পেজের জন্য একটি আকর্ষণীয় পোস্ট লিখো। 
        আজকের টপিক: {selected_topic}
        পোস্টের নিয়ম:
        ১. একটি আকর্ষণীয় হুক (প্রথম লাইন)।
        ২. ২ প্যারাগ্রাফের বিস্তারিত (যাতে কাস্টমার আগ্রহী হয়)।
        ৩. একটি শক্তিশালী Call to Action (যেমন: আজই ভর্তি হোন বা আমাদের ইনবক্স করুন)।
        ৪. ৫টি রিলেভেন্ট হ্যাশট্যাগ। 
        ভাষা হবে একদম প্রফেশনাল ও সাবলীল বাংলা।"""
        
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b",
            temperature=0.7
        )
        post_text = response.choices[0].message.content.strip()
        
        # ডাটাবেসে সেভ করা (টপিকের নাম সহ)
        result = pending_posts_col.insert_one({
            "text": post_text, 
            "topic": selected_topic, 
            "type": "text", 
            "status": "pending", 
            "timestamp": time.time()
        })
        post_id = str(result.inserted_id)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "text": f"📝 নতুন পোস্ট (টপিক: {selected_topic}):\n\n{post_text}",
            "reply_markup": {"inline_keyboard": [[{"text": "Approve ✅", "callback_data": f"approve_{post_id}"}, {"text": "Reject ❌", "callback_data": f"reject_{post_id}"}]]}
        }
        requests.post(url, json=payload)
    except Exception as e:
        send_telegram_message(f"❌ পোস্ট তৈরি করতে সমস্যা: {e}")

# ==========================================
# ২. ছবি রিসিভ করলে ক্যাপশন তৈরি
# ==========================================
def handle_telegram_photo(photo_file_id):
    if not groq_client or pending_posts_col is None: return
    try:
        prompt = "তুমি আল আকসা কম্পিউটারের সেলস ম্যানেজার। এই ছবির সাথে ফেসবুকের জন্য একটি আকর্ষণীয় ক্যাপশন লিখো। ২ প্যারাগ্রাফের পোস্ট হবে। সাথে ৫টি রিলেভেন্ট হ্যাশট্যাগ দাও। প্রফেশনাল বাংলায় লিখবে।"
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

# ==========================================
# ৩. ভিডিও রিসিভ করলে ক্যাপশন তৈরি
# ==========================================
def handle_telegram_video(video_file_id):
    if not groq_client or pending_posts_col is None: return
    try:
        prompt = "তুমি আল আকসা কম্পিউটারের সেলস ম্যানেজার। এই ভিডিওর সাথে ফেসবুকের জন্য একটি আকর্ষণীয় ক্যাপশন লিখো। ২ প্যারাগ্রাফের পোস্ট হবে। সাথে ৫টি রিলেভেন্ট হ্যাশট্যাগ দাও। প্রফেশনাল বাংলায় লিখবে।"
        response = groq_client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="openai/gpt-oss-120b",
            temperature=0.7
        )
        caption = response.choices[0].message.content.strip()
        
        result = pending_posts_col.insert_one({"file_id": video_file_id, "text": caption, "type": "video", "status": "pending", "timestamp": time.time()})
        post_id = str(result.inserted_id)
        
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo"
        payload = {
            "chat_id": ADMIN_CHAT_ID,
            "video": video_file_id,
            "caption": caption[:1000],
            "reply_markup": {"inline_keyboard": [[{"text": "Approve ✅", "callback_data": f"approve_{post_id}"}, {"text": "Reject ❌", "callback_data": f"reject_{post_id}"}]]}
        }
        requests.post(url, json=payload)
    except Exception as e:
        send_telegram_message(f"❌ ভিডিওর ক্যাপশন তৈরি করতে সমস্যা: {e}")

# ==========================================
# ৪. টেলিগ্রামের বাটন রিমুভার
# ==========================================
def remove_telegram_buttons(chat_id, message_id):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/editMessageReplyMarkup"
    payload = {"chat_id": chat_id, "message_id": message_id}
    requests.post(url, json=payload)

# ==========================================
# ৫. Approve করলে ফেসবুকে পাবলিশ
# ==========================================
def approve_and_publish_post(post_id, chat_id, message_id):
    if pending_posts_col is None: return
    
    # ডাবল ক্লিক প্রিভেন্ট (একবারে শুধু একটি রিকোয়েস্ট প্রসেস হবে)
    result = pending_posts_col.update_one(
        {"_id": ObjectId(post_id), "status": "pending"},
        {"$set": {"status": "processing"}}
    )
    
    if result.modified_count == 0:
        send_telegram_message("⚠️ এই পোস্টটি ইতিমধ্যে প্রসেস করা হচ্ছে বা হয়ে গেছে।")
        return

    post = pending_posts_col.find_one({"_id": ObjectId(post_id)})
    
    if post:
        post_text = post["text"]
        
        try:
            if post["type"] == "photo":
                file_id = post["file_id"]
                file_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}").json()
                file_path = file_res['result']['file_path']
                img_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                img_bytes = requests.get(img_url).content
                
                url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/photos"
                payload = {"message": post_text, "access_token": POST_ACCESS_TOKEN}
                files = {"source": ("image.jpg", img_bytes)}
                res = requests.post(url, data=payload, files=files)
                
            elif post["type"] == "video":
                file_id = post["file_id"]
                file_res = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getFile?file_id={file_id}").json()
                file_path = file_res['result']['file_path']
                vid_url = f"https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}"
                vid_bytes = requests.get(vid_url).content
                
                url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/videos"
                payload = {"description": post_text, "access_token": POST_ACCESS_TOKEN}
                files = {"source": ("video.mp4", vid_bytes)}
                res = requests.post(url, data=payload, files=files)
                
            else:
                url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/feed"
                payload = {"message": post_text, "access_token": POST_ACCESS_TOKEN}
                res = requests.post(url, json=payload)
            
            if res.status_code == 200:
                pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "approved"}})
                send_telegram_message(f"✅ **পোস্ট সফলভাবে ফেসবুকে পাবলিশ হয়েছে!**\n\n(পোস্ট আইডি: {res.json().get('id')})")
            else:
                pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "failed"}})
                send_telegram_message(f"❌ ফেসবুক এরর: {res.text}")
                
        except Exception as e:
            pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "failed"}})
            send_telegram_message(f"❌ কোডের ভেতরে এরর: {e}")

# ==========================================
# ৬. Reject করলে পোস্ট বাতিল
# ==========================================
def reject_post(post_id, chat_id, message_id):
    if pending_posts_col is None: return
    pending_posts_col.update_one({"_id": ObjectId(post_id)}, {"$set": {"status": "rejected"}})
    send_telegram_message("❌ পোস্টটি বাতিল করা হয়েছে।")

# ==========================================
# ৭. টেলিগ্রামে মেসেজ পাঠানোর সাধারণ ফাংশন
# ==========================================
def send_telegram_message(message_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": message_text, "parse_mode": "Markdown"}
    requests.post(url, json=payload)
