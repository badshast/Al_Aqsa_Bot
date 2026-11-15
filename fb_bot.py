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

# MongoDB Connection
MONGO_URI = os.getenv("MONGO_URI")
if MONGO_URI:
    try:
        mongo_client = pymongo.MongoClient(MONGO_URI)
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
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Privacy Policy - Al Aqsa Computer</title>
        <style>body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }</style>
    </head>
    <body>
        <h1>Privacy Policy</h1>
        <p>Last updated: November 2026</p>
        <p><strong>Al Aqsa Computer & Matamuhuri Trade & Supply Ltd.</strong> ("we", "us", or "our") operates the Al Aqsa Computer Automation bot. This page informs you of our policies regarding the collection, use, and disclosure of personal data when you use our Facebook Messenger service.</p>
        <h2>1. Information We Collect</h2>
        <p>When you interact with our Facebook Page or Messenger bot, we may collect the following information:</p>
        <ul>
            <li>Your Facebook Profile Name and ID (PSID).</li>
            <li>Messages you send to us (text, voice notes, and images).</li>
            <li>Phone numbers you voluntarily provide during a conversation.</li>
            <li>Payment screenshots (bKash/Nagad) if you choose to share them for course enrollment.</li>
        </ul>
        <h2>2. How We Use Your Information</h2>
        <p>We use the collected information for the following purposes:</p>
        <ul>
            <li>To respond to your inquiries regarding our courses and services.</li>
            <li>To process admissions, course registrations, and issue digital VIP tokens.</li>
            <li>To communicate with you via Messenger or SMS regarding your admission.</li>
            <li>We store this data securely in MongoDB (Cloud CRM) to maintain your student profile.</li>
        </ul>
        <h2>3. Data Sharing and Disclosure</h2>
        <p>We do not sell, trade, or rent your personal information to third parties. We only share information with our internal administration (via Telegram) to process your requests.</p>
        <h2>4. Data Deletion</h2>
        <p>You have the right to request the deletion of your data. If you wish to have your chat history, phone number, or profile removed from our database, please contact us with the subject "Data Deletion Request" at:</p>
        <p><strong>Email:</strong> mohammadbadsha070@gmail.com<br>
        <strong>Phone/WhatsApp:</strong> 01832465790</p>
        <h2>5. Contact Us</h2>
        <p>If you have any questions about this Privacy Policy, please contact us at:<br>
        Al Aqsa Computer, New Bus Terminal (2nd Floor, Old Commerce College), Chakaria, Cox's Bazar.</p>
    </body>
    </html>
    """
    return html_content

@app.route("/terms-of-service", methods=["GET"])
def terms_of_service():
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Terms of Service - Al Aqsa Computer</title>
        <style>body { font-family: Arial, sans-serif; line-height: 1.6; padding: 20px; max-width: 800px; margin: auto; }</style>
    </head>
    <body>
        <h1>Terms of Service</h1>
        <p>Last updated: November 2026</p>
        <p>By using the Al Aqsa Computer Automation bot on Facebook Messenger, you agree to the following terms and conditions.</p>
        <h2>1. Services Provided</h2>
        <p>Our bot provides information about our computer courses, pricing, admission procedures, and processes lead inquiries. We reserve the right to modify course fees, schedules, and policies without prior notice.</p>
        <h2>2. User Conduct</h2>
        <p>You agree to use this bot for lawful purposes only. You must not use the bot to send spam, abusive language, or false information. Any misuse may result in a block from our page.</p>
        <h2>3. Payments and Refunds</h2>
        <p>All course payments must be made through our official bKash/Nagad numbers. Admission is only confirmed upon verification of payment by our administration. Refund policies are strictly governed by our physical institution's rules and government free course guidelines.</p>
        <h2>4. Automated Responses</h2>
        <p>You acknowledge that you are interacting with an AI-powered bot. While we strive for accuracy, the bot may occasionally provide incorrect information. Final decisions regarding admissions and fees will be made by our human administrators.</p>
        <h2>5. Contact Information</h2>
        <p>For official inquiries, please contact:<br>
        <strong>Phone:</strong> 01725259074<br>
        <strong>Location:</strong> Notun Bus Terminal, Chakaria, Cox's Bazar.</p>
    </body>
    </html>
    """
    return html_content

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
    
    # রেসপন্স ইনস্ট্যান্ট পাঠানোর জন্য থ্রেড ব্যবহার (যাতে ফেসবুক টাইমআউট না খায়)
    threading.Thread(target=process_webhook_data, args=(data,)).start()
    
    return "EVENT_RECEIVED", 200

