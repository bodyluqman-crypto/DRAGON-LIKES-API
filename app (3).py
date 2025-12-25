from flask import Flask, jsonify
import aiohttp
import asyncio
import requests
import json
from byte import *
from protobuf_parser import Parser, Utils

app = Flask(__name__)

def fetch_tokens():
    try:
        # قراءة التوكنات من ملف accounts.json
        with open('accounts.json', 'r') as file:
            accounts_data = json.load(file)
        
        valid_jwts = []
        jwt_api_url = "https://zix-official-jwt.vercel.app/get"
        
        # أخذ أول 4 حسابات فقط
        for uid, password in list(accounts_data.items())[:4]:
            try:
                if not uid or not password:
                    print(f"⚠️ UID أو كلمة المرور فارغ للحساب {uid}")
                    continue
                
                # طلب JWT من API الخارجي
                response = requests.get(
                    f"{jwt_api_url}?uid={uid}&password={password}",
                    timeout=10
                )
                
                if response.status_code == 200:
                    jwt_data = response.json()
                    if 'token' in jwt_data:
                        valid_jwts.append(jwt_data['token'])
                        print(f"✅ تم تحويل التوكن لـ UID {uid} إلى JWT بنجاح")
                    else:
                        print(f"⚠️ لا يوجد حقل token في الاستجابة لـ UID {uid}")
                else:
                    print(f"⚠️ فشل في تحويل التوكن لـ UID {uid}. كود الاستجابة: {response.status_code}")
                    print(f"تفاصيل الخطأ: {response.text}")
            
            except Exception as e:
                print(f"⚠️ خطأ في معالجة الحساب {uid}: {str(e)}")
                continue
        
        print(f"✅ تم استخراج {len(valid_jwts)} توكنات JWT صالحة")
        return valid_jwts[:4]  # تأكد من عدم تجاوز 4 توكنات
    
    except FileNotFoundError:
        print("⚠️ ملف accounts.json غير موجود")
        return []
    except json.JSONDecodeError:
        print("⚠️ ملف accounts.json تالف أو غير صحيح")
        return []
    except Exception as e:
        print(f"⚠️ خطأ عام في جلب التوكنات: {str(e)}")
        return []

# باقي السورس يبقى كما هو بدون تغيير
async def visit(session, token, uid, data):
    url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
    headers = {
        "ReleaseVersion": "OB50",
        "X-GA": "v1 1",
        "Authorization": f"Bearer {token}",
        "Host": "clientbp.ggblueshark.com"
    }
    try:
        async with session.post(url, headers=headers, data=data, ssl=False):
            pass
    except Exception as e:
        print(f"⚠️ خطأ في إرسال الطلب: {str(e)}")

async def send_requests_concurrently(tokens, uid, num_requests=300):
    if not tokens:
        raise ValueError("لا توجد توكنات متاحة للإرسال")
    
    connector = aiohttp.TCPConnector(limit=0)
    async with aiohttp.ClientSession(connector=connector) as session:
        data = bytes.fromhex(encrypt_api("08" + Encrypt_ID(uid) + "1801"))
        tasks = [asyncio.create_task(visit(session, tokens[i % len(tokens)], uid, data)) for i in range(num_requests)]
        await asyncio.gather(*tasks)

@app.route('/visit', methods=['GET'])
def send_visits(uid):
    tokens = fetch_tokens()
    
    if not tokens:
        return jsonify({"message": "⚠️ لم يتم العثور على أي توكن صالح"}), 500
    
    print(f"✅ عدد التوكنات JWT المتاحة: {len(tokens)}")

    try:
        num_requests = 300
        asyncio.run(send_requests_concurrently(tokens, uid, num_requests))
        return jsonify({"message": f"✅ تم إرسال {num_requests} زائر إلى UID: {uid} باستخدام {len(tokens)} توكنات JWT"}), 200
    except Exception as e:
        print(f"⚠️ خطأ في إرسال الزيارات: {str(e)}")
        return jsonify({"message": f"⚠️ فشل في إرسال الزيارات: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)