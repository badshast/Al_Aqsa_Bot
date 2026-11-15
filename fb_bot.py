import os
import json
import threading
import time
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from gemini_brain import AlAqsaAssistant
import pymongo

# Load environment variables
load_dotenv()

app = Flask(__name__)
import logging
logging.basicConfig(level=logging.INFO)
print('=== BOT STARTED === PAGE_TOKEN SET:', bool(os.getenv('PAGE_ACCESS_TOKEN')), 'VERIFY:', os.getenv('VERIFY_TOKEN'))

# Initialize AI Brain
ai_brain = AlAqsaAssistant()

# MongoDB Connection with Timeout
MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    try:
        # ৫ সেকেন্ডের মধ্যে কানেক্ট না হলে এরর দেবে, হ্যাং করবে না
        mongo_client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        db = mongo_client.get_database("alaqsa_db")
        messages_col = db.get_collection("processed_messages")
        print("✅ MONGODB CONNECTED SUCCESSFULLY.")
    except Exception as e:
        print(f"❌ MONGODB CONNECTION ERROR: {e}")
        messages_col = None
else:
    messages_col = None
    print("❌ MONGO_URI MISSING.")

# Secure Tokens
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

@app.route("/", methods=["GET"])
def home():
    return "✅ Al Aqsa Computer Master Automation & Full System is Running Live!"

@app.route("/health", methods=["GET"])
def health():
    return "OK", 200

@app.route("/privacy-policy", methods=["GET"])
def privacy_policy():
    return "<h1>Privacy Policy</h1><p>This is the privacy policy for Al Aqsa Bot.</p>"

@app.route("/terms-of-service", methods=["GET"])
def terms_of_service():
    return "<h1>Terms of Service</h1><p>By using this bot, you agree to our terms.</p>"

@app.route("/webhook", methods=["GET"])
def verify_webhook():
    mode = request.args.get("hub.mode")
    token = request.args.get("hub.verify_token")
    challenge = request.args.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == VERIFY_TOKEN:
            return challenge, 200
        else:
            return "Verification failed", 403
    return "Hello World", 200

@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.get_json(force=True, silent=True) or {}
    # ফেসবুককে সাথে সাথে ২০০ রেসপন্স দেওয়া
    threading.Thread(target=process_webhook_data, args=(data,)).start()
    return "EVENT_RECEIVED", 200

def process_webhook_data(data):
    try:
        if data.get("object") == "page":
            for entry in data.get("entry", []):
                
                # A. Handle Messenger Inbox Messages
                messaging_events = entry.get("messaging", [])
                for event in messaging_events:
                    # বটের নিজের পাঠানো মেসেজ ইগনোর করা (is_echo)
                    if event.get("message", {}).get("is_echo"):
                        continue

                    sender_id = event["sender"]["id"]
                    
                    # ডুপ্লিকেট মেসেজ চেক (MongoDB)
                    mid = event.get("message", {}).get("mid")
                    if mid and messages_col is not None:
                        if messages_col.find_one({"mid": mid}):
                            print(f"Duplicate message ignored: {mid}")
                            continue
                        else:
                            messages_col.insert_one({"mid": mid, "timestamp": time.time()})

                    if "message" in event and "text" in event["message"]:
                        user_message = event["message"]["text"]
                        process_facebook_text(sender_id, user_message)

                # B. Handle Page Comments (Smart Lead Hunter)
                changes = entry.get("changes", [])
                for change in changes:
                    if change.get("field") == "feed" and change.get("value", {}).get("item") == "comment":
                        val = change["value"]
                        if val.get("verb") == "add":
                            commenter_id = val.get("from", {}).get("id")
                            commenter_name = val.get("from", {}).get("name", "Student")
                            # নিজের পেজের কমেন্ট ইগনোর করা
                            if commenter_id != entry.get("id"): 
                                ai_brain.sync_to_crm(commenter_id, name=commenter_name, status="Commented on Post")
                                if not ai_brain.has_chatted_before(commenter_id):
                                    outreach_msg = f"আসসালামু আলাইকুম {commenter_name} ভাইয়া! আল আকসা কম্পিউটার পেজে আপনার কমেন্টটি দেখলাম। আমাদের কোর্সে ভর্তি চলছে। আপনি কোন কোর্সটি সম্পর্কে জানতে চান?"
                                    send_facebook_message(commenter_id, outreach_msg)
    except Exception as e:
        print(f"❌ THREAD ERROR: {e}")

def process_facebook_text(sender_id, text):
    try:
        result = ai_brain.handle_message(sender_id, text, "Student")
        print(f"🤖 AI REPLY GENERATED: {result['reply'][:50]}...")
        send_facebook_message(sender_id, result["reply"])
        
        if result.get("alert_admin") and result.get("alert_type") == "BARGAIN_LEAD":
            send_telegram_bargain_alert(sender_id, result["phone"], result["course"], result["final_fee"])
    except Exception as e:
        print(f"❌ TEXT PROCESSING ERROR: {e}")

def send_facebook_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        print(f"✅ FB API RESPONSE: {response.status_code}")
    except Exception as e:
        print(f"❌ FB API ERROR: {e}")

def send_telegram_bargain_alert(customer_id, phone, course, final_fee):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    msg = f"🚨 **নতুন ডিসকাউন্ট ও লিড অ্যালার্ট!**\n\n📞 **নম্বর:** `{phone}`\n📘 **কোর্স:** {course}\n💬 বটম-লাইন ফি: **{final_fee} টাকা**।"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
