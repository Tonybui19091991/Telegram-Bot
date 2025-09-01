import os
import requests
from dotenv import load_dotenv
from datetime import datetime, timedelta
from PIL import Image
from io import BytesIO
import base64
import time
import aiohttp

load_dotenv()

MORALIS_API_KEY = os.getenv("MORALIS_API_KEY")
MORALIS_URL = os.getenv("MORALIS_URL")
TXN_ENDPOINT = os.getenv("TXN_ENDPOINT")
SOLANA_RPC = os.getenv("SOLANA_RPC")

Headers = {
    "accept": "application/json",
    "X-API-Key": MORALIS_API_KEY
}
    
async def get_latest_token() -> dict:
    url = f"https://api.dexscreener.com/token-profiles/latest/v1"
    response = requests.get(url) 
    if response.status_code != 200:
        print(f"Error fetching latest token: {response.status_code} {response.text}")
        return None
    
    return response.json()

async def get_token_information(token_address: str) -> dict:
    url = f"https://api.dexscreener.com/latest/dex/tokens/{token_address}"
    response = requests.get(url) 
    if response.status_code != 200:
        print(f"Error fetching token information: {response.status_code} {response.text}")
        return None
    data = response.json()
    pairs = data.get("pairs", [])
    if not pairs:
        return None
    
    # chọn cặp có thanh khoản cao nhất
    main_pair = max(pairs, key=lambda x: x.get("liquidity", {}).get("usd", 0))

    #price_usd
    price_usd = float(main_pair.get("priceUsd", 0))

    # Pool age (giờ)
    created_at = main_pair.get("pairCreatedAt")
    if not created_at:
        return None
    pair_age_hours = round((time.time()*1000 - created_at) / (1000*60*60), 2)

    # Marketcap (nếu DexScreener không trả, phải tự tính)
    marketcap = main_pair.get("marketCap") or "N/A"

    # Liquidity
    base_symbol = main_pair.get("baseToken", {}).get("symbol", "?")
    quote_symbol = main_pair.get("quoteToken", {}).get("symbol", "?")

    liquidity_base = main_pair.get("liquidity", {}).get("base", 0)
    liquidity_quote = main_pair.get("liquidity", {}).get("quote", 0)
    liquidity_usd = main_pair.get("liquidity", {}).get("usd") or 0

    # Tính toán Volumes 
    volume_24h = main_pair.get("volume", {}).get("h24", 0)
    volume_1h = main_pair.get("volume", {}).get("h1", 0)
    volume_5m = main_pair.get("volume", {}).get("m5", 0)
    transfer_buy_5m = main_pair.get("txns", {}).get("m5", {}).get("buys", 0)
    transfer_sell_5m = main_pair.get("txns", {}).get("m5", {}).get("sells", 0)
    transfers5m = transfer_buy_5m + transfer_sell_5m

    transfer_buy_1h = main_pair.get("txns", {}).get("h1", {}).get("buys", 0)
    transfer_sell_1h = main_pair.get("txns", {}).get("h1", {}).get("sells", 0)
    transfers1h = transfer_buy_1h + transfer_sell_1h

    volume_buy_1h, volume_sell_1h = split_volume(volume_1h, transfer_buy_1h, transfer_sell_1h)
    volume_buy_5m, volume_sell_5m = split_volume(volume_5m, transfer_buy_5m, transfer_sell_5m)

    #  # Get holders and top holders from Moralis
    holder_response = await get_holders_info(token_address)
    if not holder_response:
        print("Error fetching holders info")
        return None
    holders_count = holder_response.get("holders_count", 0)
    top_holder_pct = holder_response.get("top_holder_pct", 0)
    
    total_supply_info = await get_token_supply(token_address)
    if not total_supply_info:
        print("Error fetching token supply info")
        return None
    total_supply = total_supply_info.get("total_supply", 1)
    token_decimals = total_supply_info.get("decimals", 9)    
    snipers_count, snipers_pct, first20_pct, fish_count, fish_pct = await analyze_snipers(token_address, total_supply, token_decimals)
    
    return {
            "name": main_pair.get("baseToken", {}).get("name"),
            "image": main_pair.get("info", {}).get("imageUrl", ""),
            "symbol": main_pair.get("baseToken", {}).get("symbol"),
            "address": main_pair.get("baseToken", {}).get("address"),
            "price_usd": price_usd,
            "marketcap": marketcap,
            "liquidity": liquidity_usd,
            "base_symbol": base_symbol,
            "quote_symbol": quote_symbol,
            "liquidity_base": liquidity_base,
            "liquidity_quote": liquidity_quote,
            "volume_24h": volume_24h,
            "volume_1h": volume_1h,
            "volume_buy_1h" : volume_buy_1h,
            "volume_sell_1h" : volume_sell_1h,
            "volume_5m": volume_5m,
            "volume_buy_5m" : volume_buy_5m,
            "volume_sell_5m" : volume_sell_5m,
            "dex_link": main_pair.get("url"),
            "holders": holders_count,
            "topHolderPct": top_holder_pct,
            "transfers5m": transfers5m,
            "transfers1h": transfers1h,
            "ATH": 9,
            "pair_age_hours": pair_age_hours,
            "scans_count": 5,
            "snipers": snipers_count,
            "sniper_pct": snipers_pct,
            "first20_pct": first20_pct,
            "fish_count": fish_count,
            "fish_pct": fish_pct
        }

