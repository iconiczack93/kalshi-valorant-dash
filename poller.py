#!/usr/bin/env python3
"""Polls Kalshi public Valorant markets (+ authed portfolio when secrets exist) -> data.json"""
import json, os, time, base64, urllib.request, urllib.error, datetime

BASE = "https://api.elections.kalshi.com/trade-api/v2"
SERIES = ["KXVALORANTGAME", "KXVALORANTMAP", "KXVALORANTTOTALMAPS"]

def get(path, headers=None, tries=4):
    for i in range(tries):
        try:
            req = urllib.request.Request(BASE + path, headers={"User-Agent": "val-dash/1.0", **(headers or {})})
            return json.load(urllib.request.urlopen(req, timeout=25))
        except urllib.error.HTTPError as e:
            if e.code == 429 and i < tries - 1:
                time.sleep(2.5 * (i + 1)); continue
            raise

def f(m, k):
    v = m.get(k)
    try: return float(v) if v not in (None, "") else None
    except (TypeError, ValueError): return None

def kalshi_headers(method, path):
    key_id, pem = os.environ.get("KALSHI_KEY_ID"), os.environ.get("KALSHI_PRIVATE_KEY", "").replace("\\n", "\n")
    if not key_id or "PRIVATE KEY" not in pem: return None
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    key = serialization.load_pem_private_key(pem.encode(), password=None)
    ts = str(int(time.time() * 1000))
    sig = key.sign((ts + method + "/trade-api/v2" + path).encode(),
                   padding.PSS(mgf=padding.MGF1(hashes.SHA256()), salt_length=padding.PSS.DIGEST_LENGTH),
                   hashes.SHA256())
    return {"KALSHI-ACCESS-KEY": key_id, "KALSHI-ACCESS-TIMESTAMP": ts,
            "KALSHI-SIGNATURE" if False else "KALSHI-ACCESS-SIGNATURE": base64.b64encode(sig).decode()}

def portfolio():
    h = kalshi_headers("GET", "/portfolio/balance")
    if not h: return None
    try:
        bal = get("/portfolio/balance", h)
        pos = get("/portfolio/positions?limit=100&count_filter=position", kalshi_headers("GET", "/portfolio/positions"))
        out = {"balance_dollars": bal.get("balance", 0) / 100 if isinstance(bal.get("balance"), int) else bal.get("balance"),
               "portfolio_value": bal.get("portfolio_value"),
               "positions": [{"ticker": p.get("ticker"), "position": p.get("position"),
                              "exposure": p.get("market_exposure"), "realized": p.get("realized_pnl")}
                             for p in pos.get("market_positions", []) if p.get("position")]}
    except Exception as e:
        out = {"error": str(e)}
    pin = os.environ.get("POSITIONS_PIN")
    if not pin: return None  # never publish portfolio unencrypted to the public repo
    from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    salt, iv = os.urandom(16), os.urandom(12)
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=200000)
    ct = AESGCM(kdf.derive(pin.encode())).encrypt(iv, json.dumps(out).encode(), None)
    return {"enc": True, "salt": base64.b64encode(salt).decode(),
            "iv": base64.b64encode(iv).decode(), "data": base64.b64encode(ct).decode()}

def main():
    events = []
    for s in SERIES:
        try:
            evs = get(f"/events?series_ticker={s}&status=open&limit=100&with_nested_markets=true").get("events", [])
        except Exception as e:
            print(f"error {s}: {e}"); continue
        for e in evs:
            mkts = []
            for m in e.get("markets", []):
                bid, ask = f(m, "yes_bid_dollars"), f(m, "yes_ask_dollars")
                last = f(m, "last_price_dollars")
                mid = round((bid + ask) / 2, 4) if bid and ask and bid > 0 else (round(last, 4) if last else None)
                mkts.append({"ticker": m["ticker"], "label": m.get("title") or m["ticker"], "mid": mid,
                             "bid": bid, "ask": ask, "vol": f(m, "volume_fp"), "close": m.get("close_time", "")})
            events.append({"ticker": e["event_ticker"], "title": e.get("title", ""), "sub": e.get("sub_title", ""),
                           "series": s, "markets": mkts})
        time.sleep(1.0)
    # sparkline history
    hist = {}
    try: hist = json.load(open("history.json"))
    except Exception: pass
    now = datetime.datetime.now(datetime.timezone.utc).isoformat()
    for e in events:
        for m in e["markets"]:
            if m["mid"] is None: continue
            h = hist.setdefault(m["ticker"], [])
            if not h or h[-1][1] != m["mid"]:
                h.append([now, m["mid"]])
            hist[m["ticker"]] = h[-288:]
    json.dump(hist, open("history.json", "w"))
    data = {"ts": now, "events": events, "history": {k: [p[1] for p in v] for k, v in hist.items()},
            "portfolio": portfolio()}
    json.dump(data, open("data.json", "w"))
    print(f"wrote data.json: {len(events)} events, portfolio={'yes' if data['portfolio'] else 'no'}")

if __name__ == "__main__":
    main()
