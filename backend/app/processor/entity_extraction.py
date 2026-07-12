import re
from dataclasses import dataclass


@dataclass(frozen=True)
class StockMention:
    ticker: str
    company_name: str | None = None
    exchange: str | None = None
    sector: str | None = None
    confidence: float = 1.0
    source: str = "regex"


STOCK_ALIASES: dict[str, StockMention] = {
    "AAPL": StockMention("AAPL", "Apple Inc.", "NASDAQ", "Technology", 1.0, "dictionary"),
    "APPLE": StockMention("AAPL", "Apple Inc.", "NASDAQ", "Technology", 0.95, "dictionary"),
    "AMZN": StockMention(
        "AMZN", "Amazon.com, Inc.", "NASDAQ", "Consumer Discretionary", 1.0, "dictionary"
    ),
    "AMAZON": StockMention(
        "AMZN", "Amazon.com, Inc.", "NASDAQ", "Consumer Discretionary", 0.95, "dictionary"
    ),
    "GOOG": StockMention(
        "GOOG", "Alphabet Inc.", "NASDAQ", "Communication Services", 1.0, "dictionary"
    ),
    "GOOGL": StockMention(
        "GOOGL", "Alphabet Inc.", "NASDAQ", "Communication Services", 1.0, "dictionary"
    ),
    "GOOGLE": StockMention(
        "GOOGL", "Alphabet Inc.", "NASDAQ", "Communication Services", 0.95, "dictionary"
    ),
    "META": StockMention(
        "META", "Meta Platforms, Inc.", "NASDAQ", "Communication Services", 1.0, "dictionary"
    ),
    "FACEBOOK": StockMention(
        "META", "Meta Platforms, Inc.", "NASDAQ", "Communication Services", 0.9, "dictionary"
    ),
    "MSFT": StockMention(
        "MSFT", "Microsoft Corporation", "NASDAQ", "Technology", 1.0, "dictionary"
    ),
    "MICROSOFT": StockMention(
        "MSFT", "Microsoft Corporation", "NASDAQ", "Technology", 0.95, "dictionary"
    ),
    "NFLX": StockMention(
        "NFLX", "Netflix, Inc.", "NASDAQ", "Communication Services", 1.0, "dictionary"
    ),
    "NETFLIX": StockMention(
        "NFLX", "Netflix, Inc.", "NASDAQ", "Communication Services", 0.95, "dictionary"
    ),
    "NVDA": StockMention("NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", 1.0, "dictionary"),
    "NVIDIA": StockMention(
        "NVDA", "NVIDIA Corporation", "NASDAQ", "Technology", 0.98, "dictionary"
    ),
    "TSLA": StockMention(
        "TSLA", "Tesla, Inc.", "NASDAQ", "Consumer Discretionary", 1.0, "dictionary"
    ),
    "TESLA": StockMention(
        "TSLA", "Tesla, Inc.", "NASDAQ", "Consumer Discretionary", 0.95, "dictionary"
    ),
    "AMD": StockMention(
        "AMD", "Advanced Micro Devices, Inc.", "NASDAQ", "Technology", 1.0, "dictionary"
    ),
    "INTC": StockMention("INTC", "Intel Corporation", "NASDAQ", "Technology", 1.0, "dictionary"),
    "PLTR": StockMention(
        "PLTR", "Palantir Technologies Inc.", "NYSE", "Technology", 1.0, "dictionary"
    ),
    "SMCI": StockMention(
        "SMCI", "Super Micro Computer, Inc.", "NASDAQ", "Technology", 1.0, "dictionary"
    ),
    "NIFTY": StockMention("NIFTY", "Nifty 50", "NSE", "Index", 1.0, "dictionary"),
    "BANKNIFTY": StockMention("BANKNIFTY", "Nifty Bank", "NSE", "Index", 1.0, "dictionary"),
    "FINNIFTY": StockMention("FINNIFTY", "Nifty Financial Services", "NSE", "Index", 1.0, "dictionary"),
    "RELIANCE": StockMention(
        "RELIANCE", "Reliance Industries Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "RELIANCE INDUSTRIES": StockMention(
        "RELIANCE", "Reliance Industries Ltd.", "NSE", "Energy", 0.98, "dictionary"
    ),
    "TCS": StockMention(
        "TCS", "Tata Consultancy Services Ltd.", "NSE", "Information Technology", 1.0, "dictionary"
    ),
    "INFY": StockMention(
        "INFY", "Infosys Ltd.", "NSE", "Information Technology", 1.0, "dictionary"
    ),
    "INFOSYS": StockMention(
        "INFY", "Infosys Ltd.", "NSE", "Information Technology", 0.98, "dictionary"
    ),
    "HDFCBANK": StockMention(
        "HDFCBANK", "HDFC Bank Ltd.", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "HDFC BANK": StockMention(
        "HDFCBANK", "HDFC Bank Ltd.", "NSE", "Financial Services", 0.98, "dictionary"
    ),
    "ICICIBANK": StockMention(
        "ICICIBANK", "ICICI Bank Ltd.", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "ICICI BANK": StockMention(
        "ICICIBANK", "ICICI Bank Ltd.", "NSE", "Financial Services", 0.98, "dictionary"
    ),
    "SBIN": StockMention(
        "SBIN", "State Bank of India", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "SBI": StockMention(
        "SBIN", "State Bank of India", "NSE", "Financial Services", 0.95, "dictionary"
    ),
    "STATE BANK": StockMention(
        "SBIN", "State Bank of India", "NSE", "Financial Services", 0.9, "dictionary"
    ),
    "KOTAKBANK": StockMention(
        "KOTAKBANK", "Kotak Mahindra Bank Ltd.", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "AXISBANK": StockMention(
        "AXISBANK", "Axis Bank Ltd.", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "LT": StockMention(
        "LT", "Larsen & Toubro Ltd.", "NSE", "Industrials", 1.0, "dictionary"
    ),
    "LARSEN": StockMention(
        "LT", "Larsen & Toubro Ltd.", "NSE", "Industrials", 0.9, "dictionary"
    ),
    "ITC": StockMention(
        "ITC", "ITC Ltd.", "NSE", "Consumer Staples", 1.0, "dictionary"
    ),
    "HINDUNILVR": StockMention(
        "HINDUNILVR", "Hindustan Unilever Ltd.", "NSE", "Consumer Staples", 1.0, "dictionary"
    ),
    "HUL": StockMention(
        "HINDUNILVR", "Hindustan Unilever Ltd.", "NSE", "Consumer Staples", 0.95, "dictionary"
    ),
    "BHARTIARTL": StockMention(
        "BHARTIARTL", "Bharti Airtel Ltd.", "NSE", "Telecommunication", 1.0, "dictionary"
    ),
    "AIRTEL": StockMention(
        "BHARTIARTL", "Bharti Airtel Ltd.", "NSE", "Telecommunication", 0.95, "dictionary"
    ),
    "BAJFINANCE": StockMention(
        "BAJFINANCE", "Bajaj Finance Ltd.", "NSE", "Financial Services", 1.0, "dictionary"
    ),
    "HCLTECH": StockMention(
        "HCLTECH", "HCL Technologies Ltd.", "NSE", "Information Technology", 1.0, "dictionary"
    ),
    "WIPRO": StockMention(
        "WIPRO", "Wipro Ltd.", "NSE", "Information Technology", 1.0, "dictionary"
    ),
    "TECHM": StockMention(
        "TECHM", "Tech Mahindra Ltd.", "NSE", "Information Technology", 1.0, "dictionary"
    ),
    "MARUTI": StockMention(
        "MARUTI", "Maruti Suzuki India Ltd.", "NSE", "Automobile", 1.0, "dictionary"
    ),
    "TATAMOTORS": StockMention(
        "TATAMOTORS", "Tata Motors Ltd.", "NSE", "Automobile", 1.0, "dictionary"
    ),
    "TATA MOTORS": StockMention(
        "TATAMOTORS", "Tata Motors Ltd.", "NSE", "Automobile", 0.98, "dictionary"
    ),
    "SUNPHARMA": StockMention(
        "SUNPHARMA", "Sun Pharmaceutical Industries Ltd.", "NSE", "Healthcare", 1.0, "dictionary"
    ),
    "CIPLA": StockMention(
        "CIPLA", "Cipla Ltd.", "NSE", "Healthcare", 1.0, "dictionary"
    ),
    "DRREDDY": StockMention(
        "DRREDDY", "Dr. Reddy's Laboratories Ltd.", "NSE", "Healthcare", 1.0, "dictionary"
    ),
    "DIVISLAB": StockMention(
        "DIVISLAB", "Divi's Laboratories Ltd.", "NSE", "Healthcare", 1.0, "dictionary"
    ),
    "TITAN": StockMention(
        "TITAN", "Titan Company Ltd.", "NSE", "Consumer Discretionary", 1.0, "dictionary"
    ),
    "ULTRACEMCO": StockMention(
        "ULTRACEMCO", "UltraTech Cement Ltd.", "NSE", "Construction Materials", 1.0, "dictionary"
    ),
    "ADANIENT": StockMention(
        "ADANIENT", "Adani Enterprises Ltd.", "NSE", "Diversified", 1.0, "dictionary"
    ),
    "ADANIPORTS": StockMention(
        "ADANIPORTS", "Adani Ports and Special Economic Zone Ltd.", "NSE", "Services", 1.0, "dictionary"
    ),
    "COALINDIA": StockMention(
        "COALINDIA", "Coal India Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "ONGC": StockMention(
        "ONGC", "Oil and Natural Gas Corporation Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "NTPC": StockMention(
        "NTPC", "NTPC Ltd.", "NSE", "Power", 1.0, "dictionary"
    ),
    "POWERGRID": StockMention(
        "POWERGRID", "Power Grid Corporation of India Ltd.", "NSE", "Power", 1.0, "dictionary"
    ),
    "ASIANPAINT": StockMention(
        "ASIANPAINT", "Asian Paints Ltd.", "NSE", "Consumer Discretionary", 1.0, "dictionary"
    ),
    "JSWSTEEL": StockMention(
        "JSWSTEEL", "JSW Steel Ltd.", "NSE", "Metals", 1.0, "dictionary"
    ),
    "TATASTEEL": StockMention(
        "TATASTEEL", "Tata Steel Ltd.", "NSE", "Metals", 1.0, "dictionary"
    ),
    "HINDALCO": StockMention(
        "HINDALCO", "Hindalco Industries Ltd.", "NSE", "Metals", 1.0, "dictionary"
    ),
    "GRASIM": StockMention(
        "GRASIM", "Grasim Industries Ltd.", "NSE", "Diversified", 1.0, "dictionary"
    ),
    "EICHERMOT": StockMention(
        "EICHERMOT", "Eicher Motors Ltd.", "NSE", "Automobile", 1.0, "dictionary"
    ),
    "HEROMOTOCO": StockMention(
        "HEROMOTOCO", "Hero MotoCorp Ltd.", "NSE", "Automobile", 1.0, "dictionary"
    ),
    "BPCL": StockMention(
        "BPCL", "Bharat Petroleum Corporation Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "IOC": StockMention(
        "IOC", "Indian Oil Corporation Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "GAIL": StockMention(
        "GAIL", "GAIL (India) Ltd.", "NSE", "Energy", 1.0, "dictionary"
    ),
    "IRCTC": StockMention(
        "IRCTC", "Indian Railway Catering and Tourism Corporation Ltd.", "NSE", "Services", 1.0, "dictionary"
    ),
    "ZOMATO": StockMention(
        "ZOMATO", "Zomato Ltd.", "NSE", "Consumer Services", 1.0, "dictionary"
    ),
    "PAYTM": StockMention(
        "PAYTM", "One 97 Communications Ltd.", "NSE", "Financial Technology", 1.0, "dictionary"
    ),
}

COMMON_WORDS = {
    "AI",
    "API",
    "ATH",
    "CEO",
    "CFO",
    "CPI",
    "DCF",
    "EPS",
    "ETF",
    "FDA",
    "FOMC",
    "GDP",
    "IPO",
    "MACD",
    "NYSE",
    "PM",
    "QQQ",
    "RSI",
    "SEC",
    "USD",
    "YOY",
}

TICKER_RE = re.compile(r"(?<![A-Za-z0-9])\$?([A-Z]{1,5})(?![A-Za-z0-9])")
COMPANY_RE = re.compile(
    r"\b("
    + "|".join(re.escape(key) for key in sorted(STOCK_ALIASES, key=len, reverse=True))
    + r")\b",
    re.IGNORECASE,
)


def extract_stock_mentions(text: str) -> list[StockMention]:
    mentions: dict[str, StockMention] = {}

    for match in COMPANY_RE.finditer(text or ""):
        alias = match.group(1).upper()
        mention = STOCK_ALIASES[alias]
        mentions[mention.ticker] = _merge_mentions(mentions.get(mention.ticker), mention)

    for match in TICKER_RE.finditer(text or ""):
        ticker = match.group(1).upper()
        if ticker in COMMON_WORDS:
            continue
        if ticker in STOCK_ALIASES:
            mention = STOCK_ALIASES[ticker]
        elif match.group(0).startswith("$"):
            mention = StockMention(ticker=ticker, confidence=0.85, source="cash_tag")
        else:
            continue
        mentions[ticker] = _merge_mentions(mentions.get(ticker), mention)

    return sorted(mentions.values(), key=lambda item: item.ticker)


def _merge_mentions(left: StockMention | None, right: StockMention) -> StockMention:
    if left is None or right.confidence >= left.confidence:
        return right
    return left
