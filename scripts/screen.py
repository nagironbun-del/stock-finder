"""
Stock Finder - Value & Growth Screener
========================================
ファンダメンタル指標で「割安かつ成長性のある」銘柄をスクリーニング。
3軸スコア(Value/Growth/Timing)を計算し、TOP10をJSONとして出力。

実行: python scripts/screen.py
出力: data/findings.json
"""

import json
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import yfinance as yf

# =============================================================================
# 対象ユニバース
# =============================================================================
# 「割安成長株」を探すための母集団。流動性のある中型〜大型株中心。
# 超大型のメガキャップ(AAPL, MSFT等)はバリュー候補に上がりにくいので除外気味。
# 中小型に振りすぎると流動性リスクが増えるので、ある程度知名度のある銘柄に絞る。

JP_UNIVERSE = [
    # 自動車・輸送
    "7203.T", "7267.T", "7269.T", "7270.T", "7201.T", "7211.T", "7261.T",
    "9101.T", "9104.T", "9201.T", "9202.T", "9020.T", "9022.T",
    # 電機・半導体・機械
    "6501.T", "6503.T", "6594.T", "6981.T", "6861.T", "6098.T", "6273.T",
    "6367.T", "6326.T", "6301.T", "6645.T", "6471.T", "6472.T", "6473.T",
    "6146.T", "6857.T", "6920.T", "8035.T", "7741.T", "7751.T", "7752.T",
    "6502.T", "6701.T", "6702.T", "6724.T",
    # 化学・素材・鉄鋼
    "4063.T", "4452.T", "4188.T", "3407.T", "4005.T", "4042.T", "4204.T",
    "5401.T", "5411.T", "5713.T", "5714.T", "5801.T", "5802.T",
    "3861.T", "3863.T",
    # 商社・小売
    "8001.T", "8002.T", "8031.T", "8053.T", "8058.T", "8015.T",
    "3382.T", "8267.T", "9983.T", "7974.T", "3099.T",
    # 建設・不動産
    "1801.T", "1802.T", "1803.T", "1812.T", "1928.T", "1925.T",
    "8801.T", "8802.T", "8830.T", "3289.T",
    # 金融
    "8306.T", "8316.T", "8411.T", "8604.T", "8766.T", "8725.T", "8750.T",
    "8591.T", "8593.T", "8473.T",
    # 医薬・ヘルスケア
    "4502.T", "4503.T", "4519.T", "4523.T", "4568.T", "4578.T", "4151.T",
    "4506.T", "4507.T", "4901.T",
    # IT・通信・サービス
    "9432.T", "9433.T", "9434.T", "9613.T", "4324.T", "4385.T", "4689.T",
    "4307.T", "4755.T", "4751.T", "9984.T", "3659.T", "2432.T",
    # 食品・消費
    "2502.T", "2503.T", "2914.T", "2802.T", "2801.T", "2269.T", "2282.T",
    "4452.T", "4901.T",
    # 電力・ガス・エネルギー
    "9501.T", "9502.T", "9503.T", "9531.T", "9532.T", "5020.T", "1605.T",
]

# 重複除去
JP_UNIVERSE = sorted(set(JP_UNIVERSE))

US_UNIVERSE = [
    # Value寄りの大型株
    "JPM", "BAC", "WFC", "C", "GS", "MS", "USB", "PNC", "TFC",
    "XOM", "CVX", "COP", "OXY", "EOG", "PSX", "VLO", "MPC",
    "VZ", "T", "TMUS", "CMCSA",
    "PFE", "MRK", "ABBV", "BMY", "GILD", "CVS", "CI",
    "GM", "F", "STLA",
    # 成長系で時々割安になる中型
    "INTC", "CSCO", "ORCL", "IBM", "HPQ", "DELL", "WDC", "STX",
    "PYPL", "EBAY", "MTCH", "PINS", "SNAP", "RBLX", "U",
    "DIS", "WBD", "PARA", "FOXA",
    "F", "GM", "RIVN", "LCID",
    "AAL", "DAL", "UAL", "LUV", "ALK", "JBLU",
    "M", "KSS", "GPS", "JWN", "BBY", "TGT", "TJX",
    "X", "CLF", "NUE", "STLD", "RS",
    "DE", "CAT", "PH", "ETN", "ITW", "EMR", "ROK",
    "BA", "LMT", "RTX", "NOC", "GD", "LHX",
    "DOW", "DD", "LYB", "EMN", "PPG",
    "AMGN", "REGN", "VRTX", "BIIB", "BMRN", "ALXN",
    "WMT", "COST", "HD", "LOW", "TJX", "DG", "DLTR",
    "PEP", "KO", "MDLZ", "GIS", "K", "CAG", "CPB", "HSY",
    "PG", "CL", "KMB", "CHD", "CLX",
    "DUK", "SO", "NEE", "AEP", "EXC", "XEL",
    # 中型成長
    "PLTR", "SOFI", "AFRM", "UPST", "HOOD", "COIN",
    "SHOP", "SQ", "RIOT", "MARA", "CLSK",
    "ROKU", "SPOT", "FSLY", "NET", "DDOG", "MDB", "OKTA", "ZS", "CRWD",
    "DKNG", "PENN", "MGM", "WYNN", "LVS",
]
US_UNIVERSE = sorted(set(US_UNIVERSE))


