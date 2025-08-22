from flask import Flask, request, jsonify
import httpx
import asyncio

app = Flask(__name__)

MAX_SUCCESSFUL = 50  # الحد الأقصى لعدد طلبات الصداقة

async def send_friend_request(client, token, uid):
    url = f"https://add-friend-ecru.vercel.app/add_friend?token={token}&uid={uid}"
    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
    }
    try:
        resp = await client.get(url, headers=headers, timeout=10.0)
        return token, resp.status_code == 200
    except httpx.RequestError:
        return token, False

@app.route("/send_friend", methods=["GET"])
def send_friend():
    player_id = request.args.get("player_id")

    if not player_id:
        return jsonify({"error": "player_id is required"}), 400

    try:
        player_id_int = int(player_id)
    except ValueError:
        return jsonify({"error": "player_id must be an integer"}), 400

    # جلب التوكنات من API خارجي
    try:
        token_data = httpx.get("https://auto-token-bngx.onrender.com/api/get_jwt", timeout=15).json()
        tokens_dict = token_data.get("tokens", {})
        if not tokens_dict:
            return jsonify({"error": "No tokens found"}), 500

        tokens = list(tokens_dict.values())  # قائمة التوكنات فقط
    except Exception as e:
        return jsonify({"error": f"Failed to fetch tokens: {e}"}), 500

    # الدالة async لإرسال الطلبات جميعها
    async def send_all_requests():
        results = []
        requests_sent = 0

        async with httpx.AsyncClient() as client:
            tasks = []
            for token in tokens:
                if requests_sent + len(tasks) >= MAX_SUCCESSFUL:
                    break
                tasks.append(send_friend_request(client, token, player_id_int))

            # جمع النتائج فور انتهاء كل طلب
            for future in asyncio.as_completed(tasks):
                token, success = await future
                if success:
                    requests_sent += 1
                    status = "success"
                else:
                    status = "failed"
                results.append({"token": token[:20] + "...", "status": status})

        return requests_sent, results

    # تشغيل الحدث asyncio
    requests_sent, results = asyncio.run(send_all_requests())

    return jsonify({
        "player_id": player_id_int,
        "friend_requests_sent": requests_sent,
        "details": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
