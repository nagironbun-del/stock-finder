"""HTMLの動作確認用にダミーfindings.jsonを生成。"""
import json
import sys
import random
from pathlib import Path
from datetime import datetime, timezone, timedelta

sys.path.insert(0, str(Path(__file__).parent))
from screen import calc_value_score, calc_growth_score, calc_timing_score, SCORE_WEIGHTS, TOP_N

random.seed(7)

# 適当なダミー銘柄(name, sector, industryなど)
JP_DUMMIES = [
    ("8306.T", "三菱UFJフィナンシャル・グループ", "Financial Services", "Banks—Diversified", "JPY", 1500, 18_000_000_000_000),
    ("9432.T", "日本電信電話", "Communication Services", "Telecom Services", "JPY", 165, 14_500_000_000_000),
    ("7203.T", "トヨタ自動車", "Consumer Cyclical", "Auto Manufacturers", "JPY", 2800, 45_000_000_000_000),
    ("8053.T", "住友商事", "Industrials", "Trading Companies", "JPY", 3500, 4_300_000_000_000),
    ("4502.T", "武田薬品工業", "Healthcare", "Drug Manufacturers", "JPY", 4100, 6_400_000_000_000),
    ("5401.T", "日本製鉄", "Basic Materials", "Steel", "JPY", 3200, 3_000_000_000_000),
    ("8316.T", "三井住友フィナンシャルグループ", "Financial Services", "Banks—Regional", "JPY", 9500, 12_500_000_000_000),
    ("9101.T", "日本郵船", "Industrials", "Marine Shipping", "JPY", 5200, 2_700_000_000_000),
    ("6501.T", "日立製作所", "Industrials", "Conglomerates", "JPY", 12500, 11_500_000_000_000),
    ("7267.T", "ホンダ", "Consumer Cyclical", "Auto Manufacturers", "JPY", 1750, 8_900_000_000_000),
]
US_DUMMIES = [
    ("INTC", "Intel Corporation", "Technology", "Semiconductors", "USD", 35, 150_000_000_000),
    ("PFE", "Pfizer Inc.", "Healthcare", "Drug Manufacturers", "USD", 28, 158_000_000_000),
    ("VZ", "Verizon Communications", "Communication Services", "Telecom Services", "USD", 42, 175_000_000_000),
    ("F", "Ford Motor Company", "Consumer Cyclical", "Auto Manufacturers", "USD", 11, 44_000_000_000),
    ("BAC", "Bank of America Corporation", "Financial Services", "Banks—Diversified", "USD", 38, 290_000_000_000),
    ("CVS", "CVS Health Corporation", "Healthcare", "Healthcare Plans", "USD", 65, 82_000_000_000),
    ("XOM", "Exxon Mobil Corporation", "Energy", "Oil & Gas Integrated", "USD", 110, 470_000_000_000),
    ("WBA", "Walgreens Boots Alliance", "Healthcare", "Pharmaceutical Retail", "USD", 11, 9_500_000_000),
    ("PARA", "Paramount Global", "Communication Services", "Entertainment", "USD", 12, 8_000_000_000),
    ("GM", "General Motors Company", "Consumer Cyclical", "Auto Manufacturers", "USD", 48, 55_000_000_000),
]

def random_info(profile):
    """profile: 'garp', 'expensive', 'trap', 'avg'"""
    if profile == "garp":
        return {
            "trailingPE": random.uniform(7, 13),
            "forwardPE": random.uniform(6, 11),
            "priceToBook": random.uniform(0.6, 1.4),
            "pegRatio": random.uniform(0.5, 1.0),
            "dividendYield": random.uniform(0.02, 0.045),
            "revenueGrowth": random.uniform(0.10, 0.25),
            "earningsGrowth": random.uniform(0.15, 0.35),
            "returnOnEquity": random.uniform(0.13, 0.22),
            "operatingMargins": random.uniform(0.10, 0.20),
            "ret_6m": random.uniform(-0.20, 0.05),
            "_pos_in_52w": random.uniform(0.15, 0.45),
        }
    if profile == "trap":
        return {
            "trailingPE": random.uniform(5, 10),
            "forwardPE": random.uniform(8, 14),
            "priceToBook": random.uniform(0.5, 0.9),
            "pegRatio": None,
            "dividendYield": random.uniform(0.05, 0.08),
            "revenueGrowth": random.uniform(-0.15, -0.02),
            "earningsGrowth": random.uniform(-0.40, -0.10),
            "returnOnEquity": random.uniform(0.02, 0.08),
            "operatingMargins": random.uniform(0.01, 0.05),
            "ret_6m": random.uniform(-0.40, -0.20),
            "_pos_in_52w": random.uniform(0.02, 0.15),
        }
    return {  # avg
        "trailingPE": random.uniform(14, 22),
        "forwardPE": random.uniform(13, 19),
        "priceToBook": random.uniform(1.5, 3.0),
        "pegRatio": random.uniform(1.0, 1.8),
        "dividendYield": random.uniform(0.01, 0.03),
        "revenueGrowth": random.uniform(0.02, 0.10),
        "earningsGrowth": random.uniform(0.0, 0.15),
        "returnOnEquity": random.uniform(0.08, 0.15),
        "operatingMargins": random.uniform(0.07, 0.13),
        "ret_6m": random.uniform(-0.10, 0.15),
        "_pos_in_52w": random.uniform(0.30, 0.65),
    }