# =============================================================================
# スコア重み
# =============================================================================
SCORE_WEIGHTS = {
    "value": 40,    # 割安度
    "growth": 40,   # 成長性
    "timing": 20,   # 底値圏判定
}

TOP_N = 10


# =============================================================================
# Value(割安度)スコア
# =============================================================================

def score_pe(pe: float | None) -> tuple[float, str]:
    """Trailing PER スコア。低いほど良いが、マイナスは赤字なのでむしろ低得点。"""
    if pe is None:
        return 50, "PER取得不可"
    if pe < 0:
        return 15, f"PER赤字 ({pe:.1f})"
    if pe < 8:
        return 95, f"PER非常に割安 ({pe:.1f})"
    if pe < 12:
        return 85, f"PER割安 ({pe:.1f})"
    if pe < 16:
        return 70, f"PER やや割安 ({pe:.1f})"
    if pe < 22:
        return 50, f"PER 平均的 ({pe:.1f})"
    if pe < 30:
        return 30, f"PER やや割高 ({pe:.1f})"
    return 10, f"PER割高 ({pe:.1f})"


def score_forward_pe(fpe: float | None) -> tuple[float, str]:
    """Forward PER。将来予想ベースなのでより重要。"""
    if fpe is None:
        return 50, "予想PER取得不可"
    if fpe < 0:
        return 20, f"予想PER赤字 ({fpe:.1f})"
    if fpe < 10:
        return 95, f"予想PER非常に割安 ({fpe:.1f})"
    if fpe < 14:
        return 80, f"予想PER割安 ({fpe:.1f})"
    if fpe < 18:
        return 65, f"予想PER やや割安 ({fpe:.1f})"
    if fpe < 25:
        return 45, f"予想PER 平均 ({fpe:.1f})"
    return 20, f"予想PER割高 ({fpe:.1f})"


def score_pb(pb: float | None) -> tuple[float, str]:
    """PBR スコア。1.0以下で資産バリュー。ただし極端に低いと業績懸念。"""
    if pb is None:
        return 50, "PBR取得不可"
    if pb <= 0:
        return 25, f"PBR異常 ({pb:.2f})"
    if pb < 0.5:
        return 75, f"PBR大幅割安 (要注意 {pb:.2f})"
    if pb < 1.0:
        return 90, f"PBR割安(資産割れ {pb:.2f})"
    if pb < 1.5:
        return 75, f"PBR やや割安 ({pb:.2f})"
    if pb < 2.5:
        return 55, f"PBR 平均 ({pb:.2f})"
    if pb < 4.0:
        return 35, f"PBR やや割高 ({pb:.2f})"
    return 15, f"PBR割高 ({pb:.2f})"


def score_peg(peg: float | None) -> tuple[float, str]:
    """PEG ratio。PER ÷ EPS成長率。1.0以下が成長加味で割安。"""
    if peg is None:
        return 50, "PEG取得不可"
    if peg <= 0:
        return 30, f"PEG異常 ({peg:.2f})"
    if peg < 0.5:
        return 95, f"PEG非常に割安 ({peg:.2f})"
    if peg < 1.0:
        return 85, f"PEG割安 ({peg:.2f})"
    if peg < 1.5:
        return 65, f"PEG 適正 ({peg:.2f})"
    if peg < 2.0:
        return 40, f"PEG やや割高 ({peg:.2f})"
    return 20, f"PEG割高 ({peg:.2f})"


def score_dividend(dy: float | None) -> tuple[float, str]:
    """配当利回り。補助指標として、安定配当があれば加点。"""
    if dy is None or dy == 0:
        return 50, "無配・取得不可"
    pct = dy * 100
    if pct > 6:
        return 70, f"配当利回り {pct:.2f}% (高め・要持続性確認)"
    if pct > 4:
        return 80, f"配当利回り {pct:.2f}%"
    if pct > 2.5:
        return 70, f"配当利回り {pct:.2f}%"
    if pct > 1:
        return 60, f"配当利回り {pct:.2f}%"
    return 55, f"配当利回り {pct:.2f}%"


