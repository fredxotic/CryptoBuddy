import os
import sys
import time
import json
import math
import csv
import random
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any

try:
    import requests
except ImportError:
    raise SystemExit("Please install requests: pip install requests")

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

# Optional sentiment libs
try:
    from textblob import TextBlob
    TEXTBLOB_AVAILABLE = True
except Exception:
    TEXTBLOB_AVAILABLE = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("CryptoBuddyProPlus")


# -----------------------------
# Personality System
# -----------------------------

class CryptoPersonality:
    """Meme-loving, friendly personality system for CryptoBuddy"""
    
    def __init__(self):
        self.user_name = None
        self.conversation_count = 0
        self.mood = "enthusiastic"  # enthusiastic, cautious, excited, professional
        
        # Personality elements
        self.greetings = [
            "Hey there! CryptoBuddy here! 🚀 Ready to find you some green and growing cryptos!",
            "WAGMI, friend! Let's explore the crypto universe together! 🌌",
            "GM! CryptoBuddy in the house! Ready to moon or get rekt? (Just kidding... mostly 😄)",
            "Hello there! Let's find you some sustainable gains! 🌱📈",
            "Ape together strong! Wait, I mean... let's make some smart crypto moves! 🦍💪"
        ]
        
        self.farewells = [
            "LFG! Remember: DYOR and don't invest your lambo money! 🚗💨",
            "Catch you on the flip side! May your portfolio be green! 📈💚",
            "GM! (Goodbye for now!) Stay based and don't FOMO too hard! 🎯",
            "Peace out! Remember: time in the market > timing the market! ⏰",
            "Adios! Don't do anything I wouldn't do... which isn't much in crypto! 😅"
        ]
        
        self.positive_reactions = [
            "Based! 📈",
            "This is the way! 🙌",
            "Bullish on this! 🐂",
            "Absolute gem! 💎",
            "Moon potential! 🌕",
            "GM! This looks solid! ☀️"
        ]
        
        self.cautious_reactions = [
            "NGMI if you're not careful with this one... ⚠️",
            "Might want to check the charts on this, fren 📉",
            "Do your own research, this could be risky! 🔍",
            "Not financial advice, but maybe sleep on this one 😴",
            "Paper hands beware! 🧻✋"
        ]
        
        self.encouragements = [
            "You've got this! 💪",
            "Trust the process! 🎯",
            "WAGMI! (We're All Gonna Make It) 🌟",
            "Stay based! 🏄‍♂️",
            "Keep stacking those sats! ₿"
        ]
        
        self.meme_references = [
            " to the moon! 🌕",
            " when lambo? 🚗",
            " wen moon? 🌙",
            " diamond hands! 💎✋",
            " HODL! 🚀"
        ]

    def get_greeting(self) -> str:
        """Return a personalized greeting"""
        self.conversation_count += 1
        greeting = random.choice(self.greetings)
        if self.user_name:
            return f"Hey {self.user_name}! {greeting}"
        return greeting

    def get_farewell(self) -> str:
        """Return a personalized farewell"""
        farewell = random.choice(self.farewells)
        if self.user_name:
            return f"Later {self.user_name}! {farewell}"
        return farewell

    def react_to_positive_data(self, coin_name: str, change_24h: float) -> str:
        """React to positive price movement"""
        if change_24h > 10:
            return f"🚀 {coin_name} is pumping! {random.choice(self.positive_reactions)}"
        elif change_24h > 5:
            return f"📈 {coin_name} looking strong! {random.choice(self.encouragements)}"
        else:
            return f"✅ {coin_name} in the green! {random.choice(self.positive_reactions)}"

    def react_to_negative_data(self, coin_name: str, change_24h: float) -> str:
        """React to negative price movement"""
        if change_24h < -10:
            return f"📉 {coin_name} taking a hit! {random.choice(self.cautious_reactions)}"
        elif change_24h < -5:
            return f"⚠️  {coin_name} feeling bearish! {random.choice(self.cautious_reactions)}"
        else:
            return f"🔻 {coin_name} slightly down! {random.choice(self.encouragements)}"

    def add_meme_comment(self, text: str) -> str:
        """Add a meme comment to any message (25% chance)"""
        if random.random() < 0.25:
            return text + random.choice(self.meme_references)
        return text

    def get_sustainability_praise(self, score: float) -> str:
        """Praise sustainable coins"""
        if score >= 0.8:
            return "🌱 Super eco-friendly! Mother Earth approves! 🌍"
        elif score >= 0.6:
            return "✅ Pretty green! Good for the planet! 🌿"
        else:
            return "⚡ Energy intensive... but maybe still based? 🤔"

    def get_risk_comment(self, risk: float) -> str:
        """Comment on risk levels"""
        if risk <= 0.3:
            return "🟢 Low risk! Probably won't get rekt! 😎"
        elif risk <= 0.6:
            return "🟡 Medium risk! Could go either way! 🎲"
        else:
            return "🔴 High risk! Diamond hands required! 💎✋"