async def get_holders_info(token_address):
    url = f"{MORALIS_URL}/holders/{token_address}"
    response = requests.get(url, headers=Headers)
    if response.status_code != 200:
        print(f"Error fetching holders data: {response.status_code} {response.text}")
        return None
    holders_resp = response.json()
    holders_count = holders_resp.get("totalHolders", 0)
    top_holder_pct = holders_resp.get("holderSupply", {}).get("top10", {}).get("supplyPercent", 0)
    return {
        "holders_count": holders_count,
        "top_holder_pct": top_holder_pct
    }

async def get_first_buyers(token_address: str, limit=200):
    headers = {"Content-Type": "application/json"}
    body = {
        "jsonrpc": "2.0",
        "id": "my-id",
        "method": "getSignaturesForAddress",
        "params": [token_address, {"limit": limit}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TXN_ENDPOINT, headers=headers, json=body) as resp:
            data = await resp.json()
            return data.get("result", [])


async def decode_buyer(signature: str):
    headers = {"Content-Type": "application/json"}
    body = {
        "jsonrpc": "2.0",
        "id": "tx",
        "method": "getTransaction",
        "params": [signature, {"encoding": "jsonParsed", "maxSupportedTransactionVersion": 0}]
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(TXN_ENDPOINT, headers=headers, json=body) as resp:
            data = await resp.json()
            tx = data.get("result")
            if not tx: 
                return None

            pre = tx["meta"].get("preTokenBalances", [])
            post = tx["meta"].get("postTokenBalances", [])

            buyers = []
            for p, q in zip(pre, post):
                if p["mint"] == q["mint"]:  # cùng token
                    delta = int(q["uiTokenAmount"]["amount"]) - int(p["uiTokenAmount"]["amount"])
                    if delta > 0:
                        buyers.append({
                            "owner": q["owner"],
                            "amount": delta,
                            "mint": q["mint"]
                        })
            return buyers

async def analyze_snipers(token_address: str, total_supply: float, token_decimals: int = 9):
    # Nếu total_supply = raw_amount thì chuẩn hoá
    if total_supply > 1e12:  # heuristic: số raw thường rất lớn
        total_supply = total_supply / (10 ** token_decimals)

    if total_supply <= 0:
        return 0, 0, 0, 0, 0

    signatures = await get_first_buyers(token_address, 200)
    buyers_data = []

    for sig in signatures[:50]:
        sig_str = sig["signature"]
        decoded = await decode_buyer(sig_str)
        if decoded:
            buyers_data.extend(decoded)

    # group theo buyer
    summary = {}
    for b in buyers_data:
        addr = b["owner"]
        amount = b["amount"] / (10 ** token_decimals)
        summary[addr] = summary.get(addr, 0) + amount

    buyers_list = [
        {"address": addr, "pct": (amount * 100 / total_supply)}
        for addr, amount in summary.items()
    ]
    buyers_list.sort(key=lambda x: -x["pct"])

    snipers_count = len(buyers_list)
    snipers_pct = min(100, sum(b["pct"] for b in buyers_list))

    first20 = buyers_list[:20]
    first20_pct = min(100, sum(b["pct"] for b in first20))

    fish = [b for b in first20 if b["pct"] < 1]
    fish_count = len(fish)
    fish_pct = min(100, sum(b["pct"] for b in fish))

    return snipers_count, snipers_pct, first20_pct, fish_count, fish_pct

def split_volume(volume, buys, sells, ndigits=2):
    v = float(volume or 0)
    b = int(buys or 0)
    s = int(sells or 0)
    t = b + s
    if t == 0:
        return 0.0, 0.0
    vb = round(v * b / t, ndigits)
    vs = round(v * s / t, ndigits)
    return vb, vs

async def get_token_supply(token_address: str):
    body = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "getTokenSupply",
        "params": [token_address]
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(SOLANA_RPC, json=body) as resp:
            data = await resp.json()
            try:
                result = data.get("result", {}).get("value", {})
                amount = int(result.get("amount", 0))
                decimals = result.get("decimals", 0)
                ui_amount = amount / (10 ** decimals) if decimals else amount
                return {
                    "raw_amount": amount,
                    "decimals": decimals,
                    "total_supply": ui_amount
                }
            except Exception as e:
                print("Error parsing response:", e)
                return None