def calc_value_score(info: dict) -> tuple[float, dict]:
    pe = info.get("trailingPE")
    fpe = info.get("forwardPE")
    pb = info.get("priceToBook")
    peg = info.get("pegRatio") or info.get("trailingPegRatio")
    dy = info.get("dividendYield")

    s_pe, n_pe = score_pe(pe)
    s_fpe, n_fpe = score_forward_pe(fpe)
    s_pb, n_pb = score_pb(pb)
    s_peg, n_peg = score_peg(peg)
    s_dy, n_dy = score_dividend(dy)

    # Value内の重み: Forward PER と PEG を重視
    weights = {"pe": 20, "fpe": 30, "pb": 20, "peg": 25, "dy": 5}
    total = (
        s_pe * weights["pe"] + s_fpe * weights["fpe"] + s_pb * weights["pb"]
        + s_peg * weights["peg"] + s_dy * weights["dy"]
    ) / sum(weights.values())

    detail = {
        "trailing_pe": {"score": s_pe, "note": n_pe, "value": pe},
        "forward_pe":  {"score": s_fpe, "note": n_fpe, "value": fpe},
        "pbr":         {"score": s_pb, "note": n_pb, "value": pb},
        "peg":         {"score": s_peg, "note": n_peg, "value": peg},
        "dividend":    {"score": s_dy, "note": n_dy, "value": dy},
    }
    return total, detail


# =============================================================================
# Growth(成長性)スコア
# =============================================================================

def score_revenue_growth(rg: float | None) -> tuple[float, str]:
    """売上成長率(直近)"""
    if rg is None:
        return 50, "売上成長率取得不可"
    pct = rg * 100
    if pct > 30:
        return 95, f"売上成長 +{pct:.1f}% (急成長)"
    if pct > 15:
        return 85, f"売上成長 +{pct:.1f}%"
    if pct > 7:
        return 70, f"売上成長 +{pct:.1f}%"
    if pct > 0:
        return 55, f"売上成長 +{pct:.1f}% (微増)"
    if pct > -10:
        return 30, f"売上 {pct:.1f}% (減少)"
    return 10, f"売上 {pct:.1f}% (大幅減)"


def score_earnings_growth(eg: float | None) -> tuple[float, str]:
    """利益成長率"""
    if eg is None:
        return 50, "利益成長率取得不可"
    pct = eg * 100
    if pct > 50:
        return 95, f"利益成長 +{pct:.1f}% (急成長)"
    if pct > 25:
        return 85, f"利益成長 +{pct:.1f}%"
    if pct > 10:
        return 75, f"利益成長 +{pct:.1f}%"
    if pct > 0:
        return 60, f"利益成長 +{pct:.1f}%"
    if pct > -20:
        return 30, f"利益 {pct:.1f}% (減益)"
    return 10, f"利益 {pct:.1f}% (大幅減)"


def score_roe(roe: float | None) -> tuple[float, str]:
    """ROE 自己資本利益率"""
    if roe is None:
        return 50, "ROE取得不可"
    pct = roe * 100
    if pct > 25:
        return 95, f"ROE {pct:.1f}% (非常に高効率)"
    if pct > 15:
        return 85, f"ROE {pct:.1f}% (高効率)"
    if pct > 10:
        return 70, f"ROE {pct:.1f}%"
    if pct > 5:
        return 50, f"ROE {pct:.1f}%"
    if pct > 0:
        return 30, f"ROE {pct:.1f}% (低い)"
    return 15, f"ROE {pct:.1f}% (赤字)"


def score_margin(margin: float | None) -> tuple[float, str]:
    """営業利益率"""
    if margin is None:
        return 50, "営業利益率取得不可"
    pct = margin * 100
    if pct > 25:
        return 90, f"営業利益率 {pct:.1f}% (高収益体質)"
    if pct > 15:
        return 75, f"営業利益率 {pct:.1f}%"
    if pct > 8:
        return 60, f"営業利益率 {pct:.1f}%"
    if pct > 3:
        return 45, f"営業利益率 {pct:.1f}%"
    if pct > 0:
        return 30, f"営業利益率 {pct:.1f}% (薄い)"
    return 10, f"営業利益率 {pct:.1f}% (赤字)"