# -----------------------------
# Utility functions
# -----------------------------

def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def format_currency(amount: float) -> str:
    if amount is None:
        return "N/A"
    if amount >= 1e12:
        return f"${amount/1e12:.2f}T"
    if amount >= 1e9:
        return f"${amount/1e9:.2f}B"
    if amount >= 1e6:
        return f"${amount/1e6:.2f}M"
    return f"${amount:,.2f}"


# -----------------------------
# Data client (CoinGecko)
# -----------------------------

class DataClient:
    """Simple CoinGecko client with caching and retry/backoff.

    Methods provided are minimal and tailored to the application's needs but can be
    extended. This uses the free CoinGecko endpoints and does not require an API key.
    """

    BASE = "https://api.coingecko.com/api/v3"

    def __init__(self, session: Optional[requests.Session] = None, cache_ttl: int = 60):
        self.session = session or requests.Session()
        self.user_agent = "CryptoBuddyProPlus/3.0 (+https://example.local)"
        self.session.headers.update({"User-Agent": self.user_agent})
        self.cache_ttl = cache_ttl
        self._cache: Dict[str, Tuple[float, Any]] = {}

    def _get(self, path: str, params: Optional[dict] = None, ttl: Optional[int] = None) -> Any:
        url = f"{self.BASE}{path}"
        cache_key = url + (json.dumps(params, sort_keys=True) if params else "")
        now = time.time()
        ttl = ttl if ttl is not None else self.cache_ttl

        # Return cached
        if cache_key in self._cache:
            ts, val = self._cache[cache_key]
            if now - ts < ttl:
                return val

        # Simple retry with exponential backoff
        backoff = 0.5
        for attempt in range(5):
            try:
                resp = self.session.get(url, params=params, timeout=10)
                if resp.status_code == 200:
                    data = resp.json()
                    self._cache[cache_key] = (now, data)
                    return data

                # Handle rate-limiting / 429 gracefully
                if resp.status_code == 429:
                    wait = int(resp.headers.get("Retry-After", 5))
                    logger.warning("Rate limited by CoinGecko, sleeping %s seconds", wait)
                    time.sleep(wait)
                else:
                    logger.debug("Unexpected status code %s for %s", resp.status_code, url)
            except requests.RequestException as e:
                logger.debug("Request exception: %s", e)
            time.sleep(backoff)
            backoff *= 2

        raise RuntimeError(f"Failed to GET {url} after retries")

    # Coin listing and resolution
    def coins_list(self) -> List[Dict[str, Any]]:
        """Return the list of all coins (id, symbol, name).

        This is cached for a configurable TTL.
        """
        return self._get("/coins/list", ttl=3600)

    def coin_market(self, coin_id: str, vs_currency: str = "usd") -> dict:
        """Get market data for a coin (market endpoint)

        Uses /coins/{id}?market_data=true which returns a wide set of fields.
        """
        params = {
            "localization": "false",
            "tickers": "false",
            "market_data": "true",
            "community_data": "false",
            "developer_data": "false",
            "sparkline": "false",
        }
        return self._get(f"/coins/{coin_id}", params=params)

    def simple_price(self, ids: str, vs_currencies: str = "usd") -> dict:
        params = {
            "ids": ids,
            "vs_currencies": vs_currencies,
            "include_24hr_change": "true",
            "include_market_cap": "true",
            "include_24hr_vol": "true",
        }
        return self._get("/simple/price", params=params)


# -----------------------------
# Helpers: symbol/id resolution
# -----------------------------

class CoinRegistry:
    """Resolve between symbol (e.g. BTC) and CoinGecko id (e.g. bitcoin).

    Downloads coin list once and provides lookups. Case-insensitive and supports
    best-effort fuzzy match if exact symbol not found.
    """

    def __init__(self, client: DataClient):
        self.client = client
        self._by_symbol: Dict[str, List[Dict[str, Any]]] = {}
        self._by_id: Dict[str, Dict[str, Any]] = {}
        self.refresh()

    def refresh(self):
        coins = self.client.coins_list()
        self._by_symbol.clear()
        self._by_id.clear()
        for c in coins:
            sym = c.get("symbol", "").lower()
            cid = c.get("id")
            if not sym or not cid:
                continue
            self._by_symbol.setdefault(sym, []).append(c)
            self._by_id[cid] = c

    def find_id(self, query: str) -> Optional[str]:
        """Return a best-effort coin id for a given query (symbol or id or name).

        Examples: 'btc' -> 'bitcoin', 'bitcoin' -> 'bitcoin', 'ethereum' -> 'ethereum'
        """
        q = query.strip().lower()
        # exact id
        if q in self._by_id:
            return q
        # exact symbol
        if q in self._by_symbol and len(self._by_symbol[q]) == 1:
            return self._by_symbol[q][0]["id"]
        # multiple symbols with same symbol (rare) -> prefer common names
        if q in self._by_symbol:
            # heuristics: prefer id that matches symbol+"(token)" etc. Just return first.
            return self._by_symbol[q][0]["id"]
        # fallback: try to find by name substring
        for cid, meta in self._by_id.items():
            if q == meta.get("name", "").lower():
                return cid
        for cid, meta in self._by_id.items():
            if q in meta.get("name", "").lower():
                return cid
        return None


