from flask import Flask, request, jsonify
import httpx
import asyncio

app = Flask(__name__)
MAX_SUCCESSFUL = 20  # عدد الطلبات الناجحة المطلوب

async def send_friend_request(session, token, uid):
    url = f"https://add-friend-teal.vercel.app/add_friend?token={token}&uid={uid}"
    headers = {
        'User-Agent': 'Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)',
        'Connection': 'Keep-Alive',
        'Expect': '100-continue',
    }
    try:
        resp = await session.get(url, headers=headers, timeout=5.0)
        return token, resp.status_code == 200
    except Exception:
        return token, False

async def send_all_requests(tokens, uid):
    results = []
    requests_sent = 0
    async with httpx.AsyncClient() as session:
        tasks = [send_friend_request(session, token, uid) for token in tokens]
        for coro in asyncio.as_completed(tasks):
            token, success = await coro
            status = "success" if success else "failed"
            results.append({"token": token[:20]+"...", "status": status})
            if success:
                requests_sent += 1
            if requests_sent >= MAX_SUCCESSFUL:
                break
    return requests_sent, results

@app.route("/send_friend", methods=["GET"])
def send_friend():
    player_id = request.args.get("player_id")
    if not player_id:
        return jsonify({"error": "player_id is required"}), 400
    try:
        player_id_int = int(player_id)
    except ValueError:
        return jsonify({"error": "player_id must be an integer"}), 400

    # جلب التوكنات
    try:
        token_data = httpx.get("https://aauto-token.onrender.com/api/get_jwt", timeout=50).json()
        tokens = list(token_data.get("tokens", {}).values())
        if not tokens:
            return jsonify({"error": "No tokens found"}), 500
    except Exception as e:
        return jsonify({"error": f"Failed to fetch tokens: {e}"}), 500

    # تنفيذ asyncio داخل Flask
    requests_sent, results = asyncio.run(send_all_requests(tokens, player_id_int))

    return jsonify({
        "player_id": player_id_int,
        "friend_requests_sent": requests_sent,
        "details": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