def score_target_upside(current: float | None, target: float | None) -> tuple[float, str]:
    """アナリスト目標株価との乖離"""
    if current is None or target is None or current <= 0:
        return 50, "目標株価取得不可"
    upside = (target / current - 1) * 100
    if upside > 40:
        return 95, f"目標まで +{upside:.1f}% (大幅上振れ余地)"
    if upside > 20:
        return 80, f"目標まで +{upside:.1f}%"
    if upside > 10:
        return 65, f"目標まで +{upside:.1f}%"
    if upside > 0:
        return 55, f"目標まで +{upside:.1f}%"
    if upside > -10:
        return 35, f"目標 {upside:.1f}% (やや上回る)"
    return 15, f"目標 {upside:.1f}% (大幅上回る)"


def calc_growth_score(info: dict) -> tuple[float, dict]:
    rg = info.get("revenueGrowth")
    eg = info.get("earningsGrowth") or info.get("earningsQuarterlyGrowth")
    roe = info.get("returnOnEquity")
    margin = info.get("operatingMargins") or info.get("profitMargins")
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    target = info.get("targetMeanPrice")

    s_rg, n_rg = score_revenue_growth(rg)
    s_eg, n_eg = score_earnings_growth(eg)
    s_roe, n_roe = score_roe(roe)
    s_margin, n_margin = score_margin(margin)
    s_target, n_target = score_target_upside(current, target)

    weights = {"rg": 25, "eg": 25, "roe": 20, "margin": 15, "target": 15}
    total = (
        s_rg * weights["rg"] + s_eg * weights["eg"] + s_roe * weights["roe"]
        + s_margin * weights["margin"] + s_target * weights["target"]
    ) / sum(weights.values())

    detail = {
        "revenue_growth":  {"score": s_rg, "note": n_rg, "value": rg},
        "earnings_growth": {"score": s_eg, "note": n_eg, "value": eg},
        "roe":             {"score": s_roe, "note": n_roe, "value": roe},
        "operating_margin":{"score": s_margin, "note": n_margin, "value": margin},
        "target_upside":   {"score": s_target, "note": n_target,
                            "current": current, "target": target},
    }
    return total, detail


# =============================================================================
# Timing(底値圏)スコア
# =============================================================================

def score_52w_position(current: float | None, low: float | None, high: float | None) -> tuple[float, str]:
    """52週レンジ内のポジション。下半分を高評価、最安値直近は警戒。"""
    if not all([current, low, high]) or high <= low:
        return 50, "52週レンジ取得不可"
    pos = (current - low) / (high - low)
    pct_from_high = (current / high - 1) * 100
    if pos < 0.05:
        return 70, f"52週安値圏 (高値から{pct_from_high:.1f}%、業績悪化リスク要確認)"
    if pos < 0.20:
        return 90, f"52週下位20%圏 (高値から{pct_from_high:.1f}%)"
    if pos < 0.40:
        return 80, f"52週下半分 (高値から{pct_from_high:.1f}%)"
    if pos < 0.60:
        return 60, f"52週中位 (高値から{pct_from_high:.1f}%)"
    if pos < 0.80:
        return 40, f"52週上位40% (高値から{pct_from_high:.1f}%)"
    return 20, f"52週高値圏 (高値から{pct_from_high:.1f}%)"


def score_6m_return(ret: float | None) -> tuple[float, str]:
    """6ヶ月リターン。下げているほどバリュー候補だが下げ過ぎは警戒。"""
    if ret is None:
        return 50, "6ヶ月リターン取得不可"
    pct = ret * 100
    if pct < -40:
        return 60, f"6ヶ月 {pct:.1f}% (大幅下落・要因確認)"
    if pct < -20:
        return 85, f"6ヶ月 {pct:.1f}% (調整局面)"
    if pct < -5:
        return 75, f"6ヶ月 {pct:.1f}%"
    if pct < 10:
        return 60, f"6ヶ月 {pct:+.1f}%"
    if pct < 30:
        return 40, f"6ヶ月 +{pct:.1f}% (上昇局面)"
    return 20, f"6ヶ月 +{pct:.1f}% (急騰中)"


def calc_timing_score(info: dict, hist_ret_6m: float | None) -> tuple[float, dict]:
    current = info.get("currentPrice") or info.get("regularMarketPrice")
    low = info.get("fiftyTwoWeekLow")
    high = info.get("fiftyTwoWeekHigh")

    s_pos, n_pos = score_52w_position(current, low, high)
    s_6m, n_6m = score_6m_return(hist_ret_6m)

    weights = {"pos": 60, "ret_6m": 40}
    total = (s_pos * weights["pos"] + s_6m * weights["ret_6m"]) / sum(weights.values())

    detail = {
        "fifty_two_week_position": {"score": s_pos, "note": n_pos,
                                    "low": low, "high": high, "current": current},
        "return_6m":               {"score": s_6m, "note": n_6m, "value": hist_ret_6m},
    }
    return total, detail