# -----------------------------
# Analysis utilities
# -----------------------------

def heuristic_sustainability(coin_market_data: dict) -> float:
    """Compute a heuristic sustainability score in range 0..1.

    Approach:
    - If coin has 'hashing_algorithm' or mentions 'proof-of-work' -> lower score
    - If community/dev or consensus fields include 'proof of stake' or 'pos' -> higher score
    - Use length-of-name / presence of 'foundation' as weak signals

    This is a heuristic only and should be labeled as such in UI.
    """
    text_fields = []
    try:
        if coin_market_data is None:
            return 0.5
        desc = coin_market_data.get("description", {}).get("en", "") or ""
        platforms = coin_market_data.get("platforms", {}) or {}
        hashing = coin_market_data.get("hashing_algorithm")
        if hashing:
            # presence of hashing algorithm == likely PoW
            return 0.2
        lc = (desc + " ").lower()
        if "proof-of-stake" in lc or "proof of stake" in lc or "pos" in lc:
            return 0.8
        if "proof-of-work" in lc or "proof of work" in lc or "pow" in lc:
            return 0.2
        # developer or governance signals
        if "foundation" in lc or "non-profit" in lc:
            return 0.75
    except Exception:
        pass
    return 0.5


def compute_risk_score(coin_market_data: dict) -> float:
    """Compute a risk score: higher means more risky (0..1).

    - Volatility: 24h change magnitude
    - Market cap: smaller market cap -> more risky
    - Liquidity: volume relative to market cap
    """
    try:
        market = coin_market_data.get("market_data", {})
        price_change = safe_float(market.get("price_change_percentage_24h", 0))
        market_cap = safe_float(market.get("market_cap", {}).get("usd", 0))
        vol = safe_float(market.get("total_volume", {}).get("usd", 0))

        vol_ratio = (vol / market_cap) if market_cap > 0 else 1.0
        vol_score = min(1.0, abs(price_change) / 20.0)  # 20% -> 1.0
        cap_score = 1.0 - (math.tanh(math.log1p(market_cap) / 20.0))  # larger cap -> lower risk
        liquidity_score = 1.0 - math.tanh(vol_ratio * 10)

        # combine
        score = 0.5 * vol_score + 0.3 * cap_score + 0.2 * liquidity_score
        return max(0.0, min(1.0, score))
    except Exception:
        return 0.7


def sentiment_score(text: str) -> float:
    """Return sentiment polarity in [-1,1]. Use TextBlob if available, else deterministic fallback."""
    if not text:
        return 0.0
    if TEXTBLOB_AVAILABLE:
        try:
            tb = TextBlob(text)
            return max(-1.0, min(1.0, tb.sentiment.polarity))
        except Exception:
            pass
    # fallback: keyword based
    strong_positive = ['excellent', 'amazing', 'perfect', 'bullish', 'moon', 'profit', 'growth']
    positive = ['good', 'great', 'nice', 'positive', 'up', 'gain']
    negative = ['bad', 'poor', 'negative', 'down', 'loss']
    strong_negative = ['terrible', 'awful', 'crash', 'bearish', 'scam', 'rugpull']
    txt = text.lower()
    score = 0.0
    for w in strong_positive:
        if w in txt:
            score += 0.6
    for w in positive:
        if w in txt:
            score += 0.3
    for w in strong_negative:
        if w in txt:
            score -= 0.6
    for w in negative:
        if w in txt:
            score -= 0.3
    return max(-1.0, min(1.0, score))


# -----------------------------
# Main Advisor class
# -----------------------------

