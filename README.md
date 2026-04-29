# Stock Finder — 割安成長株スクリーナー

ファンダメンタル指標で「**今は割安、今後成長期待**」の銘柄を週次でスクリーニング。
日米両市場対応、yfinance のみで完全無料。

## 関連ツール

- `stock-advisor` (テクニカル分析・短期トレード向け、毎日更新)
- `stock-finder` (本ツール: ファンダメンタル分析・中長期視点、週次更新)

## アーキテクチャ

```
GitHub Actions (毎週月曜 6:00 JST)
   ↓ 実行
scripts/screen.py  ──→  yfinance API
   ↓ 出力
data/findings.json
   ↓ 自動 commit & push
   ↓ 読み込み
index.html (GitHub Pages)
```

## スコアリング設計(3軸)

### Value(割安度) 40%
| 指標 | 重み | 判定 |
|------|------|------|
| Trailing PER | 20% | 12以下で高得点、赤字は減点 |
| Forward PER | 30% | 将来予想ベース、より重要 |
| PBR | 20% | 1.0以下で資産バリュー |
| PEG ratio | 25% | 1.0以下で成長加味の割安 |
| 配当利回り | 5% | 補助指標 |

### Growth(成長性) 40%
| 指標 | 重み | 判定 |
|------|------|------|
| 売上成長率 | 25% | 直近の売上拡大度 |
| 利益成長率 | 25% | 直近の利益拡大度 |
| ROE | 20% | 自己資本利益率、15%超で高得点 |
| 営業利益率 | 15% | 収益体質 |
| アナリスト目標との乖離 | 15% | 上振れ余地 |

### Timing(底値圏判定) 20%
| 指標 | 重み | 判定 |
|------|------|------|
| 52週レンジ位置 | 60% | 下半分で高得点、最安値直近は警戒 |
| 過去6ヶ月リターン | 40% | 調整局面で高得点、急騰中は減点 |

## バリュートラップ対策

「PERが低い」だけで高得点にすると、業績悪化を市場が織り込んだ「バリュートラップ」を拾ってしまう。
本ツールでは以下で対策:

- **Forward PERを重視**(過去ではなく将来予想)
- **PEG ratioで成長を加味**
- **Growth軸で売上/利益成長率をチェック** → 減収減益の銘柄は減点
- **ROE と 営業利益率** → 収益体質が悪化していないか確認
- **52週安値直近すぎる銘柄は警戒シグナル**

## ディレクトリ構成

```
stock-finder/
├── .github/workflows/weekly-screening.yml   # 自動実行(週次)
├── scripts/
│   ├── screen.py                            # メインスクリプト
│   ├── requirements.txt
│   ├── dry_run.py                           # 合成データでロジック検証
│   └── gen_sample_data.py                   # UI用サンプル生成
├── data/
│   └── findings.json                        # スクリーニング結果
└── index.html                               # ダッシュボード
```

## セットアップ

`stock-advisor` と同じ手順:

1. GitHubで新規Publicリポジトリ `stock-finder` を作成
2. ファイル一式をアップロード(GitHub Desktop または zip展開→ブラウザでドラッグ&ドロップ)
3. Settings → Pages → Branch `main` → Save
4. Actions → Weekly Stock Screening → Run workflow で初回実行
5. `https://<USER>.github.io/stock-finder/` で閲覧

## 実行頻度

ファンダメンタル指標は日々大きく変動しないため、**週1回(月曜朝6時 JST)**で十分。
決算発表シーズンは決算後に手動でRun workflowすると最新の指標が反映される。

## カスタマイズ

- **対象銘柄**: `scripts/screen.py` の `JP_UNIVERSE`, `US_UNIVERSE`
- **スコア重み**: `SCORE_WEIGHTS`(現在 Value 40 / Growth 40 / Timing 20)
- **流動性フィルタ**: `run_screening` 内の時価総額閾値(JP: 500億円、US: 10億ドル)

## データ仕様の注意

yfinance(Yahoo Finance非公式API)のため:
- 日本株はforward PE、PEGなどの予想系指標が欠損することが多い
- 決算直後はinfo APIが古い数値を返すことがある(数日で更新される)
- 一部銘柄でAPIエラーが起きることがある(該当銘柄はスキップして続行)

## 免責

本ツールはファンダメンタル指標による機械的スクリーニングであり、投資推奨ではありません。
- バリュートラップ(割安に見えるが構造的衰退)を完全には除外できません
- アナリスト目標株価には外れることが多い予測値が含まれます
- 実際の投資判断は、決算短信・有報・業界動向・個別ニュースを併せてご自身で確認してください
