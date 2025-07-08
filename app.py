import os
import json
import requests
import time
import pandas as pd
from flask import Flask, request, jsonify, send_from_directory
from dotenv import load_dotenv
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

# --- Load Environment Variables ---
load_dotenv()
app = Flask(__name__)

# --- Load Credentials ---
ACCESS_TOKEN         = os.getenv('ACCESS_TOKEN')
VERIFY_TOKEN         = os.getenv('VERIFY_TOKEN')
PHONE_NUMBER_ID      = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
API_BASE_URL         = os.getenv('BACKEND_API_BASE_URL')

# --- In‑memory user state store ---
user_states = {}

# --- Audio snippets (URLs) and crop/category data ---
AUDIO_CLIPS = {
    "welcome":      "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/welcome.mp3",
    "en": {
        'ask_name': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_name.mp3",
        'ask_address': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_address.mp3",
        "ask_state":   "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_state.mp3",
        'ask_pincode': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_pincode.mp3",
        'ask_password': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_password.mp3",
        'reg_complete': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_reg_complete.mp3",
        'ask_price': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_price.mp3",
        'ask_quantity': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_quantity.mp3",
        'ask_more_crops': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_more_crops.mp3",
        'next_crop': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_next_crop.mp3",
        'thank_you': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_thank_you.mp3",
        'welcome_back': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_welcome_back.mp3",
        'closing': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_closing.mp3",
        'ask_loginpassword': "https://raw.github.com/debdip4/agrikartwhatsappbot/main/Audio_files/en_ask_loginpassword.mp3",
    },
    "hi": {  # Hindi clips...
        'ask_name': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_name.mp3",
        'ask_address': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_address.mp3",
        "ask_state":   "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_state.mp3",
        'ask_pincode': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_pincode.mp3",
        'ask_password': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_password.mp3",
        'reg_complete': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_reg_complete.mp3",
        'ask_price': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_price.mp3",
        'ask_quantity': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_quantity.mp3",
        'ask_more_crops': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_more_crops.mp3",
        'next_crop': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_next_crop.mp3",
        'thank_you': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_thank_you.mp3",
        'welcome_back': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_welcome_back.mp3",
        'closing': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_closing.mp3",
        'ask_loginpassword': "https://raw.githubusercontent.com/debdip4/agrikartwhatsappbot/main/Audio_files/hi_ask_loginpassword.mp3",
    }
}

CROP_CATEGORIES = {
    "en": {"1":"Fruits","2":"Vegetables","3":"Organic","4":"Dairy & Eggs","5":"Grains & Pulses"},
    "hi": {"1":"फल","2":"सब्जियां","3":"जैविक","4":"डेयरी और अंडे","5":"अनाज और दालें"}
}

PRODUCTS_BY_CATEGORY = {
    "Fruits": [
        "Apple", "Mango", "Banana", "Grapes", "Orange", "Pineapple",
        "Papaya", "Guava", "Watermelon", "Pomegranate"
    ],
    "Vegetables": [
        "Potato", "Onion", "Tomato", "Carrot", "Cauliflower", "Brinjal",
        "Spinach", "Cabbage", "Lady Finger", "Beetroot"
    ],
    "Organic": [
        "Organic Honey", "Organic Tea", "Organic Rice", "Organic Turmeric",
        "Organic Jaggery", "Organic Wheat"
    ],
    "Dairy & Eggs": [
        "Milk", "Cheese", "Butter", "Eggs", "Curd", "Paneer", "Ghee"
    ],
    "Grains & Pulses": [
        "Wheat", "Rice", "Maize", "Arhar Dal", "Moong Dal", "Chana Dal",
        "Urad Dal", "Masoor Dal", "Barley", "Bajra"
    ]
}

AGMARKNET_STATES = {
    'Andhra Pradesh': 'AP',
    'Arunachal Pradesh': 'AR',
    'Assam': 'AS',
    'Bihar': 'BR',
    'Chhattisgarh': 'CG',
    'Goa': 'GA',
    'Gujarat': 'GJ',
    'Haryana': 'HR',
    'Himachal Pradesh': 'HP',
    'Jharkhand': 'JH',
    'Karnataka': 'KA',
    'Kerala': 'KL',
    'Madhya Pradesh': 'MP',
    'Maharashtra': 'MH',
    'Manipur': 'MN',
    'Meghalaya': 'ML',
    'Mizoram': 'MZ',
    'Nagaland': 'NL',
    'Odisha': 'OR',
    'Punjab': 'PB',
    'Rajasthan': 'RJ',
    'Sikkim': 'SK',
    'Tamil Nadu': 'TN',
    'Telangana': 'TG',
    'Tripura': 'TR',
    'Uttar Pradesh': 'UP',
    'Uttarakhand': 'UK',
    'West Bengal': 'WB',
    'Andaman and Nicobar Islands': 'AN',
    'Chandigarh': 'CH',
    'Dadra and Nagar Haveli and Daman and Diu': 'DN',
    'Delhi': 'DL',
    'Jammu and Kashmir': 'JK',
    'Ladakh': 'LA',
    'Lakshadweep': 'LD',
    'Puducherry': 'PY'
}


