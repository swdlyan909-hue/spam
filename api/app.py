from flask import Flask, request, jsonify
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed

app = Flask(__name__)
lock = threading.Lock()
REQUESTS_TO_SEND = 20  # عدد الطلبات المراد إرسالها

def send_friend_request(token, uid):
    url = f"https://add-friend-sigma.vercel.app/add_friend?token={token}&uid={uid}"
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

    # جلب التوكنات من API
    try:
        token_data = httpx.get("https://aauto-token.onrender.com/api/get_jwt", timeout=20).json()
        tokens_dict = token_data.get("tokens", {})
        if not tokens_dict:
            return jsonify({"error": "No tokens found"}), 500

        # استخدام أول 20 توكن فقط
        tokens = list(tokens_dict.values())[:REQUESTS_TO_SEND]
    except Exception as e:
        return jsonify({"error": f"Failed to fetch tokens: {e}"}), 500

    results = []

    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = {executor.submit(send_friend_request, token, player_id_int): token for token in tokens}
        for future in as_completed(futures):
            token = futures[future]
            try:
                _, success = future.result()
            except Exception:
                success = False

            status = "success" if success else "failed"
            results.append({"token": token[:20] + "...", "status": status})

    requests_sent = sum(1 for r in results if r["status"] == "success")

    return jsonify({
        "player_id": player_id_int,
        "friend_requests_sent": requests_sent,
        "details": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