class CryptoAdvisor:
    """Main facade for providing recommendations and utilities.

    Responsibilities:
    - Resolve coin ids from user input
    - Fetch market data
    - Compute sustainability/risk scores
    - Provide comparison, ranking, portfolio reports
    """

    def __init__(self, client: Optional[DataClient] = None):
        self.client = client or DataClient()
        self.registry = CoinRegistry(self.client)
        self.personality = CryptoPersonality()
        self.watchlist: List[str] = []  # store coin ids
        self.portfolio: Dict[str, float] = {}  # coin_id -> holdings (in coin units)

    def resolve(self, symbol_or_id: str) -> Optional[str]:
        return self.registry.find_id(symbol_or_id)

    def fetch_market(self, coin_id: str) -> Optional[dict]:
        try:
            return self.client.coin_market(coin_id)
        except Exception as e:
            logger.warning("Failed to fetch market for %s: %s", coin_id, e)
            return None

    def summarize_coin(self, query: str) -> str:
        cid = self.resolve(query)
        if not cid:
            return f"❌ Oops! Couldn't find '{query}' in the crypto verse! Maybe it's a shitcoin? 🤔"
        
        data = self.fetch_market(cid)
        if not data:
            return f"😅 Yikes! Couldn't fetch data for {cid}. Maybe check your connection?"

        md = data.get("market_data", {})
        price = safe_float(md.get("current_price", {}).get("usd", 0))
        change_24h = safe_float(md.get("price_change_percentage_24h", 0))
        mcap = safe_float(md.get("market_cap", {}).get("usd", 0))
        vol = safe_float(md.get("total_volume", {}).get("usd", 0))
        sustain = heuristic_sustainability(data)
        risk = compute_risk_score(data)

        # Personality reactions
        price_reaction = ""
        if change_24h > 0:
            price_reaction = self.personality.react_to_positive_data(data.get('name', cid), change_24h)
        elif change_24h < 0:
            price_reaction = self.personality.react_to_negative_data(data.get('name', cid), change_24h)

        out = []
        out.append(f"⛏️  **{data.get('name', cid)} ({data.get('symbol','').upper()})** - Let's dig in!")
        out.append("")
        out.append(f"💰 **Price**: {format_currency(price)} | 24h: {change_24h:+.2f}%")
        out.append(f"   {price_reaction}")
        out.append("")
        out.append(f"📊 **Market Cap**: {format_currency(mcap)}")
        out.append(f"📈 **24h Volume**: {format_currency(vol)}")
        out.append("")
        out.append(f"🌱 **Sustainability**: {sustain*100:.0f}%")
        out.append(f"   {self.personality.get_sustainability_praise(sustain)}")
        out.append("")
        out.append(f"⚡ **Risk Score**: {risk:.2f}/1.0")
        out.append(f"   {self.personality.get_risk_comment(risk)}")
        
        desc = data.get("description", {}).get("en", "").strip()
        if desc:
            short = (desc[:300] + '...') if len(desc) > 300 else desc
            out.append("")
            out.append(f"📖 **Description**: {short}")
        
        out.append("")
        out.append("⚠️  **Remember**: Not financial advice! DYOR! 📚")
        
        return "\n".join(out)

    def compare(self, a: str, b: str) -> str:
        ida = self.resolve(a)
        idb = self.resolve(b)
        if not ida or not idb:
            return "❌ Couldn't resolve one or both coins, fren! Check those tickers! 🔍"

        da = self.fetch_market(ida)
        db = self.fetch_market(idb)
        if not da or not db:
            return "😅 Oops! Couldn't fetch data for one or both coins. API might be sleeping! 😴"

        ma = da.get('market_data', {})
        mb = db.get('market_data', {})
        pa = safe_float(ma.get('current_price', {}).get('usd', 0))
        pb = safe_float(mb.get('current_price', {}).get('usd', 0))
        ca = safe_float(ma.get('price_change_percentage_24h', 0))
        cb = safe_float(mb.get('price_change_percentage_24h', 0))
        mca = safe_float(ma.get('market_cap', {}).get('usd', 0))
        mcb = safe_float(mb.get('market_cap', {}).get('usd', 0))
        sa = heuristic_sustainability(da)
        sb = heuristic_sustainability(db)
        ra = compute_risk_score(da)
        rb = compute_risk_score(db)

        # Determine winner with personality
        winner = ""
        if sa > sb and ra < rb:
            winner = f"🏆 {da.get('name')} looking more based overall! 🌟"
        elif sb > sa and rb < ra:
            winner = f"🏆 {db.get('name')} might be the play! 🎯"
        else:
            winner = "🤷 It's a tough call! Both have their strengths! ⚖️"

        lines = [f"🔎 **Battle of the Coins**: {da.get('name')} vs {db.get('name')}"]
        lines.append("")
        lines.append(f"💰 **Price Fight**:")
        lines.append(f"   {da.get('symbol','').upper()}: {format_currency(pa)} ({ca:+.2f}%)")
        lines.append(f"   {db.get('symbol','').upper()}: {format_currency(pb)} ({cb:+.2f}%)")
        lines.append("")
        lines.append(f"📊 **Market Power**:")
        lines.append(f"   {da.get('symbol','').upper()}: {format_currency(mca)}")
        lines.append(f"   {db.get('symbol','').upper()}: {format_currency(mcb)}")
        lines.append("")
        lines.append(f"🌱 **Eco Battle**:")
        lines.append(f"   {da.get('symbol','').upper()}: {sa*100:.0f}% - {self.personality.get_sustainability_praise(sa)}")
        lines.append(f"   {db.get('symbol','').upper()}: {sb*100:.0f}% - {self.personality.get_sustainability_praise(sb)}")
        lines.append("")
        lines.append(f"⚡ **Risk Check**:")
        lines.append(f"   {da.get('symbol','').upper()}: {ra:.2f} - {self.personality.get_risk_comment(ra)}")
        lines.append(f"   {db.get('symbol','').upper()}: {rb:.2f} - {self.personality.get_risk_comment(rb)}")
        lines.append("")
        lines.append(winner)
        lines.append("")
        lines.append("🎯 **Remember**: This ain't financial advice! Do your own research! 📚")

        return "\n".join(lines)

    def rank_coins(self, queries: List[str]) -> str:
        """Rank a list of coins with personality"""
        if not queries:
            return "🤔 You gotta give me some coins to rank, fren! Try 'rank btc eth ada'"

        resolved = []
        for q in queries:
            cid = self.resolve(q)
            if cid:
                resolved.append(cid)
        
        if not resolved:
            return "❌ Couldn't find any of those coins! Maybe they're too based for CoinGecko? 😅"

        results = []
        iterator = resolved
        if TQDM_AVAILABLE:
            iterator = tqdm(resolved, desc="🔄 Crunching numbers")
        
        for cid in iterator:
            d = self.fetch_market(cid)
            if not d:
                continue
            md = d.get('market_data', {})
            price = safe_float(md.get('current_price', {}).get('usd', 0))
            change = safe_float(md.get('price_change_percentage_24h', 0))
            mcap = safe_float(md.get('market_cap', {}).get('usd', 0))
            sustain = heuristic_sustainability(d)
            risk = compute_risk_score(d)
            # combined score: favor sustainability and positive momentum, penalize risk
            combined = sustain * 0.4 + (max(-10, change) / 100.0) * 0.3 - risk * 0.3
            results.append({
                'id': cid,
                'symbol': d.get('symbol','').upper(),
                'name': d.get('name',''),
                'price': price,
                'change_24h': change,
                'market_cap': mcap,
                'sustainability': sustain,
                'risk': risk,
                'combined_score': combined,
            })

        if not results:
            return "😅 Well this is awkward... couldn't fetch data for any of those coins! 📡"

        results.sort(key=lambda x: x['combined_score'], reverse=True)
        
        # Build response with personality
        lines = [f"🏆 **Crypto Rankings** - From based to rekt potential:"]
        lines.append("")
        
        for i, r in enumerate(results[:10], 1):  # Top 10 only
            medal = ""
            if i == 1:
                medal = "🥇 "
            elif i == 2:
                medal = "🥈 "
            elif i == 3:
                medal = "🥉 "
            
            trend = "🚀" if r['change_24h'] > 5 else "📈" if r['change_24h'] > 0 else "📉" if r['change_24h'] < 0 else "➡️"
            risk_emoji = "🟢" if r['risk'] <= 0.3 else "🟡" if r['risk'] <= 0.6 else "🔴"
            sustain_emoji = "🌍" if r['sustainability'] >= 0.8 else "🌱" if r['sustainability'] >= 0.6 else "⚡"
            
            lines.append(f"{medal}{i}. **{r['symbol']}** - {r['name']}")
            lines.append(f"   Score: {r['combined_score']:.3f} | Price: {format_currency(r['price'])} {trend}")
            lines.append(f"   Risk: {risk_emoji} {r['risk']:.2f} | Sustain: {sustain_emoji} {r['sustainability']:.2f}")
            lines.append("")

        lines.append("💎 **Pro tip**: High sustainability + low risk = Probably won't get rekt! 😎")
        lines.append("⚠️  **Disclaimer**: This is for fun! Always DYOR! 📚")
        
        return "\n".join(lines)

    # Portfolio / watchlist utilities with personality
    def add_watch(self, query: str) -> str:
        cid = self.resolve(query)
        if not cid:
            return f"❌ Couldn't find '{query}' in the crypto jungle! 🌴"
        if cid in self.watchlist:
            return f"👀 Already watching {cid}! You must really like this one! ❤️"
        self.watchlist.append(cid)
        return f"✅ Added {cid} to watchlist! I'll keep an eye on it! 👁️"

    def remove_watch(self, query: str) -> str:
        cid = self.resolve(query)
        if not cid or cid not in self.watchlist:
            return f"🤷 {query} wasn't in the watchlist! Maybe it rugged? 😅"
        self.watchlist.remove(cid)
        return f"🗑️  Removed {cid} from watchlist! Out of sight, out of mind! ✨"

    def show_watchlist(self) -> str:
        if not self.watchlist:
            return "📝 Watchlist is empty! Add some coins to watch, fren! 🎯"
        
        lines = ["📌 **Your Watchlist** - Coins you're probably emotionally attached to:"]
        lines.append("")
        
        for cid in self.watchlist:
            d = self.fetch_market(cid)
            if not d:
                lines.append(f"❌ {cid}: API said no! Maybe it's sleeping? 😴")
                continue
            
            md = d.get('market_data', {})
            price = safe_float(md.get('current_price', {}).get('usd', 0))
            change = safe_float(md.get('price_change_percentage_24h', 0))
            
            # Add emotional commentary based on performance
            emotion = "😊" if change > 5 else "🙂" if change > 0 else "😐" if change > -5 else "😟"
            trend = "🚀" if change > 10 else "📈" if change > 0 else "📉" if change < 0 else "➡️"
            
            lines.append(f"{emotion} **{d.get('name')}** ({d.get('symbol','').upper()}): {format_currency(price)} {trend} ({change:+.2f}%)")
        
        lines.append("")
        lines.append("💭 **Remember**: Don't fall in love with your bags! Stay rational! 🧠")
        
        return "\n".join(lines)

    # Simple alerts with personality
    def poll_alerts(self, checks: List[Tuple[str, float, str]], interval: int = 30, rounds: int = 5):
        """Poll a set of alerts with personality"""
        resolved_checks = []
        for q, tgt, direction in checks:
            cid = self.resolve(q)
            if cid:
                resolved_checks.append((cid, tgt, direction))

        if not resolved_checks:
            print("❌ No valid coins found for alerts! Check those tickers! 🔍")
            return

        print(f"🔔 Starting alert watch! I'll check {len(resolved_checks)} coins for {rounds} rounds...")
        
        for r in range(rounds):
            print(f"🔄 Round {r+1}/{rounds}...")
            for cid, tgt, direction in resolved_checks:
                d = self.fetch_market(cid)
                if not d:
                    continue
                price = safe_float(d.get('market_data', {}).get('current_price', {}).get('usd', 0))
                name = d.get('name')
                if (direction == 'above' and price >= tgt) or (direction == 'below' and price <= tgt):
                    if direction == 'above':
                        print(f"🚀 ALERT: {name} pumped to {price}! Target {tgt} reached! TO THE MOON! 🌕")
                    else:
                        print(f"📉 ALERT: {name} dipped to {price}! Target {tgt} hit! Buying opportunity? 🛒")
            if r < rounds - 1:  # Don't sleep after last round
                time.sleep(interval)
        
        print("✅ Alert watch complete! Hope you made some gains! 💰")

    # Export portfolio/watchlist to CSV
    def export_watchlist_csv(self, path: str) -> str:
        if not self.watchlist:
            return "❌ Watchlist is empty! Nothing to export but regrets! 😅"
            
        rows = []
        for cid in self.watchlist:
            d = self.fetch_market(cid)
            if not d:
                continue
            md = d.get('market_data', {})
            rows.append({
                'id': cid,
                'symbol': d.get('symbol','').upper(),
                'name': d.get('name',''),
                'price_usd': safe_float(md.get('current_price', {}).get('usd', 0)),
                'change_24h_pct': safe_float(md.get('price_change_percentage_24h', 0)),
                'market_cap_usd': safe_float(md.get('market_cap', {}).get('usd', 0)),
            })
        
        if not rows:
            return "❌ Couldn't fetch any data for export! API might be rekt! 📡"
            
        keys = ['id','symbol','name','price_usd','change_24h_pct','market_cap_usd']
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        
        return f"✅ Watchlist exported to {path}! Your portfolio is now officially organized! 📊"

    # Assignment-specific methods
    def get_profitability_recommendations(self) -> str:
        """Assignment-style profitability recommendation with personality"""
        coins = self.rank_coins_internal(['bitcoin', 'ethereum', 'cardano', 'solana', 'polkadot'])
        profitable = [c for c in coins if c['change_24h'] > 0]
        
        if profitable:
            response = ["📈 **Based Profit Picks** - These are looking green! 💚", ""]
            for coin in profitable[:3]:
                trend = "🚀 rising" if coin['change_24h'] > 5 else "📈 rising" if coin['change_24h'] > 2 else "↗️ stable"
                response.append(f"• **{coin['name']}**: {trend} trend, {format_currency(coin['market_cap'])} market cap")
            response.append("")
            response.append("🎯 **CryptoBuddy says**: Invest in these for potential gains! 🌕")
            response.append("⚠️  **But remember**: Crypto is risky—always do your own research! 📚")
            return "\n".join(response)
        return "😴 No highly profitable cryptocurrencies found right now. Market might be sleeping! 💤"

    def get_sustainability_recommendations(self) -> str:
        """Assignment-style sustainability recommendation with personality"""
        coins = self.rank_coins_internal(['bitcoin', 'ethereum', 'cardano', 'solana', 'polkadot', 'stellar'])
        sustainable = [c for c in coins if c['sustainability'] >= 0.6]
        
        if sustainable:
            response = ["🌱 **Eco-Friendly Champions** - Good for your portfolio AND the planet! 🌍", ""]
            for coin in sustainable[:3]:
                score_percent = int(coin['sustainability'] * 100)
                earth_emoji = "🌍" if score_percent >= 80 else "🌱" if score_percent >= 60 else "✅"
                response.append(f"• **{coin['name']}**: {score_percent}% sustainability {earth_emoji}")
            response.append("")
            response.append("🎯 **CryptoBuddy says**: These coins are eco-friendly and have long-term potential! ✨")
            response.append("⚠️  **But remember**: Crypto is risky—always do your own research! 📚")
            return "\n".join(response)
        return "🌵 No highly sustainable cryptocurrencies found. Maybe stick to trees? 🌳"

    def rank_coins_internal(self, queries: List[str]) -> List[dict]:
        """Internal method for ranking without personality formatting"""
        resolved = []
        for q in queries:
            cid = self.resolve(q)
            if cid:
                resolved.append(cid)
        results = []
        for cid in resolved:
            d = self.fetch_market(cid)
            if not d:
                continue
            md = d.get('market_data', {})
            price = safe_float(md.get('current_price', {}).get('usd', 0))
            change = safe_float(md.get('price_change_percentage_24h', 0))
            mcap = safe_float(md.get('market_cap', {}).get('usd', 0))
            sustain = heuristic_sustainability(d)
            risk = compute_risk_score(d)
            combined = sustain * 0.4 + (max(-10, change) / 100.0) * 0.3 - risk * 0.3
            results.append({
                'id': cid,
                'symbol': d.get('symbol','').upper(),
                'name': d.get('name',''),
                'price': price,
                'change_24h': change,
                'market_cap': mcap,
                'sustainability': sustain,
                'risk': risk,
                'combined_score': combined,
            })
        results.sort(key=lambda x: x['combined_score'], reverse=True)
        return results