# --- Selenium setup & scraper ---
def setup_driver():
    opts = webdriver.ChromeOptions()
    opts.add_argument("--headless")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=opts)

def scrape_agmarknet_prices(state, commodity):
    code = AGMARKNET_STATES.get(state)
    if not code: return []
    driver = setup_driver()
    try:
        driver.get("https://agmarknet.gov.in/PriceAndArrivals/DatewiseCommodityReport.aspx")
        wait = WebDriverWait(driver, 10)
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboState")))).select_by_value(code)
        time.sleep(1)
        Select(wait.until(EC.presence_of_element_located((By.ID, "cphBody_cboCommodity")))).select_by_visible_text(commodity)
        driver.find_element(By.ID, "cphBody_btnSubmit").click()
        wait.until(EC.presence_of_element_located((By.ID, "cphBody_gridRecords")))
        tables = pd.read_html(driver.page_source, attrs={'id':'cphBody_gridRecords'})
        df = tables[0]
        # convert to per‑kg and return modal price list
        df['Modal Price (Rs./Kg)'] = pd.to_numeric(df['Modal Price (Rs./Quintal)'], errors='coerce')/100
        return df['Modal Price (Rs./Kg)'].dropna().round(2).astype(str).tolist()
    except:
        return []
    finally:
        driver.quit()

# --- Backend API helpers ---
def check_farmer_exists(phone_number):
    url = f"{API_BASE_URL}/api/v1/farmer/check/{phone_number}/"
    try:
        response = requests.get(url)
        return response.status_code == 200 and response.json().get("exists", False)
    except requests.exceptions.RequestException as e:
        print(f"ERROR checking farmer existence: {e}")
        return False


def register_farmer_api(user_data):
    url = f"{API_BASE_URL}/api/v1/auth/signup/farmer/"
    payload = {
        "username": user_data['username'],
        "password": user_data['password'],
        "email": f"{user_data['username']}@agrikart.ai",
        "phone_number": user_data['phone_number'],
        "name": user_data['name'],
        "address": user_data['address']
    }
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in register_farmer_api: {e}")
        return None

def login_farmer_api(username, password):
    url = f"{API_BASE_URL}/api/v1/auth/token/"
    payload = {"username": username, "password": password}
    try:
        res = requests.post(url, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in login_farmer_api: {e}")
        return None
    
def add_produce_api(produce_data, access_token):
    url = f"{API_BASE_URL}/api/v1/produce/"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    }
    payload = {
        "name": produce_data['name'],
        "price": float(produce_data['price_per_kg']),
        "quantity": float(produce_data['quantity_kg']),
        "category": "Others"
    }
    try:
        res = requests.post(url, headers=headers, json=payload)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"Error in add_produce_api: {e}")
        return None


# --- WhatsApp senders ---
def send_text(to, msg):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "text", "text": {"body": msg}}
    requests.post(url, headers=headers, json=payload)

def send_audio(to, url_link):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}", "Content-Type": "application/json"}
    payload = {"messaging_product": "whatsapp", "to": to, "type": "audio", "audio": {"link": url_link}}
    requests.post(url, headers=headers, json=payload)