def make_record(meta, profile):
    ticker, name, sector, industry, currency, price, mcap = meta
    info = random_info(profile)
    pos = info.pop("_pos_in_52w")
    ret_6m = info.pop("ret_6m")
    low = price * (1 - random.uniform(0.20, 0.50))
    high = price * (1 + random.uniform(0.10, 0.35))
    # adjust price to match pos
    price = low + pos * (high - low)
    target = price * (1 + random.uniform(0.05, 0.40))
    info.update({
        "currentPrice": price, "targetMeanPrice": target,
        "fiftyTwoWeekLow": low, "fiftyTwoWeekHigh": high,
        "shortName": name, "sector": sector, "industry": industry,
        "currency": currency, "marketCap": mcap,
    })
    v_score, v_d = calc_value_score(info)
    g_score, g_d = calc_growth_score(info)
    t_score, t_d = calc_timing_score(info, ret_6m)
    total = (v_score * SCORE_WEIGHTS["value"] + g_score * SCORE_WEIGHTS["growth"]
             + t_score * SCORE_WEIGHTS["timing"]) / sum(SCORE_WEIGHTS.values())
    return {
        "ticker": ticker, "name": name, "sector": sector, "industry": industry,
        "price": round(price, 2), "market_cap": int(mcap), "currency": currency,
        "total_score": round(total, 1),
        "axis_scores": {
            "value": round(v_score, 1), "growth": round(g_score, 1), "timing": round(t_score, 1),
        },
        "value": v_d, "growth": g_d, "timing": t_d,
    }

def make_market(dummies, label):
    profiles = ["garp"]*4 + ["avg"]*4 + ["trap"]*2
    random.shuffle(profiles)
    items = []
    for meta, profile in zip(dummies, profiles):
        rec = make_record(meta, profile)
        rec["market"] = label
        items.append(rec)
    items.sort(key=lambda x: x["total_score"], reverse=True)
    return items

jp = make_market(JP_DUMMIES, "JP")
us = make_market(US_DUMMIES, "US")

jst = timezone(timedelta(hours=9))
payload = {
    "generated_at": datetime.now(jst).isoformat(),
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "weights": SCORE_WEIGHTS,
    "top_n": TOP_N,
    "markets": {
        "JP": {"top": jp[:TOP_N], "all_scanned": len(jp)},
        "US": {"top": us[:TOP_N], "all_scanned": len(us)},
    },
    "methodology": (
        "ファンダメンタル指標(PER、PBR、PEG、配当)で割安度、"
        "売上/利益成長率、ROE、目標株価で成長性、"
        "52週レンジと過去6ヶ月リターンで底値圏を判定し、"
        "重み付けスコアでランキング。yfinance(Yahoo Finance)データ使用。"
    ),
    "disclaimer": (
        "本データはファンダメンタル指標による機械的スクリーニングの結果であり、"
        "投資推奨ではありません。指標の数値は遅延・欠損があり得ます。"
        "実際の投資判断は最新の決算情報、企業ニュース、業界動向を確認の上、"
        "ご自身の責任で行ってください。バリュートラップ(割安に見えるが業績悪化)"
        "や業績悪化銘柄が含まれる可能性があります。"
    ),
    "_note": "SAMPLE PREVIEW DATA — generated by gen_sample_data.py for UI preview.",
}

out = Path(__file__).parent.parent / "data" / "findings.json"
out.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
print(f"Saved: {out}")
print(f"  JP top 3: {[(r['ticker'], r['total_score']) for r in jp[:3]]}")
print(f"  US top 3: {[(r['ticker'], r['total_score']) for r in us[:3]]}")
