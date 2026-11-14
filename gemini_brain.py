import json
import os
import re
import requests
from groq import Groq
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# 1. Configure Groq AI securely
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if GROQ_API_KEY:
    groq_client = Groq(api_key=GROQ_API_KEY)
    print(f"✅ GROQ CLIENT INITIALIZED SUCCESSFULLY.")
else:
    groq_client = None
    print(f"❌ GROQ_API_KEY IS MISSING IN ENVIRONMENT VARIABLES!")

# 2. Google Sheet Cloud Database URL
GOOGLE_SHEET_WEBHOOK_URL = os.getenv("GOOGLE_SHEET_WEBHOOK_URL", "")

MASTER_SYSTEM_PROMPT = """
তুমি হলে "আল আকসা কম্পিউটার" (চকরিয়া, কক্সবাজার)-এর একজন দক্ষ, আন্তরিক এবং বিনয়ী সেলস এক্সিকিউটিভ। প্রতিষ্ঠানের পরিচালক: মোহাম্মদ বাদশা মিয়া। 

তোমার কথা বলার ধরন হবে একদম মানুষের মতো। রোবটের মতো কঠিন ভাষায় কথা বলবে না। কাস্টমারকে সম্বোধন করবে "ভাইয়া" বা "স্যার" বলে। (কখনোই কাস্টমারকে 'Student' বলে ডাকবে না)। উত্তরে যেন কোনো ফালতু কথা না থাকে, একদম সঠিক তথ্য দাও। যেখানে সম্ভব বুলেট পয়েন্ট (বিন্দু) ব্যবহার করে উত্তর পরিষ্কার ও গুছিয়ে দাও।

### ১. সরকারি ফ্রি কোর্সসমূহ (মেয়াদ: ৩ মাস | বয়স: ১৮ থেকে ৪৫ বছর)
- কোর্সসমূহ: ১. কম্পিউটার অফিস অ্যাপ্লিকেশন, ২. গ্রাফিক ডিজাইন, ৩. সেলাই প্রশিক্ষণ, ৪. সরকারি স্কিল ডেভেলপমেন্ট (ইন্ডাস্ট্রিয়াল বেকারি, শেফ)।
- ফি ও ভাতা: রেজিস্ট্রেশন ফি ১,৫০০ টাকা (ফেরতযোগ্য) + ফরম ফি ১০০ টাকা (মোট ১,৬০০ টাকা)। কোর্স শেষে ১০,০০০+ টাকা ভাতা ও সার্টিফিকেট পাবে। 
- মাস্টার-কি: কাস্টমার ফ্রি কোর্স করতে চাইলে তাকে প্রথমে "স্কিল ডেভেলপমেন্ট" কোর্সে ভর্তি হতে বলবে। কারণ এটি করলে পরে কম্পিউটার, গ্রাফিক ডিজাইন, ড্রাইভিং, জাপানিজ ভাষা—সবকিছু ফ্রিতে করা যাবে এবং প্রতিবার ভাতা পাওয়া যাবে।

### ২. পেইড কোর্স ও দরদামের (Bargain) কঠোর নিয়ম
কাস্টমারের দরদামের ধাপ (Step) তোমাকে নিচে জানিয়ে দেওয়া হবে। তুমি শুধু সেই ধাপের নির্ধারিত দামই বলবে, এক লাফে অনেক কম দাম বলবে না:
- কম্পিউটার অফিস অ্যাপ্লিকেশন (৩/৬ মাস): মূল ফি ৫,০০০ -> ১ম ছাড় ৪,৫০০ -> ২য় ছাড় ৪,০০০ -> বটম লাইন ৩,৫০০ টাকা।
- গ্রাফিক ডিজাইন (৩/৬ মাস): মূল ফি ৬,৫০০ -> ১ম ছাড় ৫,৫০০ -> ২য় ছাড় ৫,০০০ -> বটম লাইন ৪,৫০০ টাকা।
- সেলাই প্রশিক্ষণ (৩ মাস): মূল ফি ৪,৫০০ -> ১ম ছাড় ৩,৫০০ -> বটম লাইন ৩,০০০ টাকা।
- ফ্রিল্যান্সিং (৬ মাস): মূল ফি ১৫,০০০ -> ১ম ছাড় ১৪,০০০ -> ২য় ছাড় ১৩,০০০ -> বটম লাইন ১২,৫০০ টাকা। (কোর্স শেষে লাইভ অর্ডার দেওয়া হয়, প্রফিটের ২/৩ অংশ শিক্ষার্থী পাবে)।
- ফরেক্স ট্রেডিং (৩ মাস): ফি ১৫,০০০ টাকা (একদম ফিক্সড, ছাড় নেই)। 

### ৩. ভর্তির জন্য যা যা লাগবে (Admission Requirements)
কাস্টমার জিজ্ঞেস করলে বলবে:
১. এনআইডি (NID) বা জন্ম নিবন্ধন সনদের ফটোকপি।
২. ২ কপি পাসপোর্ট সাইজের ছবি।
৩. রেজিস্ট্রেশন ফি (সরকারি কোর্সের ক্ষেত্রে ১,৬০০ টাকা)।

### ৪. লোকেশন ও পেমেন্ট
- ঠিকানা: নতুন বাস টার্মিনাল (লামা-আলীকদম কাউন্টারের পাশে), পুরাতন কমার্স কলেজের ২য় তলা, চকরিয়া, কক্সবাজার।
- বিকাশ (Payment): 01777109390, নগদ: 01725259074। 
"""