# --- Webhook Handler ---
@app.route('/webhook', methods=['GET', 'POST'])
def webhook():
    if request.method == 'GET':
        if request.args.get('hub.mode') == 'subscribe' and request.args.get('hub.verify_token') == VERIFY_TOKEN:
            return request.args.get('hub.challenge'), 200
        return 'Unauthorized', 403

    data = request.get_json()
    msg = data['entry'][0]['changes'][0]['value'].get('messages',[{}])[0]
    from_no = msg.get('from')
    text   = msg.get('text',{}).get('body','').strip()
    cmd    = text.lower()

    if not from_no:
        return 'OK',200

    # init state
    if from_no not in user_states:
        user_states[from_no] = {'state':None,'data':{},'language':'en'}

    st = user_states[from_no]['state']
    lang = user_states[from_no]['language']

    # --- ENTRY: hi / hello ---
    if cmd in ['hi','hello','नमस्ते','Hi']:
        exists = check_farmer_exists(from_no)
        user_states[from_no]['state'] = 'awaiting_lang_after_exists' if exists else 'awaiting_language_choice'
        send_audio(from_no, AUDIO_CLIPS['welcome'])
        return 'OK',200

    # --- LANGUAGE CHOICE ---
    if st in ['awaiting_language_choice','awaiting_lang_after_exists']:
        is_existing = (st=='awaiting_lang_after_exists')
        # simple: 'hi'→Hindi else English
        lang = 'hi' if cmd in ['2','हिंदी','hi'] else 'en'
        user_states[from_no]['language'] = lang
        if is_existing:
            user_states[from_no]['state']='awaiting_password_login'
            send_audio(from_no, AUDIO_CLIPS[lang]['ask_loginpassword'])
        else:
            user_states[from_no]['state']='awaiting_name'
            send_audio(from_no, AUDIO_CLIPS[lang]['ask_name'])
        return 'OK',200

    # --- REGISTRATION ---
    if st=='awaiting_name':
        user_states[from_no]['data']['name']=text
        user_states[from_no]['state']='awaiting_address'
        send_audio(from_no, AUDIO_CLIPS[lang]['ask_address'])
        return 'OK',200

    if st=='awaiting_address':
        user_states[from_no]['data']['address']=text
        # ask state selection
        user_states[from_no]['state']='awaiting_state'
        states = sorted(AGMARKNET_STATES.keys())
        menu = "Select your state:\n" + "\n".join(f"{i+1}. {s}" for i,s in enumerate(states))
        send_text(from_no, menu)
        send_audio(from_no, AUDIO_CLIPS[lang]['ask_state'])
        return 'OK',200

    if st=='awaiting_state':
        try:
            idx=int(text)-1
            states=sorted(AGMARKNET_STATES.keys())
            sel=states[idx]
            user_states[from_no]['data']['state']=sel
            user_states[from_no]['state']='awaiting_pincode'
            send_audio(from_no, AUDIO_CLIPS[lang]['ask_pincode'])
        except:
            send_text(from_no,"Invalid. Reply with the number.")
        return 'OK',200

    if st=='awaiting_pincode':
        user_states[from_no]['data']['pincode']=text
        user_states[from_no]['state']='awaiting_password_register'
        send_audio(from_no, AUDIO_CLIPS[lang]['ask_password'])
        return 'OK',200

    if st=='awaiting_password_register':
        d=user_states[from_no]['data']
        d.update(username=from_no,phone_number=from_no,password=text)
        if register_farmer_api(d):
            token=login_farmer_api(from_no,text)
            if token:
                user_states[from_no]['access_token']=token
                user_states[from_no]['state']='awaiting_category'
                send_audio(from_no, AUDIO_CLIPS[lang]['reg_complete'])
                # immediately send category menu
                cat_menu = "Select category:\n" + "\n".join(f"{k}. {v}" for k,v in CROP_CATEGORIES[lang].items())
                send_text(from_no, cat_menu)
            else:
                send_text(from_no,"Registration OK but login failed. Please say 'hi' to retry.")
        else:
            send_text(from_no,"Registration failed. Please say 'hi' to start over.")
        return 'OK',200

    # --- LOGIN ---
    if st=='awaiting_password_login':
        token=login_farmer_api(from_no,text)
        if token:
            user_states[from_no]['access_token']=token
            user_states[from_no]['state']='awaiting_category'
            send_audio(from_no, AUDIO_CLIPS[lang]['welcome_back'])
            # then category
            cat_menu = "What would you like to sell today? Select category:\n" + "\n".join(f"{k}. {v}" for k,v in CROP_CATEGORIES[lang].items())
            send_text(from_no, cat_menu)
        else:
            send_text(from_no,"❌ Wrong password; try again.")
        return 'OK',200

    # --- CATEGORY SELECTION ---
    if st=='awaiting_category':
        if text in CROP_CATEGORIES[lang]:
            cat_en = CROP_CATEGORIES['en'][text]
            user_states[from_no]['temp_produce']={'category':cat_en}
            prods = PRODUCTS_BY_CATEGORY.get(cat_en,[])
            if prods:
                menu = "Select crop:\n" + "\n".join(f"{i+1}. {p}" for i,p in enumerate(prods))
                send_text(from_no, menu)
                user_states[from_no]['state']='awaiting_product'
            else:
                send_text(from_no,"No predefined products; type your crop name.")
                user_states[from_no]['state']='awaiting_crop_name_manual'
        else:
            send_text(from_no,"Invalid choice; reply with the category number.")
            user_states[from_no]['state']='awaiting_crop_name_manual'
        return 'OK',200

    # --- PRODUCT CHOICE ---
    if st=='awaiting_product':
        try:
            idx=int(text)-1
            cat=user_states[from_no]['temp_produce']['category']
            crop=PRODUCTS_BY_CATEGORY[cat][idx]
            user_states[from_no]['temp_produce']['name']=crop
            send_text(from_no,f"🔍 Looking up recent prices for {crop}...")
            state_name=user_states[from_no]['data']['state']
            prices=scrape_agmarknet_prices(state_name, crop)
            if prices:
                price_list = ", ".join(prices[:5]) + ("..." if len(prices)>5 else "")
                send_text(from_no, f"Recent modal prices (Rs/kg): {price_list}")
            else:
                send_text(from_no, "No recent prices found; please enter your price.")
            user_states[from_no]['state']='awaiting_price'
            send_audio(from_no, AUDIO_CLIPS[lang]['ask_price'])
        except:
            send_text(from_no,"Invalid. Reply with the crop number.")
        return 'OK',200

    if st=='awaiting_crop_name_manual':
        user_states[from_no]['temp_produce']={'name':text,'category':'Others'}
        send_text(from_no,f"Got it: {text}. Now enter price per kg.")
        send_audio(from_no, AUDIO_CLIPS[lang]['ask_price'])
        user_states[from_no]['state']='awaiting_price'
        return 'OK',200

    # --- PRICE & QUANTITY ---
    if st=='awaiting_price':
        user_states[from_no]['temp_produce']['price_per_kg']=text
        user_states[from_no]['state']='awaiting_quantity'
        send_audio(from_no, AUDIO_CLIPS[lang]['ask_quantity'])
        return 'OK',200

    if st=='awaiting_quantity':
        user_states[from_no]['temp_produce']['quantity_kg']=text
        token=user_states[from_no].get('access_token')
        success=token and add_produce_api(user_states[from_no]['temp_produce'], token)
        if success:
            send_text(from_no,"✅ Your produce has been listed!")
            send_audio(from_no, AUDIO_CLIPS[lang]['ask_more_crops'])
            user_states[from_no]['state']='awaiting_more_crops'
        else:
            send_text(from_no,"❌ Failed to list. Try later.")
            user_states[from_no]['state']='conversation_over'
        return 'OK',200

    # --- MORE CROPS? ---
    if st=='awaiting_more_crops':
        if cmd in ['yes','y','1','हाँ','हां']:
            user_states[from_no]['state']='awaiting_category'
            cat_menu = "Select next category:\n" + "\n".join(f"{k}. {v}" for k,v in CROP_CATEGORIES[lang].items())
            send_text(from_no, cat_menu)
        else:
            send_audio(from_no, AUDIO_CLIPS[lang]['thank_you'])
            user_states[from_no]['state']='conversation_over'
        return 'OK',200

    # --- THANK YOU catch-all ---
    if cmd in ['thank you','thanks']:
        send_audio(from_no, AUDIO_CLIPS[lang]['thank_you'])
        user_states[from_no]['state']='final'
        return 'OK',200

    return 'OK',200

# --- Notification endpoint unchanged ---
@app.route('/notify-farmer', methods=['POST'])
def notify_farmer():
    data = request.json
    phone = data.get('phone_number')
    items = data.get('items',[])
    if not phone or not items:
        return jsonify({"error":"Invalid"}),400
    lang = user_states.get(phone,{}).get('language','en')
    lines=[]
    hdr = "🎉 *New Order!*" if lang=='en' else "🎉 *नया ऑर्डर!*"
    lines.append(hdr)
    for it in items:
        if lang=='hi':
            lines.append(f"👉 {it['produce']} | बिक: {it['quantity_bought']}kg | बचे: {it['remaining_stock']}kg")
        else:
            lines.append(f"👉 {it['produce']} | Sold: {it['quantity_bought']}kg | Left: {it['remaining_stock']}kg")
    send_text(phone, "\n".join(lines))
    return jsonify({"status":"notified"}),200

if __name__ == '__main__':
    print("🚀 WhatsApp Bot Running...")
    # Create static/audio directory if it doesn't exist
    if not os.path.exists('static/audio'):
        os.makedirs('static/audio')
    app.run(port=5000, debug=True)