def process_webhook_data(data):
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            
            # A. Handle Messenger Inbox Messages
            messaging_events = entry.get("messaging", [])
            for event in messaging_events:
                # ১. বটের নিজের পাঠানো মেসেজ ইগনোর করা (is_echo)
                if event.get("message", {}).get("is_echo"):
                    continue

                sender_id = event["sender"]["id"]
                
                # ২. ডুপ্লিকেট মেসেজ চেক (MongoDB)
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

                elif "message" in event and "attachments" in event["message"]:
                    for attachment in event["message"]["attachments"]:
                        if attachment.get("type") == "audio":
                            audio_url = attachment["payload"]["url"]
                            process_facebook_audio(sender_id, audio_url)
                        elif attachment.get("type") == "image":
                            image_url = attachment["payload"]["url"]
                            process_facebook_image(sender_id, image_url)

            # B. Handle Page Comments (Smart Lead Hunter)
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "feed" and change.get("value", {}).get("item") == "comment":
                    val = change["value"]
                    if val.get("verb") == "add":
                        comment_text = val.get("message", "")
                        commenter_id = val.get("from", {}).get("id")
                        commenter_name = val.get("from", {}).get("name", "Student")
                        
                        ai_brain.sync_to_crm(commenter_id, name=commenter_name, status="Commented on Post")
                        
                        if not ai_brain.has_chatted_before(commenter_id):
                            outreach_msg = f"আসসালামু আলাইকুম {commenter_name} ভাইয়া! আল আকসা কম্পিউটার পেজে আপনার কমেন্টটি দেখলাম। আমাদের কোর্সে ভর্তি চলছে। আপনি কোন কোর্সটি সম্পর্কে জানতে চান?"
                            send_facebook_message(commenter_id, outreach_msg)

def process_facebook_text(sender_id, text):
    result = ai_brain.handle_message(sender_id, text, "Student")
    send_facebook_message(sender_id, result["reply"])

    lower_t = text.lower()
    if any(w in lower_t for w in ['konfirm', 'konfirme', 'admission', 'vorti', 'vortibo', 'কনফার্ম', 'ভর্তি']):
        state = ai_brain.get_user_state(sender_id)
        pass_image_path = generate_digital_pass("Student", state["course"])
        send_facebook_image_file(sender_id, pass_image_path, caption="🎟️ আপনার ডিজিটাল ভিআইপি টোকেন ইস্যু করা হলো!")

    if result.get("alert_admin") and result.get("alert_type") == "BARGAIN_LEAD":
        send_telegram_bargain_alert(sender_id, result["phone"], result["course"], result["final_fee"])

def process_facebook_audio(sender_id, audio_url):
    try:
        audio_data = requests.get(audio_url).content
        result = ai_brain.handle_voice_message(sender_id, audio_data, mime_type="audio/mp4")
        send_facebook_message(sender_id, result["reply"])
    except Exception as e:
        send_facebook_message(sender_id, "ভাইয়া, আপনার ভয়েস নোটটি প্রসেস করতে সমস্যা হয়েছে।")

def process_facebook_image(sender_id, image_url):
    try:
        image_data = requests.get(image_url).content
        ocr_result = ai_brain.analyze_payment_screenshot(image_data, mime_type="image/jpeg")
        send_facebook_message(sender_id, "আপনার পেমেন্টের স্ক্রিনশটটি যাচাইয়ের জন্য পাঠানো হয়েছে।")
        send_telegram_photo_to_admin(sender_id, image_url, ocr_result)
    except Exception as e:
        send_facebook_message(sender_id, "ছবিটি প্রসেস করতে সমস্যা হয়েছে।")

def generate_digital_pass(student_name, course_name):
    img_width, img_height = 800, 400
    card = Image.new("RGB", (img_width, img_height), color=(15, 23, 42)) 
    draw = ImageDraw.Draw(card)
    draw.rectangle([15, 15, img_width - 15, img_height - 15], outline=(59, 130, 246), width=4)
    draw.text((40, 40), "AL AQSA COMPUTER & TRAINING CENTER", fill=(255, 255, 255))
    draw.text((40, 80), "Chakaria, Cox's Bazar | Director: Mohammad Badsha Mia", fill=(148, 163, 184))
    draw.line([40, 130, img_width - 40, 130], fill=(59, 130, 246), width=2)
    draw.text((40, 160), f"STUDENT NAME: {student_name.upper()}", fill=(255, 255, 255))
    draw.text((40, 210), f"SELECTED COURSE: {course_name}", fill=(52, 211, 153))
    draw.text((40, 260), "STATUS: VIP SEAT RESERVED & VERIFIED", fill=(250, 204, 21))
    filename = f"admit_pass_{int(time.time())}.png"
    card.save(filename)
    return filename

def send_facebook_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    requests.post(url, json=payload)

def send_facebook_image_file(recipient_id, image_path, caption=""):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": json.dumps({"id": recipient_id})}
    if caption:
        payload["message"] = json.dumps({"text": caption})
    with open(image_path, "rb") as img:
        files = {"filedata": (image_path, img, "image/png")}
        requests.post(url, data=payload, files=files)

def send_telegram_bargain_alert(customer_id, phone, course, final_fee):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    msg = f"🚨 **নতুন ডিসকাউন্ট ও লিড অ্যালার্ট!**\n\n📞 **নম্বর:** `{phone}`\n📘 **কোর্স:** {course}\n💬 বটম-লাইন ফি: **{final_fee} টাকা**।"
    payload = {"chat_id": ADMIN_CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

def send_telegram_photo_to_admin(customer_id, image_url, ocr_text):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPhoto"
    caption = f"💳 **পেমেন্ট স্ক্রিনশট (OCR):**\n{ocr_text}\n\nCustomer ID: `{customer_id}`"
    payload = {"chat_id": ADMIN_CHAT_ID, "photo": image_url, "caption": caption, "parse_mode": "Markdown"}
    requests.post(url, json=payload)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