class AlAqsaAssistant:
    def __init__(self, config_path="Courses.json"):
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                self.data = json.load(f)
        else:
            self.data = {}
        self.user_state = {}

    def sync_to_crm(self, customer_id, **kwargs):
        if not GOOGLE_SHEET_WEBHOOK_URL:
            return None
        payload = {"action": "upsert_lead", "customer_id": str(customer_id)}
        payload.update(kwargs)
        try:
            res = requests.post(GOOGLE_SHEET_WEBHOOK_URL, json=payload, timeout=5)
            if res.status_code == 200:
                return res.json()
        except Exception as e:
            print(f"Google Drive/Sheet Sync Error: {e}")
        return None

    def get_user_state(self, customer_id, customer_name="Student"):
        cid = str(customer_id)
        if cid in self.user_state:
            return self.user_state[cid]

        if GOOGLE_SHEET_WEBHOOK_URL:
            try:
                res = requests.post(
                    GOOGLE_SHEET_WEBHOOK_URL,
                    json={"action": "get_customer", "customer_id": cid},
                    timeout=5
                )
                if res.status_code == 200:
                    data = res.json()
                    if data.get("found"):
                        self.user_state[cid] = {
                            "step": int(data.get("step", 0)),
                            "course": data.get("course", "General Inquiry"),
                            "regular_fee": int(data.get("regular_fee", 5000)),
                            "step1_fee": int(data.get("offer_fee", 4500)),
                            "step2_fee": int(data.get("step2_fee", 4000)),
                            "final_fee": int(data.get("final_fee", 3500)),
                            "phone": data.get("phone", None),
                            "has_chatted": True,
                            "status": data.get("status", "Active Chat")
                        }
                        return self.user_state[cid]
            except Exception as e:
                print(f"Cloud Fetch Warning: {e}")

        self.user_state[cid] = {
            "step": 0,
            "course": "General Inquiry",
            "regular_fee": 5000,
            "step1_fee": 4500,
            "step2_fee": 4000,
            "final_fee": 3500,
            "phone": None,
            "has_chatted": False,
            "status": "New Lead"
        }
        return self.user_state[cid]

    def has_chatted_before(self, customer_id):
        state = self.get_user_state(customer_id)
        return state.get("has_chatted", False)

    def _detect_course_and_update_fees(self, text, state):
        t = text.lower()
        if state["course"] != "General Inquiry":
            return

        if any(w in t for w in ["freelanc", "ফ্রিল্যান্স", "আউটসোর্সিং", "digital marketing", "website", "hacking", "হ্যাকিং"]):
            state.update({"course": "Freelancing (6 Months)", "regular_fee": 15000, "step1_fee": 14000, "step2_fee": 13000, "final_fee": 12500, "step": 0})
        elif any(w in t for w in ["forex", "ফরেক্স", "ট্রেডিং", "trading"]):
            state.update({"course": "Forex Trading (3 Months)", "regular_fee": 15000, "step1_fee": 15000, "step2_fee": 15000, "final_fee": 15000, "step": 0})
        elif any(w in t for w in ["graphic", "গ্রাফিক", "গ্রাফিক্স", "ডিজাইন"]):
            state.update({"course": "Professional Graphic Design", "regular_fee": 6500, "step1_fee": 5500, "step2_fee": 5000, "final_fee": 4500, "step": 0})
        elif any(w in t for w in ["computer", "কম্পিউটার", "office", "অফিস"]):
            state.update({"course": "Computer Office Application", "regular_fee": 5000, "step1_fee": 4500, "step2_fee": 4000, "final_fee": 3500, "step": 0})
        elif any(w in t for w in ["tailor", "সেলাই", "ড্রেস"]):
            state.update({"course": "Tailoring & Dress Making", "regular_fee": 4500, "step1_fee": 3500, "step2_fee": 3200, "final_fee": 3000, "step": 0})
        elif any(w in t for w in ["free", "ফ্রি", "সরকারি", "ভাতা", "স্কিল", "skill"]):
            state["course"] = "Govt Free Skill Development"

    def handle_message(self, customer_id, message_text, customer_name="Student"):
        text = message_text.strip()
        lower_text = text.lower()
        state = self.get_user_state(customer_id, customer_name)
        state["has_chatted"] = True

        # 1. Phone Number Detection
        phone_match = re.search(r"01[3-9]\d{8}", lower_text)
        if phone_match:
            phone_number = phone_match.group(0)
            state["phone"] = phone_number
            state["status"] = "Waiting for Sir Approval"
            self.sync_to_crm(customer_id, name=customer_name, phone=phone_number, course=state["course"], bargain_step=state["step"], has_chatted=True, status=state["status"], note=f"Msg: {text}")
            return {"reply": "অসংখ্য ধন্যবাদ ভাইয়া! আপনার নম্বরটি আমি নোট করে নিয়েছি এবং বিষয়টি সরাসরি বাদশাহ স্যারকে জানিয়ে দিয়েছি।\n\nস্যার বর্তমানে ল্যাব ক্লাসে একটু ব্যস্ত আছেন। স্যারের সাথে কথা বলে আমি একটু পরেই আপনাকে মেসেজের মাধ্যমে চূড়ান্ত সিদ্ধান্ত জানিয়ে দেবো (ইনশাআল্লাহ)।", "alert_admin": True, "alert_type": "BARGAIN_LEAD", "phone": phone_number, "course": state["course"], "final_fee": state["final_fee"], "user_msg": text}

        # 2. Course Selection
        self._detect_course_and_update_fees(lower_text, state)

        # 3. Bargaining Logic & Smart Fallback Prep
        bargain_words = ["besi", "beshi", "kom", "koman", "discount", "বেশি", "কম", "কমান", "রাখেন", "ছাড়", "বাজেট", "টাকায় হবে"]
        is_bargaining = any(w in lower_text for w in bargain_words)

        bargain_instruction = ""
        fallback_reply = ""
        
        if is_bargaining and state["course"] != "Govt Free Skill Development":
            if state["course"] == "Forex Trading (3 Months)":
                bargain_instruction = "কাস্টমার দাম কমাতে চাচ্ছে। ফরেক্স ট্রেডিং কোর্সের ফি ১৫,০০০ টাকা একদম ফিক্সড, ১ টাকাও কমবে না। তবে তাকে মনে করিয়ে দাও যে ১,০০০ ডলার ইনভেস্টমেন্ট এখনই দিতে হবে না, কোর্স শেষেও করা যাবে।"
                fallback_reply = "ভাইয়া, ফরেক্স ট্রেডিং কোর্সের ফি ১৫,০০০ টাকা একদম ফিক্সড। এখানে কোনো ডিসকাউন্ট নেই। তবে লাইভ কাজের জন্য ১,০০০ ডলার ইনভেস্টমেন্ট এখনই দিতে হবে না, কোর্স শেষেও করা যাবে।"
            else:
                state["step"] += 1
                if state["step"] == 1:
                    offered = state["step1_fee"]
                    bargain_instruction = f"কাস্টমার ১ম বার দাম কমাতে বলছে। তাকে আমাদের আধুনিক ল্যাব ও আলাদা পিসির মান বুঝিয়ে বলো এবং বিশেষ ছাড়ের কথা বলে মাত্র ১ ধাপ কমিয়ে {offered} টাকা অফার করো। এর নিচে নামবে না।"
                    fallback_reply = f"ভাইয়া, আমাদের আধুনিক ল্যাব ও আলাদা পিসির সুবিধার কারণে ফি একটু বেশি। তবে আপনার আগ্রহের কথা চিন্তা করে বিশেষ ছাড়ে {offered} টাকা রাখা যাবে।"
                elif state["step"] == 2:
                    offered = state["step2_fee"]
                    bargain_instruction = f"কাস্টমার ২য় বার দাম কমাতে বলছে। তাকে বলো বাদশাহ স্যারের সাথে কথা বলে তার শেখার আগ্রহের কারণে আরও একটু কমিয়ে {offered} টাকা রাখা যাবে।"
                    fallback_reply = f"বাদশাহ স্যারের সাথে কথা বলে আপনার শেখার আগ্রহের কারণে আরও একটু কমিয়ে {offered} টাকা রাখা যাবে।"
                elif state["step"] == 3:
                    offered = state["final_fee"]
                    bargain_instruction = f"কাস্টমার ৩য় বার জোর করছে। তাকে বলো এটিই আমাদের সর্বনিম্ন বটম-লাইন ফি: {offered} টাকা। এর নিচে কোনোভাবেই সম্ভব নয়।"
                    fallback_reply = f"ভাইয়া, এটিই আমাদের সর্বনিম্ন বটম-লাইন ফি: {offered} টাকা। এর নিচে কোনোভাবেই সম্ভব নয়।"
                else:
                    offered = state["final_fee"]
                    bargain_instruction = f"কাস্টমার আমাদের সর্বনিম্ন দাম ({offered} টাকা)-এর চেয়েও কমে করতে চাচ্ছে। তুমি তাকে বলো যে {offered} টাকার নিচে কমানোর ক্ষমতা তোমার নেই, তবে সে যেন তার 'নাম', 'সচল মোবাইল নম্বর' এবং 'তার বাজেট কত' তা এখানে লিখে দেয়—তুমি বাদশাহ স্যারের সাথে কথা বলে তাকে এসএমএস দিয়ে জানাবে।"
                    fallback_reply = f"ভাইয়া, {offered} টাকার নিচে কমানোর ক্ষমতা আমার নেই। আপনি আপনার নাম, সচল মোবাইল নম্বর এবং আপনার বাজেট এখানে লিখে দিন। আমি বাদশাহ স্যারকে জানিয়ে আপনাকে জানাবো।"
        else:
            current_price_map = {0: state["regular_fee"], 1: state["step1_fee"], 2: state["step2_fee"], 3: state["final_fee"]}
            active_fee = current_price_map.get(state["step"], state["final_fee"])
            bargain_instruction = f"বর্তমানে কাস্টমারের কোর্স: {state['course']}। যদি দাম জানতে চায় তবে {active_fee} টাকা বলবে।"
            
            if "hi" in lower_text or "hello" in lower_text or "salam" in lower_text:
                fallback_reply = "আসসালামু আলাইকুম! আল আকসা কম্পিউটারে আপনাকে স্বাগতম। আপনি কোন কোর্সটি সম্পর্কে জানতে চান? (কম্পিউটার, গ্রাফিক ডিজাইন, ফ্রিল্যান্সিং, ফরেক্স বা সরকারি ফ্রি কোর্স)"
            elif any(w in lower_text for w in ["course ki", "course ache", "koto gulo course", "ki ki course", "কি কি কোর্স", "কোর্স কি"]):
                fallback_reply = "আমাদের এখানে যে যে কোর্স আছে: ১. কম্পিউটার অফিস অ্যাপ্লিকেশন (৫,০০০ টাকা), ২. গ্রাফিক ডিজাইন (৬,৫০০ টাকা), ৩. সেলাই প্রশিক্ষণ (৪,৫০০ টাকা), ৪. ফ্রিল্যান্সিং (১৫,০০০ টাকা), ৫. ফরেক্স ট্রেডিং (১৫,০০০ টাকা) এবং ৬. সরকারি ফ্রি কোর্স (১০,০০০+ ভাতা)। আপনি কোন কোর্সটি সম্পর্কে বিস্তারিত জানতে চান?"
            elif state["course"] == "Govt Free Skill Development":
                fallback_reply = "সরকারি ফ্রি কোর্সে ভর্তি চলছে! রেজিস্ট্রেশন ফি ১,৫০০ টাকা (ফেরতযোগ্য) এবং ফরম ফি ১০০ টাকা। কোর্স শেষে ১০,০০০+ টাকা ভাতা ও সার্টিফিকেট পাবেন। বিস্তারিত জানতে অফিসে আসুন।"
            else:
                fallback_reply = f"{state['course']} কোর্সের ফি {active_fee} টাকা। আমাদের ল্যাবে আলাদা পিসিতে Practical সহকারে ক্লাস করানো হয়। ভর্তি হতে চাইলে আপনার মোবাইল নম্বরটি দিন।"

        # 4. Generate Smart Response using Groq (Llama 3.3 70B)
        ai_reply = fallback_reply # Set the smart fallback as default
        
        if groq_client:
            try:
                prompt = f"কাস্টমারের নাম: {customer_name}\nকাস্টমারের মেসেজ: \"{text}\"\nতোমার জন্য বর্তমান নির্দেশনা: {bargain_instruction}\n\nউপরের নির্দেশনা মেনে কাস্টমারকে সরাসরি বাংলায় সুন্দর ও প্রফেশনাল উত্তর দাও:"
                
                response = groq_client.chat.completions.create(
                    messages=[
                        {"role": "system", "content": MASTER_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt}
                    ],
                    model="openai/gpt-oss-120b",
                    temperature=0.7,
                    max_tokens=1024
                )
                if response.choices[0].message.content:
                    ai_reply = response.choices[0].message.content.strip()
                    print(f"🤖 AI GENERATED REPLY: {ai_reply[:100]}...")
            except Exception as e:
                print(f"❌ GROQ API ERROR (Using Smart Fallback): {e}")

        # 5. Sync updated state
        self.sync_to_crm(customer_id, name=customer_name, course=state["course"], bargain_step=state["step"], regular_fee=state["regular_fee"], offer_fee=state["step1_fee"], final_fee=state["final_fee"], has_chatted=True, status=f"Active Chat (Step {state['step']})")

        return {"reply": ai_reply, "alert_admin": False}

    def analyze_payment_screenshot(self, image_bytes, mime_type="image/jpeg"):
        return "পেমেন্ট স্ক্রিনশটটি গ্রহণ করা হয়েছে। অ্যাডমিন যাচাই করে অল্প সময়ের মধ্যে কনফার্ম করবেন।"

    def handle_voice_message(self, customer_id, audio_bytes, mime_type="audio/ogg", customer_name="Student"):
        return {"reply": "ভাইয়া, ভয়েস মেসেজটি প্রসেস করার সিস্টেম আপাতত আপডেট হচ্ছে। অনুগ্রহ করে একটু লিখে বলবেন অথবা আপনার মোবাইল নম্বরটি দিন!", "alert_admin": False}