# -----------------------------
# CLI / Interactive with Personality
# -----------------------------

def interactive_mode(advisor: CryptoAdvisor):
    print(f"\n{advisor.personality.get_greeting()}")
    print("\n" + "="*60)
    print("🤖 CRYPTOBUDDY PRO+ v3 - Your Based Crypto Companion! 🚀")
    print("="*60)
    
    # Get user name for personalization
    user_input = input("\n🤖 What's your name, fren? (press Enter to stay anonymous): ").strip()
    if user_input:
        advisor.personality.user_name = user_input
        print(f"🤖 Nice to meet you, {user_input}! Let's find some alpha! 🎯")

    print("\n📋 **Quick Start Guide**:")
    print("• 'profit' - Get profitable coin recommendations")
    print("• 'sustainable' - Find eco-friendly cryptos") 
    print("• 'summary btc' - Get detailed info on Bitcoin")
    print("• 'compare btc eth' - Compare two coins")
    print("• 'watch add sol' - Add Solana to watchlist")
    print("• 'rank btc eth ada' - Rank multiple coins")
    print("• 'help' - See all commands")
    print("• 'quit' - Exit (nooo! 😢)")
    print("\n" + "="*60)

    while True:
        try:
            cmd = input("\n💬 ").strip()
            if not cmd:
                continue
                
            cmd_lower = cmd.lower()
            
            # Handle greetings
            if any(word in cmd_lower for word in ['hello', 'hi', 'hey', 'gm', 'greetings']):
                print(f"🤖 {advisor.personality.get_greeting()}")
                continue
                
            # Handle thanks
            if any(word in cmd_lower for word in ['thanks', 'thank you', 'ty']):
                print(f"🤖 You're welcome! {random.choice(advisor.personality.encouragements)}")
                continue

            if cmd_lower in ('quit', 'exit', 'bye'):
                print(f"🤖 {advisor.personality.get_farewell()}")
                break
                
            if cmd_lower == 'help':
                print("""
🎮 **Commands**:

💰 **Analysis**:
  profit                    - Based profit recommendations
  sustainable               - Eco-friendly coin picks  
  summary <coin>            - Detailed coin analysis
  compare <coin1> <coin2>   - Head-to-head comparison
  rank <coin1> <coin2> ...  - Rank multiple coins

📊 **Portfolio Tools**:
  watch add <coin>          - Add coin to watchlist
  watch remove <coin>       - Remove from watchlist  
  watch show                - Show your watchlist
  export watch <filename>   - Export watchlist to CSV

🔔 **Alerts**:
  alerts <coin> <price> <above|below> - Price alert example

🎯 **Fun Stuff**:
  hello/gm                  - Greet your based buddy
  thanks                    - Show appreciation

💡 **Pro Tips**:
• Use coin symbols (BTC) or names (bitcoin)
• I support ANY coin on CoinGecko! 
• Always DYOR - I'm just a friendly bot! 🤖

⚠️  **Disclaimer**: This is for educational purposes only! Not financial advice!
                """)
                continue
                
            parts = cmd.split()
            if not parts:
                continue

            if parts[0].lower() == 'profit':
                print(f"🤖 {advisor.get_profitability_recommendations()}")
                continue
                
            if parts[0].lower() == 'sustainable':
                print(f"🤖 {advisor.get_sustainability_recommendations()}")
                continue

            if parts[0].lower() == 'price' and len(parts) >= 2:
                cid = advisor.resolve(parts[1])
                if not cid:
                    print("🤖 ❌ Coin not found! Maybe it's too based for this universe? 🌌")
                    continue
                d = advisor.fetch_market(cid)
                if not d:
                    print("🤖 ❌ Couldn't fetch data! API might be taking a coffee break! ☕")
                    continue
                p = safe_float(d.get('market_data', {}).get('current_price',{}).get('usd',0))
                change = safe_float(d.get('market_data', {}).get('price_change_percentage_24h',0))
                trend = "🚀" if change > 5 else "📈" if change > 0 else "📉" if change < 0 else "➡️"
                print(f"🤖 💰 {d.get('name')} ({d.get('symbol','').upper()}): {format_currency(p)} {trend} ({change:+.2f}%)")
                continue
                
            if parts[0].lower() == 'summary' and len(parts) >= 2:
                print(f"🤖 {advisor.summarize_coin(parts[1])}")
                continue
                
            if parts[0].lower() == 'compare' and len(parts) >= 3:
                print(f"🤖 {advisor.compare(parts[1], parts[2])}")
                continue
                
            if parts[0].lower() == 'watch' and len(parts) >= 2:
                if parts[1].lower() == 'add' and len(parts) >= 3:
                    print(f"🤖 {advisor.add_watch(parts[2])}")
                    continue
                if parts[1].lower() in ['rm', 'remove', 'delete'] and len(parts) >= 3:
                    print(f"🤖 {advisor.remove_watch(parts[2])}")
                    continue
                if parts[1].lower() == 'show':
                    print(f"🤖 {advisor.show_watchlist()}")
                    continue
                    
            if parts[0].lower() == 'rank' and len(parts) >= 2:
                print(f"🤖 {advisor.rank_coins(parts[1:])}")
                continue
                
            if parts[0].lower() == 'export' and len(parts) >= 3 and parts[1].lower() == 'watch':
                path = advisor.export_watchlist_csv(parts[2])
                print(f"🤖 {path}")
                continue
                
            if parts[0].lower() == 'alerts' and len(parts) >= 4:
                sym = parts[1]
                price = safe_float(parts[2])
                direction = parts[3].lower()
                if direction not in ['above', 'below']:
                    print("🤖 ❌ Direction must be 'above' or 'below', fren! 📝")
                    continue
                print("🤖 🚀 Starting alerts (this will run for 3 checks)...")
                advisor.poll_alerts([(sym, price, direction)], interval=10, rounds=3)
                continue
                
            print("🤖 ❌ Command not recognized, fren! Type 'help' for based guidance! 📚")

        except KeyboardInterrupt:
            print(f"\n\n🤖 {advisor.personality.get_farewell()}")
            break
        except Exception as e:
            logger.exception("Error in interactive loop: %s", e)
            print("🤖 ❌ Yikes! Something went rekt! Check the logs or try again! 🔧")


