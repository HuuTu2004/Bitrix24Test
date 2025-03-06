from flask import Flask, request, redirect, render_template
import requests
import json
import os

app = Flask(__name__)

# Thông tin Bitrix24
BITRIX_CLIENT_ID = "local.67c83a2e30c124.97480219"
BITRIX_CLIENT_SECRET = "cKRGKUGPL5k6Fiuy2julbXQZcTbzrD0yceHmJjVLkVnPYXaQof"
REDIRECT_URI = "https://079a-222-252-92-203.ngrok-free.app"
TOKEN_FILE = "tokens.json"

# ----- TOKEN HANDLER -----
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
        return new_token_data.get("access_token")
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

# ----- CALL BITRIX API -----
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
    
    if response.status_code == 401:
        new_access_token = refresh_access_token()
        if new_access_token:
            headers["Authorization"] = f"Bearer {new_access_token}"
            response = requests.post(url, json=payload, headers=headers)
    
    return response.json()

# ----- FLASK ROUTES -----
@app.route("/", methods=["GET", "POST"])
def index():
    if not check_access_token():  # Chưa có token -> yêu cầu đăng nhập
        auth_code = request.args.get("code")
        if auth_code:
            fetch_new_token(auth_code)
        else:
            auth_url = f"https://huutu.bitrix24.vn/oauth/authorize/?client_id={BITRIX_CLIENT_ID}&response_type=code&redirect_uri={REDIRECT_URI}"
            return redirect(auth_url)
    return redirect("/listCustomer")
     
    


# Bài 2: Tạo giao diện cho phép hiển thị, thêm, sửa, xóa contact với các thông tin cơ bản dưới đây

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

if __name__ == "__main__":
    app.run(port=8000, debug=True)
