# kiro-iac-sample1
<!-- auto-trigger final test -->

Kiro IDE を使って、WEB三層アーキテクチャの CloudFormation テンプレートを生成した検証シリーズのサンプルコードです。

## 連載記事

| 回 | 検証テーマ |
|---|---|
| 第1部 | バイブコーディング × プロンプト品質の比較 |
| 第2部 | Specモード × 仕様書品質の比較 |

## Well-Architected スコア（全パターン）

| パターン | モード | プロンプト | OE | SEC | REL | PERF | COST | SUST | 合計 |
|---------|------|-----------|:---:|:---:|:---:|:----:|:----:|:----:|:----:|
| pattern-1a | バイブ | 最小限 | 1 | 2 | 2 | 2 | 3 | 2 | **12/30** |
| pattern-1b | バイブ | Well-Architected準拠を指示 | 4 | 5 | 5 | 4 | 4 | 4 | **26/30** |
| pattern-2a | Spec | WA指示（バイブと同プロンプト） | 5 | 5 | 5 | 4 | 5 | 4 | **28/30** |
| pattern-2b | Spec | 詳細な仕様書 | 5 | 5 | 5 | 5 | 5 | 5 | **30/30** |

## ディレクトリ構成

```
kiro-iac-sample1/
├── pattern-1a/           # 第1部：バイブコーディング（最小限プロンプト）
│   ├── template.yaml
│   └── design.md
├── pattern-1b/           # 第1部：バイブコーディング（WA準拠指示）
│   ├── template.yaml
│   └── design.md
├── pattern-1c/           # 第1部：参考パターン
│   ├── template.yaml
│   └── design.md
├── pattern-2a/           # 第2部：Specモード（WA指示、バイブと同プロンプト）
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md
│   └── template.yaml
├── pattern-2b/           # 第2部：Specモード（詳細な仕様書）
│   ├── spec-three-tier.md
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md
│   ├── template.yaml
│   └── test_template_properties.py
└── score_templates.py    # Well-Architected採点スクリプト（全パターン共通）
```

## 第1部：バイブコーディング比較

| | pattern-1a | pattern-1b |
|--|:----------:|:----------:|
| プロンプト | 最小限の要件のみ | + Well-Architected準拠を指示 |
| EC2構成 | インスタンス直接×2 | ASG + LaunchTemplate |
| RDS Multi-AZ | ❌ | ✅ |
| RDS暗号化 | ❌ | ✅ |
| パスワード管理 | Parameter | Secrets Manager |
| IAMロール | ❌ | ✅ SSM + CWAgent |
| VPC Flow Logs | ❌ | ✅ |
| CloudWatchアラーム | ❌ | ✅ |
| **WA スコア** | **12/30** | **26/30** |

## 第2部：Specモード比較

| | pattern-2a | pattern-2b |
|--|:----------:|:----------:|
| 入力 | WA指示のみ（バイブと同じプロンプト） | 詳細仕様書（spec-three-tier.md） |
| EC2構成 | ASG + LaunchTemplate (t4g Graviton) | ASG + LaunchTemplate (t4g Graviton) |
| HTTPS対応 | ✅ ACM | ✅ ACM |
| パスワード管理 | Secrets Manager | Secrets Manager |
| VPC Flow Logs | ✅ | ✅ |
| CloudWatchアラーム | ✅ 4種 + SNS | ✅ 4種 + SNS |
| IMDSv2強制 | ✅ | ✅ |
| EBS暗号化 | ✅ | ✅ |
| RDS StorageType | gp2（デフォルト） | **gp3（明示）** |
| **WA スコア** | **28/30** | **30/30** |

## 注意事項

本リポジトリのテンプレートはKiroによる検証目的の生成物です。実際の本番環境への適用前には、セキュリティレビューを必ず実施してください。