# -----------------------------
# Main entrypoint
# -----------------------------

if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description="CryptoBuddy Pro+ v3 — Your based crypto advisor with personality! 🚀")
    parser.add_argument('--interactive', action='store_true', help='Start interactive mode (recommended)')
    parser.add_argument('--compare', nargs=2, help='Compare two coins (symbols or ids)')
    parser.add_argument('--price', nargs=1, help='Show price for a coin')
    parser.add_argument('--summary', nargs=1, help='Show summary for a coin')
    parser.add_argument('--rank', nargs='+', help='Rank given coins')
    parser.add_argument('--profit', action='store_true', help='Get profitability recommendations')
    parser.add_argument('--sustainable', action='store_true', help='Get sustainability recommendations')
    args = parser.parse_args()

    print("🚀 Initializing CryptoBuddy Pro+ v1...")
    print("💎 Loading coin data...")
    
    client = DataClient()
    advisor = CryptoAdvisor(client)

    if args.interactive:
        interactive_mode(advisor)
        sys.exit(0)

    if args.compare:
        a, b = args.compare
        print(advisor.compare(a, b))
        sys.exit(0)

    if args.price:
        print(advisor.summarize_coin(args.price[0]))
        sys.exit(0)

    if args.summary:
        print(advisor.summarize_coin(args.summary[0]))
        sys.exit(0)

    if args.rank:
        print(advisor.rank_coins(args.rank))
        sys.exit(0)

    if args.profit:
        print(advisor.get_profitability_recommendations())
        sys.exit(0)

    if args.sustainable:
        print(advisor.get_sustainability_recommendations())
        sys.exit(0)

    # default to interactive
    interactive_mode(advisor)