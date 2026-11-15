from PIL import Image, ImageDraw, ImageFont, ImageFilter
import os

# --- কনফিগারেশন ---
WIDTH, HEIGHT = 1080, 1080
BG_COLOR = (15, 23, 42)  # Dark Blue (Tech Background)
NEON_BLUE = (59, 130, 246)
NEON_GREEN = (16, 185, 129)
WHITE = (255, 255, 255)
GRAY = (148, 163, 184)

# ফন্ট এবং লোগোর পাথ (আপনার পিসি অনুযায়ী পরিবর্তন করুন)
FONT_PATH = "HindSiliguri-Bold.ttf" 
LOGO_PATH = "logo.png"

try:
    font_title = ImageFont.truetype(FONT_PATH, 80)
    font_subtitle = ImageFont.truetype(FONT_PATH, 50)
    font_text = ImageFont.truetype(FONT_PATH, 40)
    font_small = ImageFont.truetype(FONT_PATH, 30)
except IOError:
    print("❌ ফন্ট ফাইলটি পাওয়া যায়নি। দয়া করে HindSiliguri-Bold.ttf ডাউনলোড করে একই ফোল্ডারে রাখুন।")
    exit()

# --- ইমেজ তৈরি ---
img = Image.new('RGB', (WIDTH, HEIGHT), color=BG_COLOR)
draw = ImageDraw.Draw(img)

# টেক ব্যাকগ্রাউন্ড ইফেক্ট (নিয়ন লাইন)
draw.line([(0, 200), (WIDTH, 200)], fill=NEON_BLUE, width=5)
draw.line([(0, 850), (WIDTH, 850)], fill=NEON_BLUE, width=5)

# লোগো বসানো
if os.path.exists(LOGO_PATH):
    logo = Image.open(LOGO_PATH).convert("RGBA")
    logo = logo.resize((250, 250))
    # লোগোর পেছনে হালকা গ্লো (Glow)
    img.paste(logo, (WIDTH//2 - 125, 50), logo)
else:
    print("⚠️ লোগো পাওয়া যায়নি। লোগো ছাড়া ইমেজ তৈরি হচ্ছে।")

# --- টেক্সট বসানো ---
# ১. কোর্সের নাম
course_name = "কম্পিউটার অফিস অ্যাপ্লিকেশন"
draw.text((WIDTH//2, 350), course_name, font=font_title, fill=WHITE, anchor="mm")

# ২. মেয়াদ
duration = "মেয়াদ: ৩ / ৬ মাস"
draw.text((WIDTH//2, 460), duration, font=font_subtitle, fill=NEON_GREEN, anchor="mm")

# ৩. ফি (হাইলাইট করা)
fee_text = "কোর্স ফি: ৫,০০০ টাকা"
draw.rounded_rectangle([(WIDTH//2 - 200, 530), (WIDTH//2 + 200, 630)], radius=20, outline=NEON_BLUE, width=4)
draw.text((WIDTH//2, 580), fee_text, font=font_subtitle, fill=WHITE, anchor="mm")

# ৪. ফিচার বা সুবিধা
features = [
    "✓ প্র্যাকটিক্যাল ক্লাস",
    "✓ এক্সপার্ট ইন্সট্রাক্টর",
    "✓ সার্টিফিকেট প্রদান"
]
start_y = 680
for feature in features:
    draw.text((WIDTH//2, start_y), feature, font=font_text, fill=GRAY, anchor="mm")
    start_y += 60

# ৫. যোগাযোগ (নিচে)
primary_num = "কল করুন: ০১৭২৫২৫৯০৭৪"
whatsapp_num = "হোয়াটসঅ্যাপ: ০১৮৩২৪৬৫৭৯০"

draw.text((WIDTH//2 - 200, 920), primary_num, font=font_small, fill=WHITE, anchor="mm")
draw.text((WIDTH//2 + 200, 920), whatsapp_num, font=font_small, fill=WHITE, anchor="mm")

# ঠিকানা
address = "নতুন বাস টার্মিনাল (২য় তলা), চকরিয়া, কক্সবাজার"
draw.text((WIDTH//2, 1000), address, font=font_small, fill=GRAY, anchor="mm")

# --- ইমেজ সেভ করা ---
output_filename = "pilot_L1_CourseCard.png"
img.save(output_filename)
print(f"✅ সফলভাবে ইমেজ তৈরি হয়েছে: {output_filename}")
