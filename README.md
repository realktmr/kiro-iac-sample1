# kiro-iac-sample1

Kiro IDE を使って、WEB三層アーキテクチャの CloudFormation テンプレートを生成・運用した検証シリーズのサンプルコードです。

## 連載記事

| 回 | 検証テーマ | Qiita |
|---|---|---|
| 第1部 | バイブコーディング × プロンプト品質の比較 | https://qiita.com/REALKTMR/items/325e5c5726c0989ade1c |
| 第2部 | Specモード × 仕様書品質の比較 | https://qiita.com/REALKTMR/items/0bafb70313b6d3dff3a9 |
| 第3部 | Agent HooksとCodePipelineでIaC変更を安全に適用する | https://qiita.com/REALKTMR/items/26e19c1559972a0aa5ea |

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
├── .kiro/
│   ├── hooks/
│   │   └── cfn-lint.kiro.hook   # Agent Hook：編集時にcfn-lint自動実行→クリーンなら commit/push まで完結
│   └── steering/
│       └── setup.md             # エージェント向けセットアップ情報（cfn-lintパス等）
├── pattern-1a/                  # 第1部：バイブコーディング（最小限プロンプト）
│   ├── template.yaml
│   └── design.md
├── pattern-1b/                  # 第1部：バイブコーディング（WA準拠指示）
│   ├── template.yaml
│   └── design.md
├── pattern-1c/                  # 第1部：参考パターン
│   ├── template.yaml
│   └── design.md
├── pattern-2a/                  # 第2部：Specモード（WA指示、バイブと同プロンプト）
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md
│   └── template.yaml
├── pattern-2b/                  # 第2部：Specモード（詳細な仕様書）
│   ├── spec-three-tier.md
│   ├── requirements.md
│   ├── design.md
│   ├── tasks.md
│   ├── template.yaml
│   └── test_template_properties.py
├── pattern-3/                   # 第3部：Agent Hooks + CodePipeline による変更管理
│   ├── template.yaml            # デプロイ対象CFnテンプレート（WEB三層構成）
│   ├── buildspec.yml            # CodeBuild実行仕様（cfn-lint検証）
│   └── pipeline.yaml           # パイプライン構築用CFnテンプレート
└── score_templates.py           # Well-Architected採点スクリプト（全パターン共通）
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

## 第3部：Agent Hooks + CodePipeline による変更管理

### Kiro Agent Hook のセットアップ

```powershell
# cfn-lint のインストール（初回のみ）
python -m venv .venv
.venv\Scripts\pip install cfn-lint
```

### デプロイフロー

```
template.yaml を編集
  ↓ 自動（fileEdited Hook 発火）
cfn-lint 自動チェック
  ↓ クリーン → 「コミットしてpushしますか？」
               ↓ 承認①
           git commit & push
  ↓
CodePipeline 自動起動
  ↓
Source → Validate(cfn-lint) → CreateChangeSet → Approval → ExecuteChangeSet
                                                     ↓ 承認②
                                                  デプロイ完了
```

**人間がやることは2回の承認だけ。コマンド入力は不要。**

### パイプラインのデプロイ

```bash
aws cloudformation deploy \
  --template-file pattern-3/pipeline.yaml \
  --stack-name kiro-blog-pipeline \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    GitHubConnectionArn=<your-connection-arn> \
    NotificationEmail=<your-email>
```

## 注意事項

本リポジトリのテンプレートはKiroによる検証目的の生成物です。実際の本番環境への適用前には、セキュリティレビューを必ず実施してください。