# =============================================================================
# 銘柄ごとの分析
# =============================================================================

def analyze_ticker(ticker: str) -> dict | None:
    """1銘柄を分析しスコア辞書を返す。"""
    try:
        tk = yf.Ticker(ticker)
        info = tk.info
        if not info or info.get("currentPrice") is None and info.get("regularMarketPrice") is None:
            return None

        # 6ヶ月リターン取得
        try:
            hist = tk.history(period="6mo", interval="1d", auto_adjust=True)
            if len(hist) >= 2:
                ret_6m = float(hist["Close"].iloc[-1] / hist["Close"].iloc[0] - 1)
            else:
                ret_6m = None
        except Exception:
            ret_6m = None

        # 各軸のスコアを計算
        v_score, v_detail = calc_value_score(info)
        g_score, g_detail = calc_growth_score(info)
        t_score, t_detail = calc_timing_score(info, ret_6m)

        # 総合スコア
        total = (
            v_score * SCORE_WEIGHTS["value"]
            + g_score * SCORE_WEIGHTS["growth"]
            + t_score * SCORE_WEIGHTS["timing"]
        ) / sum(SCORE_WEIGHTS.values())

        current = info.get("currentPrice") or info.get("regularMarketPrice")
        market_cap = info.get("marketCap")

        return {
            "ticker": ticker,
            "name": info.get("shortName") or info.get("longName") or ticker,
            "sector": info.get("sector") or "—",
            "industry": info.get("industry") or "—",
            "price": round(float(current), 2) if current else None,
            "market_cap": int(market_cap) if market_cap else None,
            "currency": info.get("currency") or "—",
            "total_score": round(total, 1),
            "axis_scores": {
                "value": round(v_score, 1),
                "growth": round(g_score, 1),
                "timing": round(t_score, 1),
            },
            "value": v_detail,
            "growth": g_detail,
            "timing": t_detail,
        }
    except Exception as e:
        print(f"  ! {ticker}: {e}", flush=True)
        return None


def run_screening(universe: list[str], market_label: str) -> list[dict]:
    print(f"[{market_label}] Screening {len(universe)} tickers...", flush=True)
    results = []
    for i, ticker in enumerate(universe, 1):
        if i % 20 == 0:
            print(f"  [{market_label}] {i}/{len(universe)} processed", flush=True)
        res = analyze_ticker(ticker)
        if res is None:
            continue
        # 流動性フィルタ: 時価総額が極端に小さいものは除外
        if res["market_cap"] and res["market_cap"] < 50_000_000_000 and market_label == "JP":
            # 日本株は500億円以下を除外
            continue
        if res["market_cap"] and res["market_cap"] < 1_000_000_000 and market_label == "US":
            # 米国株は10億ドル以下を除外
            continue
        res["market"] = market_label
        results.append(res)
        # APIレート制限対策(yfinanceは内部でレート制限することがある)
        time.sleep(0.1)

    print(f"[{market_label}] Got {len(results)} valid results", flush=True)
    return results


# =============================================================================
# メイン
# =============================================================================

def main():
    out_dir = Path(__file__).parent.parent / "data"
    out_dir.mkdir(parents=True, exist_ok=True)

    jst = timezone(timedelta(hours=9))
    now_jst = datetime.now(jst)

    jp = run_screening(JP_UNIVERSE, "JP")
    us = run_screening(US_UNIVERSE, "US")

    jp.sort(key=lambda x: x["total_score"], reverse=True)
    us.sort(key=lambda x: x["total_score"], reverse=True)

    payload = {
        "generated_at": now_jst.isoformat(),
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "weights": SCORE_WEIGHTS,
        "top_n": TOP_N,
        "markets": {
            "JP": {
                "top": jp[:TOP_N],
                "all_scanned": len(jp),
            },
            "US": {
                "top": us[:TOP_N],
                "all_scanned": len(us),
            },
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
    }

    out_path = out_dir / "findings.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

    print(f"\n✓ Saved: {out_path}", flush=True)
    print(f"  JP top 5: {[(r['ticker'], r['total_score']) for r in jp[:5]]}", flush=True)
    print(f"  US top 5: {[(r['ticker'], r['total_score']) for r in us[:5]]}", flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
