from flask import Flask, request, jsonify
import httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import time

app = Flask(__name__)
lock = threading.Lock()
MAX_SUCCESSFUL = 50  # عدد الطلبات الناجحة المطلوب

# قائمة الـUIDs التي تريد استخدامها
UIDS_TO_USE = [
    "4051888114","4051761386","4051755909","4051726294","4051703176",
    "4051676161","4051948335","4051959636","4051668708","4051664470",
    "4051653143","4051633493","4051627603","4051941566","4051910611",
    "4051903758","4051895352","4051883794","4051835259","4051829815",
    "4051823625","4051817693","4051801201","4051794437","4051783809",
    "4000977837","4050080063","4049933633","4049925045","4049916834",
    "4049904817","4049887746","4050057094","4050040245","4050033008",
    "4049998063","4049986344","4049978850","4049962763","4049943000",
    "4126767072","4144879717","4144891702","4144899334","4144906651",
    "4144921793","4144945333","4144951604","4144957818","4144963323",
    "4144997397","4145002664","4145007744","4145012714","4145018631",
    "4145030780","4146187937","4146195222","4146201924","4146208008",
    "4146215113","4146222260","4146229786","4146237641","4146244792",
    "4146252824","4146423738","4146438830","4146446085","4146452236",
    "4146459396","4146465947","4146472119","4146477703","4146484135",
    "4146491418","4146497597","4146503638","4146510285","4146516129",
    "4146523260"
]

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

    # جلب التوكنات الخاصة بالـUIDs المحددة
    try:
        token_data = httpx.get("https://aauto-token.onrender.com/api/get_jwt", timeout=50).json()
        tokens_dict = token_data.get("tokens", {})
        if not tokens_dict:
            return jsonify({"error": "No tokens found"}), 500

        # اختر فقط التوكنات للـUIDs الموجودة في القائمة
        tokens = [tokens_dict[uid] for uid in UIDS_TO_USE if uid in tokens_dict]
    except Exception as e:
        return jsonify({"error": f"Failed to fetch tokens: {e}"}), 500

    results = []
    requests_sent = 0
    token_index = 0
    total_tokens = len(tokens)

    with ThreadPoolExecutor(max_workers=50) as executor:
        futures = {}
        while requests_sent < MAX_SUCCESSFUL:
            while token_index < total_tokens and len(futures) < 20:
                token = tokens[token_index]
                token_index += 1
                futures[executor.submit(send_friend_request, token, player_id_int)] = token

            if not futures:
                break

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

            # إعادة التوكنات إذا لم نصل للعدد المطلوب
            if token_index >= total_tokens and requests_sent < MAX_SUCCESSFUL:
                token_index = 0
                time.sleep(1)

    return jsonify({
        "player_id": player_id_int,
        "friend_requests_sent": requests_sent,
        "details": results
    })

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
