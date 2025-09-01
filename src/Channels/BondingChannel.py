import asyncio
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from APIs import get_latest_token, get_token_information
from Rules.BondingRules import BondingRuleChecker
from handlers import send_kota
import html
import textwrap

sent_tokens = set()  # lưu token đã gửi

# ---- FORMAT MESSAGE ----
def format_message(token):
    name = html.escape(token.get('name', ''))
    symbol = html.escape(token.get('symbol', ''))
    address = html.escape(token.get('address', ''))

    price = f"{float(token.get('price_usd', 0)):,.8f}"
    marketcap = f"${float(token.get('marketcap', 0))/1000:.1f}K" if float(token.get('marketcap', 0)) > 1000 else f"${float(token.get('marketcap', 0)):.0f}"
    liquidity_val = float(token.get('liquidity', 0))
    liquidity = f"${liquidity_val/1000:.1f}K" if liquidity_val > 1000 else f"${liquidity_val:.0f}"
    base_symbol = token.get("base_symbol", "?")
    quote_symbol = token.get("quote_symbol", "?")
    liquidity_base = token.get("liquidity_base", 0)
    liquidity_quote = token.get("liquidity_quote", 0)
    
    holders = str(token.get('holders', ''))
    top10 = str(token.get('topHolderPct', ''))
    dex_link = token.get('dex_link', '')

    volume_24h = f"${float(token.get('volume_24h', 0))/1000:.1f}K" if float(token.get('volume_24h', 0)) > 1000 else f"${float(token.get('volume_24h', 0)):.0f}"
    volume_1h = f"${float(token.get('volume_1h', 0))/1000:.1f}K" if float(token.get('volume_1h', 0)) > 1000 else f"${float(token.get('volume_1h', 0)):.0f}"
    volume_buy_1h = f"${float(token.get('volume_buy_1h', 0))/1000:.1f}K" if float(token.get('volume_buy_1h', 0)) > 1000 else f"${float(token.get('volume_buy_1h', 0)):.0f}"
    volume_sell_1h = f"${float(token.get('volume_sell_1h', 0))/1000:.1f}K" if float(token.get('volume_sell_1h', 0)) > 1000 else f"${float(token.get('volume_sell_1h', 0)):.0f}"
    volume_5m = f"${float(token.get('volume_5m', 0))/1000:.1f}K" if float(token.get('volume_5m', 0)) > 1000 else f"${float(token.get('volume_5m', 0)):.0f}"
    volume_buy_5m = f"${float(token.get('volume_buy_5m', 0))/1000:.1f}K" if float(token.get('volume_buy_5m', 0)) > 1000 else f"${float(token.get('volume_buy_5m', 0)):.0f}"
    volume_sell_5m = f"${float(token.get('volume_sell_5m', 0))/1000:.1f}K" if float(token.get('volume_sell_5m', 0)) > 1000 else f"${float(token.get('volume_sell_5m', 0)):.0f}"

    transfers5m = str(token.get('transfers5m', ''))
    transfers1h = str(token.get('transfers1h', ''))

    ATH_val = float(token.get('ATH', 0))
    ATH = f"{ATH_val:,.2f}"

    pair_age = float(token.get('pair_age_hours', 0))
    pair_age_str = f"{pair_age:.2f}h" if pair_age >= 1 else f"{pair_age*60:.0f}m"

    scans = str(token.get('scans_count', 0))
    snipers_count = str(token.get('snipers', 0))
    snipers_pct = f"{float(token.get('sniper_pct', 0)):,.2f}%"
    first20_pct = f"{float(token.get('first20_pct', 0)):,.2f}%"
    fish_count = str(token.get('fish_count', 0))
    fish_pct = f"{float(token.get('fish_pct', 0)):,.2f}%"

    text = textwrap.dedent(f"""\
    ⚡ ${name} | ${symbol}

    🎯 <b>CA:</b> <code>{address}</code>

    ⏳ <b>Pool Age:</b> {pair_age_str}
    🌊 <b>Market Cap:</b> <code>{marketcap}</code> |  <b>ATH:</b> <code>{ATH}</code>
    💧 <b>Liquid:</b> <code>{liquidity}</code> ({liquidity_quote:,.2f} {quote_symbol})

    ❌ Dex Paid
    ⚡ Scans: {scans} | ❌
    👥 <b>Holders:</b> {holders} | 💪 TOP 10: {top10}%

    🔫 Snipers: {snipers_count} ｜ {snipers_pct} 🚨
    🎯 First 20: {first20_pct} ｜ {fish_count} 🐟 ｜ {fish_pct}
    🛠🌱🌱🍤🐟🐟🍤🍤🍤🍤 
    🐟🐟🐟🐟🍤🍤🐟🐟🐟🍤

    🧑‍💻 Dev: 49 SOL ｜ 0% ${symbol}
    ┣ Bundled: 10% 🤍 ｜ Sold: 10% 🔴
    ┗ Airdrop: 0% 🤍

    💵 <b>Last 5m:</b> <code>{volume_5m}</code> (B: {volume_buy_5m} / S: {volume_sell_5m}) {transfers5m} tx
    💵 <b>Last 1h:</b> <code>{volume_1h}</code> (B: {volume_buy_1h} / S: {volume_sell_1h}) {transfers1h} tx

    🚀 <b>TOTAL Volume 24h:</b> <code>{volume_24h}</code>
    """)

    return text
    
    # # Thêm rules với indent
    # text += "\n".join(f"{html.escape(rule)}" for rule in rules)

    # # Thêm link cuối cùng, luôn xuống dòng riêng
    # text += f"\n\n🔗 <a href=\"{dex_link}\">DexScreener</a>"

    # return text

async def worker(interval=300):
    global sent_tokens
    while True:
        tokens = await get_latest_token()
        if not tokens:
            print("⚠️ Không lấy được token mới.")
            await asyncio.sleep(interval)
            continue

        for token_latest in tokens:
            token_address = token_latest.get("tokenAddress")

            # bỏ qua nếu đã gửi
            if token_address in sent_tokens:
                continue  

            token_info = await get_token_information(token_address)
            if not token_info:
                print(f"⚠️ Không lấy được thông tin token: {token_address}")
                continue

            msg = format_message(token_info)
            imagePath = token_latest.get("openGraph") or token_latest.get("logoURI")

            KEYBOARD = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton("🟡 BUY NOW", url=f"https://t.me/gmgn_ai_bot"),
                    InlineKeyboardButton("💎 GEM SIGNALS", url="https://t.me/some_channel"),
                ]
            ])

            await send_kota(Caption=msg, Keyboard=KEYBOARD, imagePath=imagePath)
            print(f"✅ Sent new token: {token_address}")

            sent_tokens.add(token_address)  # đánh dấu đã gửi
            await asyncio.sleep(2)

        # chờ 5 phút rồi lặp lại
        await asyncio.sleep(interval)

    # bonding_checker = BondingRuleChecker()
    # b_score, b_results = bonding_checker.evaluate(token)
    # if b_score >= 3:
