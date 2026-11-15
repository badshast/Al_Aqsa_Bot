import os
import json
import threading
import time
from flask import Flask, request
import requests
from dotenv import load_dotenv
from gemini_brain import AlAqsaAssistant
import pymongo
import social_scheduler

load_dotenv()

app = Flask(__name__)
import logging
logging.basicConfig(level=logging.INFO)
print('=== BOT STARTED ===')

ai_brain = AlAqsaAssistant()

MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client.get_database("alaqsa_db")
        messages_col = db.get_collection("processed_messages")
        print("✅ MONGODB CONNECTED SUCCESSFULLY.")
    except Exception as e:
        print(f"❌ MONGODB CONNECTION ERROR: {e}")
        messages_col = None

PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

@app.route("/", methods=["GET"])
def home():
    return "✅ Al Aqsa Computer Master Automation is Running Live!"

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")
    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
    return "Verification failed", 403

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json(force=True, silent=True) or {}
    threading.Thread(target=process_webhook_data, args=(data,)).start()
    return "EVENT_RECEIVED", 200

def process_webhook_data(data):
    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                messaging_events = entry.get("messaging", [])
                for event in messaging_events:
                    
                    # স্যার (অ্যাডমিন) রিপ্লাই দিলে বট ১৫ মিনিটের জন্য চুপ হয়ে যাবে
                    if event.get("message", {}).get("is_echo"):
                        customer_id = event["recipient"]["id"]
                        if messages_col is not None:
                            db.get_collection("customers").update_one(
                                {"customer_id": str(customer_id)},
                                {"$set": {"bot_paused_until": time.time() + 300}} # ৩০০ সেকেন্ড = ৫ মিনিট
                            )
                            print(f"🤫 স্যার রিপ্লাই দিয়েছেন। কাস্টমার {customer_id}-এর জন্য বট ১৫ মিনিট বন্ধ থাকবে।")
                        continue

                    sender_id = event["sender"]["id"]
                    
                    # ডুপ্লিকেট মেসেজ চেক
                    mid = event.get("message", {}).get("mid")
                    if mid and messages_col is not None:
                        if messages_col.find_one({"mid": mid}): continue
                        else: messages_col.insert_one({"mid": mid, "timestamp": time.time()})

                    if "message" in event and "text" in event["message"]:
                        process_facebook_text(sender_id, event["message"]["text"])
                    
                    # ভয়েস মেসেজ হ্যান্ডেল করা
                    elif "message" in event and "attachments" in event["message"]:
                        for attachment in event["message"]["attachments"]:
                            if attachment.get("type") == "audio":
                                audio_url = attachment["payload"]["url"]
                                process_facebook_audio(sender_id, audio_url)
    except Exception as e:
        print(f"❌ THREAD ERROR: {e}")

def process_facebook_text(sender_id, text):
    try:
        result = ai_brain.handle_message(sender_id, text, "Student")
        
        # রিপ্লাই যদি None হয় (মানে বট পজ করা আছে), তবে কিছু পাঠাবে না
        if result.get("reply") is not None:
            send_facebook_message(sender_id, result["reply"])
            
            if result.get("alert_admin") and result.get("alert_type") == "BARGAIN_LEAD":
                msg = f"🚨 **নতুন লিড অ্যালার্ট!**\n\n📞 **নম্বর:** `{result['phone']}`\n📘 **কোর্স:** {result['course']}\n💬 শেষ দাম: **{result['final_fee']} টাকা**"
                social_scheduler.send_telegram_message(msg)
    except Exception as e:
        print(f"❌ TEXT ERROR: {e}")

