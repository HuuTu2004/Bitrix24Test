from flask import Flask, request, redirect, render_template, jsonify
import requests
import json
import os
import threading
import time

app = Flask(__name__)

# ----- Cấu hình Bitrix24 -----
BITRIX_CLIENT_ID = "local.67cffe70b80d31.65971584"
BITRIX_CLIENT_SECRET = "OfwguhSRQJn7la9vZqstS6Yk8RxKLWI2P7ZeTDdZcU8vbCMY5Y"
REDIRECT_URI = "https://7f9e-222-252-92-203.ngrok-free.app"
TOKEN_FILE = "tokens.json"

# ----- Quản lý Token -----
def save_token(token_data):
    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=4)

def load_token():
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            return json.load(f)
    return None

def check_access_token():
    token_data = load_token()
    if not token_data or "access_token" not in token_data:
        return None
    return token_data["access_token"]

def refresh_access_token():
    token_data = load_token()
    if not token_data or "refresh_token" not in token_data:
        return None

    refresh_url = "https://oauth.bitrix.info/oauth/token/"
    params = {
        "grant_type": "refresh_token",
        "client_id": BITRIX_CLIENT_ID,
        "client_secret": BITRIX_CLIENT_SECRET,
        "refresh_token": token_data["refresh_token"],
    }
    response = requests.post(refresh_url, data=params)
    
    if response.status_code == 200:
        new_token_data = response.json()
        save_token(new_token_data)
        print("✅ Token refreshed successfully!")
        return new_token_data.get("access_token")
    print("❌ Failed to refresh token!")
    return None

def fetch_new_token(auth_code):
    token_url = "https://oauth.bitrix.info/oauth/token/"
    params = {
        "grant_type": "authorization_code",
        "client_id": BITRIX_CLIENT_ID,
        "client_secret": BITRIX_CLIENT_SECRET,
        "redirect_uri": REDIRECT_URI,
        "code": auth_code,
    }
    response = requests.post(token_url, data=params)
    
    if response.status_code == 200:
        token_data = response.json()
        save_token(token_data)
        return token_data.get("access_token")
    return None

# ----- Tự động refresh token định kỳ -----
def auto_refresh_token():
    while True:
        time.sleep(2700) 
        new_access_token = refresh_access_token()
        if new_access_token:
            print("✅ Access token refreshed thành công!")
        else:
            print("❌ Thất bại trong việc refreshed token")

# ----- Gọi API Bitrix24 -----
def call_bitrix_api(action, payload=None):
    access_token = check_access_token()
    if not access_token:
        auth_code = request.args.get("code") 
        if auth_code:
            access_token = fetch_new_token(auth_code)
            if not access_token:
                return {"error": "Failed to obtain access token"}
        else:
            return {"error": "Authorization required"}
    
    url = f"https://huutu.bitrix24.vn/rest/{action}"
    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.post(url, json=payload, headers=headers)
    
    if response.status_code == 401:  # Token hết hạn
        new_access_token = refresh_access_token()
        if new_access_token:
            headers["Authorization"] = f"Bearer {new_access_token}"
            response = requests.post(url, json=payload, headers=headers)
    
    return response.json()

# ----- Flask Routes -----
@app.route("/", methods=["GET", "POST"])
def index():
    if not check_access_token():  # Nếu chưa có token -> yêu cầu đăng nhập
        auth_code = request.args.get("code")
        if auth_code:
            fetch_new_token(auth_code)
        else:
            auth_url = f"https://huutu.bitrix24.vn/oauth/authorize/?client_id={BITRIX_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
            return redirect(auth_url)
    return redirect("/listCustomer")
     
@app.route("/install", methods=["POST"])
def install_app():
    data = request.form.to_dict()
    if not data:
        return jsonify({"error": "No form data received"}), 400
    print("✅ Nhận sự kiện install thành công, chuyển hướng đến giao diện chính")
    return redirect("/")

# ----- Quản lý danh sách khách hàng -----
@app.route("/listCustomer", methods=["GET", "POST"])
def listCustomer():
    contacts = call_bitrix_api("crm.contact.list", {
        "select": ["ID", "NAME", "ADDRESS", "LAST_NAME", "BIRTHDATE", "PHONE", "EMAIL", "WEB", "ADDRESS_CITY", "ADDRESS_COUNTRY"]
    })
    return render_template("index.html", contacts=contacts.get("result", [])) 

@app.route("/add_contact", methods=["POST"])
def add_contact():
    payload = {
        "FIELDS": {
            "NAME": request.form.get("name"),
            "ADDRESS": request.form.get("address"),
            "PHONE": [{"VALUE": request.form.get("phone")}],
            "EMAIL": [{"VALUE": request.form.get("email")}],
            "WEB": [{"VALUE": request.form.get("website")}],
            "ADDRESS_CITY": request.form.get("bank_name"),
            "ADDRESS_COUNTRY": request.form.get("bank_account")
        }
    }
    call_bitrix_api("crm.contact.add", payload)
    return redirect("/listCustomer")

@app.route("/update_contact/<contact_id>", methods=["POST"])
def update_contact(contact_id):
    payload = {
        "ID": contact_id,
        "FIELDS": {
            "NAME": request.form.get("name"),
            "ADDRESS": request.form.get("address"),
            "PHONE": [{"VALUE": request.form.get("phone")}],
            "EMAIL": [{"VALUE": request.form.get("email")}],
            "WEB": [{"VALUE": request.form.get("website")}],
            "ADDRESS_CITY": request.form.get("bank_name"),
            "ADDRESS_COUNTRY": request.form.get("bank_account")
        }
    }
    call_bitrix_api("crm.contact.update", payload)
    return redirect("/listCustomer")

@app.route("/delete_contact/<contact_id>", methods=["GET"])
def delete_contact(contact_id):
    call_bitrix_api("crm.contact.delete", {"ID": contact_id})
    return redirect("/listCustomer")

# ----- Chạy ứng dụng Flask -----
if __name__ == "__main__":
    threading.Thread(target=auto_refresh_token, daemon=True).start()  # Chạy luồng tự động refresh token
    app.run(port=8000, debug=True)
