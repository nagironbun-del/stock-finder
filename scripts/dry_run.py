"""ファンダメンタル指標の合成データでスコアリングロジックを検証。"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from screen import calc_value_score, calc_growth_score, calc_timing_score, SCORE_WEIGHTS

# 各テストケースを定義
test_cases = {
    # 理想的な割安成長株: 低PER、低PBR、低PEG、高成長、高ROE、底値圏
    "IDEAL_GARP": {
        "trailingPE": 10, "forwardPE": 9, "priceToBook": 0.9, "pegRatio": 0.7,
        "dividendYield": 0.025, "revenueGrowth": 0.18, "earningsGrowth": 0.30,
        "returnOnEquity": 0.18, "operatingMargins": 0.15,
        "currentPrice": 100, "targetMeanPrice": 140,
        "fiftyTwoWeekLow": 80, "fiftyTwoWeekHigh": 150,
        "ret_6m": -0.10,
    },
    # 過熱した成長株: 高PER、高成長(でも割高なので減点)
    "EXPENSIVE_GROWTH": {
        "trailingPE": 45, "forwardPE": 38, "priceToBook": 8, "pegRatio": 2.5,
        "dividendYield": 0, "revenueGrowth": 0.35, "earningsGrowth": 0.40,
        "returnOnEquity": 0.30, "operatingMargins": 0.25,
        "currentPrice": 200, "targetMeanPrice": 210,
        "fiftyTwoWeekLow": 120, "fiftyTwoWeekHigh": 220,
        "ret_6m": 0.45,
    },
    # 衰退バリュー株(バリュートラップの典型): 低PER低PBRだが業績悪化
    "VALUE_TRAP": {
        "trailingPE": 6, "forwardPE": 12, "priceToBook": 0.6, "pegRatio": None,
        "dividendYield": 0.08, "revenueGrowth": -0.15, "earningsGrowth": -0.40,
        "returnOnEquity": 0.03, "operatingMargins": 0.02,
        "currentPrice": 50, "targetMeanPrice": 55,
        "fiftyTwoWeekLow": 48, "fiftyTwoWeekHigh": 100,
        "ret_6m": -0.40,
    },
    # 平均的な大型株
    "AVERAGE": {
        "trailingPE": 18, "forwardPE": 16, "priceToBook": 2.5, "pegRatio": 1.5,
        "dividendYield": 0.02, "revenueGrowth": 0.05, "earningsGrowth": 0.08,
        "returnOnEquity": 0.12, "operatingMargins": 0.10,
        "currentPrice": 100, "targetMeanPrice": 110,
        "fiftyTwoWeekLow": 85, "fiftyTwoWeekHigh": 115,
        "ret_6m": 0.08,
    },
    # 完全な赤字企業
    "LOSS_MAKER": {
        "trailingPE": -10, "forwardPE": -5, "priceToBook": 1.5, "pegRatio": None,
        "dividendYield": 0, "revenueGrowth": -0.05, "earningsGrowth": -0.80,
        "returnOnEquity": -0.10, "operatingMargins": -0.15,
        "currentPrice": 30, "targetMeanPrice": 35,
        "fiftyTwoWeekLow": 25, "fiftyTwoWeekHigh": 80,
        "ret_6m": -0.50,
    },
}

results = []
for name, info in test_cases.items():
    ret_6m = info.pop("ret_6m")
    v_score, v_d = calc_value_score(info)
    g_score, g_d = calc_growth_score(info)
    t_score, t_d = calc_timing_score(info, ret_6m)
    total = (v_score * SCORE_WEIGHTS["value"] + g_score * SCORE_WEIGHTS["growth"]
             + t_score * SCORE_WEIGHTS["timing"]) / sum(SCORE_WEIGHTS.values())
    results.append({
        "name": name, "total": round(total, 1),
        "value": round(v_score, 1), "growth": round(g_score, 1), "timing": round(t_score, 1),
    })

results.sort(key=lambda x: x["total"], reverse=True)

print("=" * 72)
print(f"{'銘柄タイプ':<22} {'総合':>6} {'Value':>7} {'Growth':>7} {'Timing':>7}")
print("=" * 72)
for r in results:
    print(f"{r['name']:<22} {r['total']:>6.1f} {r['value']:>7.1f} {r['growth']:>7.1f} {r['timing']:>7.1f}")
print("=" * 72)

# 検証
ideal = next(r for r in results if r["name"] == "IDEAL_GARP")
trap = next(r for r in results if r["name"] == "VALUE_TRAP")
loss = next(r for r in results if r["name"] == "LOSS_MAKER")
expensive = next(r for r in results if r["name"] == "EXPENSIVE_GROWTH")

print("\nLogic checks:")
checks = [
    ("IDEAL_GARP最高得点", results[0]["name"] == "IDEAL_GARP"),
    ("IDEAL > VALUE_TRAP (バリュートラップ識別)", ideal["total"] > trap["total"]),
    ("IDEAL > EXPENSIVE_GROWTH (過熱成長より割安成長)", ideal["total"] > expensive["total"]),
    ("LOSS_MAKER最低得点 (赤字回避)", results[-1]["name"] == "LOSS_MAKER"),
]
for desc, ok in checks:
    print(f"  {'✓' if ok else '✗'} {desc}")
