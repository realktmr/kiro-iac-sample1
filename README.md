# kiro-iac-sample1

Kiro IDE（Vibe coding）を使って、WEB三層アーキテクチャのCloudFormationテンプレートを生成した検証サンプルです。

Qiita記事「【Kiro活用】プロンプト一文で変わるIaCの品質——Well-Architected準拠を指示したらどうなるか検証してみた（第1部）」の検証コードです。

## 検証概要

同じ要件に対して2パターンのプロンプトでKiroに生成させ、出力の差を比較しました。

| | パターンA | パターンB |
|--|----------|----------|
| プロンプトの違い | 最小限の要件のみ | + Well-Architected準拠を指示 |
| EC2構成 | インスタンス直接×2 | ASG + LaunchTemplate |
| RDS Multi-AZ | 無効 | 有効 |
| RDS暗号化 | なし | あり |
| パスワード管理 | Parameter | Secrets Manager |
| IAMロール | なし | SSM + CWAgent付き |
| VPC Flow Logs | なし | あり |
| CloudWatchアラーム | なし | あり |

## ディレクトリ構成

```
kiro-iac-sample1/
├── README.md
├── pattern-a/
│   ├── template.yaml
│   └── design.md
└── pattern-b/
    ├── template.yaml
    └── design.md
```

## 注意事項

本リポジトリのテンプレートはKiroによる検証目的の生成物です。実際の本番環境への適用前には、セキュリティレビューを必ず実施してください。
