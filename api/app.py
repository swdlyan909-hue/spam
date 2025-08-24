from flask import Flask, request, jsonify
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

app = Flask(__name__)
lock = threading.Lock()
MAX_SUCCESSFUL = 100  # عدد الطلبات الناجحة المطلوب

def send_friend_request(token, uid):
    url = f"https://add-friend-teal.vercel.app/add_friend?token={token}&uid={uid}"
    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
    }
    try:
        resp = httpx.get(url, headers=headers, timeout=5.0)
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

    # جلب جميع التوكنات من API خارجي
    try:
        token_data = httpx.get("https://aauto-token.onrender.com/api/get_jwt", timeout=50).json()
        tokens_dict = token_data.get("tokens", {})
        if not tokens_dict:
            return jsonify({"error": "No tokens found"}), 500

        tokens = list(tokens_dict.values())  # قائمة التوكنات فقط
    except Exception as e:
        return jsonify({"error": f"Failed to fetch tokens: {e}"}), 500

    results = []
    requests_sent = 0
    token_index = 0
    total_tokens = len(tokens)

    with ThreadPoolExecutor(max_workers=200) as executor:
        futures = {}
        while requests_sent < MAX_SUCCESSFUL:
            # أضف المزيد من الطلبات إذا بقيت توكنات
            while token_index < total_tokens and len(futures) < 20:
                token = tokens[token_index]
                token_index += 1
                futures[executor.submit(send_friend_request, token, player_id_int)] = token

            if not futures:
                break  # لا توجد طلبات متبقية

            # انتظر انتهاء أي Future
            done, _ = as_completed(futures), futures.copy()
            for future in list(futures.keys()):
                token = futures[future]
                try:
                    success = future.result()
                except Exception:
                    success = False

                with lock:
                    if success[1]:
                        requests_sent += 1
                        status = "success"
                    else:
                        status = "failed"
                    results.append({"token": token[:20] + "...", "status": status})

                del futures[future]

                if requests_sent >= MAX_SUCCESSFUL:
                    break

            # إذا نفدت التوكنات وأي طلبات ما زالت لم تنجح، أعد المحاولة بعد قليل
            if token_index >= total_tokens and requests_sent < MAX_SUCCESSFUL:
                token_index = 0  # أعد التوكنات كلها
                time.sleep(1)   # فترة قصيرة قبل إعادة المحاولة

    return jsonify({
        "player_id": player_id_int,
        "friend_requests_sent": requests_sent,
        "details": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
