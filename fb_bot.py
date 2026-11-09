import os
import json
import threading
import time
from flask import Flask, request
import requests
from PIL import Image, ImageDraw, ImageFont
from dotenv import load_dotenv
from gemini_brain import AlAqsaAssistant

# Load environment variables from .env file (for local testing)
load_dotenv()

app = Flask(__name__)

# Initialize Al Aqsa AI Brain (Cloud Database & Gemini 1.5 Flash)
ai_brain = AlAqsaAssistant()

# Secure Tokens & Keys fetched from Environment Variables (Render Dashboard / .env)
PAGE_ACCESS_TOKEN = os.getenv("PAGE_ACCESS_TOKEN")
VERIFY_TOKEN = os.getenv("VERIFY_TOKEN")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID")

@app.route("/", methods=["GET"])
def home():
    return "✅ Al Aqsa Computer Master Automation & Full System is Running Live!"

# 1. Facebook Webhook Verification
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

# 2. Handle Incoming Facebook Messenger & Comments Webhook
@app.route("/webhook", methods=["POST"])
def handle_webhook():
    data = request.json
    if data.get("object") == "page":
        for entry in data.get("entry", []):
            
            # A. Handle Messenger Inbox Messages
            messaging_events = entry.get("messaging", [])
            for event in messaging_events:
                sender_id = event["sender"]["id"]
                
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

            # B. Handle Page Comments (Smart Lead Hunter & Comment Automation)
            changes = entry.get("changes", [])
            for change in changes:
                if change.get("field") == "feed" and change.get("value", {}).get("item") == "comment":
                    val = change["value"]
                    if val.get("verb") == "add":
                        comment_text = val.get("message", "")
                        commenter_id = val.get("from", {}).get("id")
                        commenter_name = val.get("from", {}).get("name", "Student")
                        post_id = val.get("post_id", "")
                        
                        # Log comment to Google Sheets Cloud DB
                        ai_brain.sync_to_crm(commenter_id, name=commenter_name, status="Commented on Post")
                        
                        # Check if we already talked to this user in inbox
                        if not ai_brain.has_chatted_before(commenter_id):
                            # Trigger Proactive Inbox Outreach
                            outreach_msg = (
                                f"আসসালামু আলাইকুম {commenter_name} ভাইয়া! আল আকসা কম্পিউটার পেজে আপনার কমেন্টটি দেখলাম। "
                                f"আমাদের কম্পিউটার অফিস অ্যাপ্লিকেশন, গ্রাফিক ডিজাইন, ফ্রিল্যান্সিং ও সরকারি ফ্রি কোর্সে (১০,০০০+ টাকা ভাতা) ভর্তি চলছে। "
                                f"আপনি কোন কোর্সটি সম্পর্কে জানতে চান?"
                            )
                            send_facebook_message(commenter_id, outreach_msg)

    return "EVENT_RECEIVED", 200

def get_facebook_user_name(sender_id):
    """Fetch the real Facebook name of the user using Facebook Graph API to personalize AI responses."""
    try:
        url = f"https://graph.facebook.com/v18.0/{sender_id}?fields=first_name,last_name,name&access_token={PAGE_ACCESS_TOKEN}"
        res = requests.get(url).json()
        return res.get("name", "Student")
    except:
        return "Student"

def process_facebook_text(sender_id, text):
    """Process customer text through Gemini AI Brain and send personalized reply."""
    # Fetch real Facebook user name for personalization
    customer_name = get_facebook_user_name(sender_id)
    
    # Pass message to AI Brain
    result = ai_brain.handle_message(sender_id, text, customer_name)
    reply_text = result["reply"]
    
    # Send reply back to Facebook Messenger
    send_facebook_message(sender_id, reply_text)

    # If admission or deal is finalized, generate Digital VIP Token / Admit Pass
    lower_t = text.lower()
    if any(w in lower_t for w in ['konfirm', 'konfirme', 'admission', 'vorti', 'vortibo', 'কনফার্ম', 'ভর্তি']):
        state = ai_brain.get_user_state(sender_id)
        pass_image_path = generate_digital_pass(customer_name, state.get("course", "Computer Office Application"))
        send_facebook_image_file(sender_id, pass_image_path, caption=f"🎟️ {customer_name} ভাইয়া, আপনার নামে আল আকসা কম্পিউটারের ডিজিটাল ভিআইপি টোকেন/গেট-পাস ইস্যু করা হলো! অফিসে আসার সময় এটি দেখিয়ে স্পেশাল ছাড় ও অগ্রাধিকার পাবেন।")

    # If user gave phone during bargaining, send Telegram Alert to Sir with 15-min timer
    if result.get("alert_admin") and result.get("alert_type") == "BARGAIN_LEAD":
        send_telegram_bargain_alert(sender_id, result.get("phone", "N/A"), result.get("course", "General"), result.get("final_fee", "3500"))
        threading.Thread(target=auto_followup_timer, args=(sender_id, result.get("final_fee", "3500"))).start()