def process_facebook_audio(sender_id, audio_url):
    try:
        # ১. অডিও ডাউনলোড করা
        audio_data = requests.get(audio_url).content
        
        # ২. Groq Whisper দিয়ে টেক্সটে রূপান্তর করা
        print(">>> TRANSCRIBING AUDIO <<<")
        transcript = ai_brain.transcribe_audio(audio_data, mime_type="audio/mp4")
        
        if transcript:
            print(f">>> TRANSCRIPTION SUCCESS: {transcript[:50]}...")
            # ৩. ট্রান্সক্রাইব করা টেক্সট দিয়ে মেসেজ প্রসেস করা
            process_facebook_text(sender_id, transcript)
        else:
            send_facebook_message(sender_id, "ভাইয়া, আপনার ভয়েস মেসেজটি স্পষ্ট বোঝা যায়নি। অনুগ্রহ করে একটু লিখে বলবেন?")
    except Exception as e:
        print(f"❌ AUDIO ERROR: {e}")
        send_facebook_message(sender_id, "ভয়েস প্রসেস করতে সমস্যা হচ্ছে। একটু লিখে বলবেন?")

def send_facebook_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ FB MSG ERROR: {e}")

@app.route("/telegram_webhook", methods=["POST"])
def telegram_webhook():
    data = request.get_json(force=True, silent=True) or {}
    
    if "message" in data:
        chat_id = data["message"]["chat"]["id"]
        text = data["message"].get("text", "")
        
        if str(chat_id) == str(ADMIN_CHAT_ID):
            if text == "/start":
                social_scheduler.send_telegram_message("আসসালামু আলাইকুম স্যার! পোস্ট তৈরি করতে `/newpost` দিন, অথবা সরাসরি ছবি বা ভিডিও পাঠান।")
            elif text == "/newpost":
                social_scheduler.send_telegram_message("⏳ স্যার, আমি এআই দিয়ে পোস্ট তৈরি করছি...")
                threading.Thread(target=social_scheduler.generate_post_for_approval).start()
            
            elif "photo" in data["message"]:
                photo_file_id = data["message"]["photo"][-1]["file_id"]
                social_scheduler.send_telegram_message("⏳ স্যার, ছবিটি পেয়েছি...")
                threading.Thread(target=social_scheduler.handle_telegram_photo, args=(photo_file_id,)).start()
            
            elif "video" in data["message"]:
                video_file_id = data["message"]["video"]["file_id"]
                social_scheduler.send_telegram_message("⏳ স্যার, ভিডিওটি পেয়েছি...")
                threading.Thread(target=social_scheduler.handle_telegram_video, args=(video_file_id,)).start()
            
            elif "document" in data["message"]:
                doc = data["message"]["document"]
                mime = doc.get("mime_type", "")
                if "image" in mime:
                    social_scheduler.send_telegram_message("⏳ স্যার, ইমেজ ফাইলটি পেয়েছি...")
                    threading.Thread(target=social_scheduler.handle_telegram_photo, args=(doc["file_id"],)).start()
                elif "video" in mime:
                    social_scheduler.send_telegram_message("⏳ স্যার, ভিডিও ফাইলটি পেয়েছি...")
                    threading.Thread(target=social_scheduler.handle_telegram_video, args=(doc["file_id"],)).start()

    elif "callback_query" in data:
        callback = data["callback_query"]
        chat_id = callback["message"]["chat"]["id"]
        message_id = callback["message"]["message_id"]
        callback_data = callback["data"]
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/answerCallbackQuery", json={"callback_query_id": callback["id"]})
        
        if str(chat_id) == str(ADMIN_CHAT_ID):
            if callback_data.startswith("approve_"):
                post_id = callback_data.split("_")[1]
                social_scheduler.remove_telegram_buttons(chat_id, message_id)
                threading.Thread(target=social_scheduler.approve_and_publish_post, args=(post_id, chat_id, message_id)).start()
            elif callback_data.startswith("reject_"):
                post_id = callback_data.split("_")[1]
                social_scheduler.remove_telegram_buttons(chat_id, message_id)
                social_scheduler.reject_post(post_id, chat_id, message_id)
                
    return {"ok": True}, 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