def process_facebook_audio(sender_id, audio_url):
    """Download customer voice note and process with Gemini AI"""
    try:
        audio_data = requests.get(audio_url).content
        result = ai_brain.handle_voice_message(sender_id, audio_data, mime_type="audio/mp4")
        send_facebook_message(sender_id, result["reply"])
    except Exception as e:
        send_facebook_message(sender_id, "ভাইয়া, আপনার ভয়েস নোটটি প্রসেস করতে সমস্যা হয়েছে। অনুগ্রহ করে লিখে দিন!")

def process_facebook_image(sender_id, image_url):
    """Download payment screenshot and verify with Gemini Vision OCR"""
    try:
        image_data = requests.get(image_url).content
        ocr_result = ai_brain.analyze_payment_screenshot(image_data, mime_type="image/jpeg")
        
        send_facebook_message(
            sender_id, 
            "অসংখ্য ধন্যবাদ! আপনার পেমেন্টের স্ক্রিনশটটি আমরা যাচাইয়ের জন্য বাদশাহ স্যারের কাছে পাঠিয়ে দিয়েছি। স্যার চেক করলেই সিট কনফার্মেশন মেসেজ পেয়ে যাবেন!"
        )
        send_telegram_photo_to_admin(sender_id, image_url, ocr_result)
    except Exception as e:
        send_facebook_message(sender_id, "ছবিটি প্রসেস করতে সমস্যা হয়েছে। দয়া করে আবার পাঠান।")

def generate_digital_pass(student_name, course_name):
    """Generate a dynamic Digital VIP Token / Admit Pass image for the student"""
    img_width, img_height = 800, 400
    card = Image.new("RGB", (img_width, img_height), color=(15, 23, 42)) # Dark blue background
    draw = ImageDraw.Draw(card)
    
    # Draw decorative border
    draw.rectangle([15, 15, img_width - 15, img_height - 15], outline=(59, 130, 246), width=4)
    
    # Text details
    draw.text((40, 40), "AL AQSA COMPUTER & TRAINING CENTER", fill=(255, 255, 255))
    draw.text((40, 80), "Chakaria, Cox's Bazar | Director: Mohammad Badsha Mia", fill=(148, 163, 184))
    
    draw.line([40, 130, img_width - 40, 130], fill=(59, 130, 246), width=2)
    
    draw.text((40, 160), f"STUDENT NAME: {student_name.upper()}", fill=(255, 255, 255))
    draw.text((40, 210), f"SELECTED COURSE: {course_name}", fill=(52, 211, 153))
    draw.text((40, 260), "STATUS: VIP SEAT RESERVED & VERIFIED", fill=(250, 204, 21))
    
    draw.text((40, 330), "📍 Notun Bus Terminal (2nd Floor, Old Commerce College)", fill=(148, 163, 184))
    
    filename = f"admit_pass_{int(time.time())}.png"
    card.save(filename)
    return filename

def send_facebook_message(recipient_id, message_text):
    url = f"https://graph.facebook.com/v18.0/me/messages?access_token={PAGE_ACCESS_TOKEN}"
    payload = {"recipient": {"id": recipient_id}, "message": {"text": message_text}}
    headers = {"Content-Type": "application/json"}
    requests.post(url, json=payload, headers=headers)

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

def auto_followup_timer(customer_id, final_fee):
    time.sleep(900) # 15 minutes timer
    state = ai_brain.get_user_state(customer_id)
    if "Waiting for Sir" in str(state.get("status", "")):
        ai_brain.sync_to_crm(customer_id, status="Auto-Approved after 15 mins", offered_fee=str(final_fee))
        auto_msg = f"আসসালামু আলাইকুম ভাইয়া! বাদশাহ স্যারের সাথে কথা হয়েছে। আপনার প্রবল শেখার আগ্রহের কারণে স্যার বিশেষ বিবেচনায় আপনার কোর্স ফি সর্বশেষ **{final_fee} টাকা** রাখার অনুমতি দিয়েছেন!"
        send_facebook_message(customer_id, auto_msg)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
