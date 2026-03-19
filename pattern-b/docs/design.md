# WEB三層アーキテクチャ 設計ドキュメント

## 1. アーキテクチャ概要

ALB → EC2 (Apache + Hello World) → RDS (MySQL) のWEB三層構成。
AWS Well-Architected Framework 6本柱に準拠。

```
Internet
    │
    ▼
┌─────────────────────────────────────────────┐
│  VPC (10.0.0.0/16) - ap-northeast-1         │
│                                              │
│  ┌─── Public Subnet (AZ-a) ───┐  ┌─── Public Subnet (AZ-c) ───┐
│  │  NAT Gateway                │  │                              │
│  │  ALB (node)                 │  │  ALB (node)                  │
│  └─────────────────────────────┘  └──────────────────────────────┘
│                                                                   │
│  ┌─── Private Subnet (AZ-a) ──┐  ┌─── Private Subnet (AZ-c) ──┐
│  │  EC2 (Apache)               │  │  EC2 (Apache)               │
│  │  Auto Scaling Group         │  │  Auto Scaling Group          │
│  └─────────────────────────────┘  └──────────────────────────────┘
│                                                                   │
│  ┌─── DB Subnet (AZ-a) ───────┐  ┌─── DB Subnet (AZ-c) ───────┐
│  │  RDS MySQL (Primary)        │  │  RDS MySQL (Standby)         │
│  └─────────────────────────────┘  └──────────────────────────────┘
└───────────────────────────────────────────────────────────────────┘
```

## 2. Well-Architected Framework 6本柱への対応

### 2.1 運用上の優秀性 (Operational Excellence)
| 対策 | 実装 |
|------|------|
| IaC | CloudFormation によるインフラ全体のコード管理 |
| モニタリング | CloudWatch アラーム (CPU, DB接続数) |
| ログ管理 | VPC Flow Logs 有効化 |
| Auto Scaling | EC2 Auto Scaling Group による自動スケーリング |

### 2.2 セキュリティ (Security)
| 対策 | 実装 |
|------|------|
| ネットワーク分離 | Public / Private / DB の3層サブネット |
| 最小権限 | Security Group で必要ポートのみ許可 |
| 暗号化(転送中) | ALB で HTTPS 対応可能な構成 |
| 暗号化(保存時) | RDS ストレージ暗号化 (KMS) |
| EC2配置 | Private Subnet に配置、直接インターネットアクセス不可 |
| DB認証 | Secrets Manager でパスワード管理 |
| IMDSv2 | EC2 メタデータサービス v2 を強制 |

### 2.3 信頼性 (Reliability)
| 対策 | 実装 |
|------|------|
| マルチAZ | 2つの AZ (ap-northeast-1a, 1c) に分散 |
| Auto Scaling | 最小2台、最大4台の EC2 Auto Scaling |
| RDS Multi-AZ | 自動フェイルオーバー対応 |
| ヘルスチェック | ALB ターゲットグループによるヘルスチェック |
| NAT Gateway | インターネットアクセス用 (パッチ適用等) |

### 2.4 パフォーマンス効率 (Performance Efficiency)
| 対策 | 実装 |
|------|------|
| インスタンスタイプ | EC2: t3.small, RDS: db.t3.small (適切なサイジング) |
| ALB | リクエストの効率的な分散 |
| Auto Scaling | CPU 70% をターゲットとしたスケーリングポリシー |

### 2.5 コスト最適化 (Cost Optimization)
| 対策 | 実装 |
|------|------|
| 適正サイジング | 小規模インスタンスから開始 |
| Auto Scaling | 需要に応じたスケールイン/アウト |
| パラメータ化 | インスタンスタイプをパラメータで変更可能 |

### 2.6 サステナビリティ (Sustainability)
| 対策 | 実装 |
|------|------|
| 効率的なリソース利用 | Auto Scaling による必要最小限のリソース運用 |
| 最新世代 | t3 インスタンスファミリー (Nitro ベース) |
| リージョン選択 | ap-northeast-1 (東京) |

## 3. ネットワーク設計

| サブネット | CIDR | 用途 |
|-----------|------|------|
| Public Subnet AZ-a | 10.0.1.0/24 | ALB, NAT Gateway |
| Public Subnet AZ-c | 10.0.2.0/24 | ALB |
| Private Subnet AZ-a | 10.0.11.0/24 | EC2 (Apache) |
| Private Subnet AZ-c | 10.0.12.0/24 | EC2 (Apache) |
| DB Subnet AZ-a | 10.0.21.0/24 | RDS |
| DB Subnet AZ-c | 10.0.22.0/24 | RDS |

## 4. セキュリティグループ設計

| SG | インバウンド | ソース |
|----|------------|--------|
| ALB SG | TCP 80 | 0.0.0.0/0 |
| EC2 SG | TCP 80 | ALB SG |
| RDS SG | TCP 3306 | EC2 SG |

## 5. パラメータ一覧

| パラメータ | デフォルト値 | 説明 |
|-----------|-------------|------|
| EnvironmentName | prod | 環境名 |
| EC2InstanceType | t3.small | EC2 インスタンスタイプ |
| DBInstanceClass | db.t3.small | RDS インスタンスクラス |
| DBName | appdb | データベース名 |
| DBMasterUsername | admin | DB マスターユーザー名 |

## 6. デプロイ手順

```bash
# 1. テンプレートの検証
aws cloudformation validate-template \
  --template-body file://cloudformation/web-three-tier.yaml

# 2. スタックの作成
aws cloudformation create-stack \
  --stack-name web-three-tier \
  --template-body file://cloudformation/web-three-tier.yaml \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-1

# 3. スタックの状態確認
aws cloudformation describe-stacks \
  --stack-name web-three-tier \
  --region ap-northeast-1
```

## 7. 出力値

| 出力 | 説明 |
|------|------|
| ALBDNSName | ALB の DNS 名 (アクセスURL) |
| VPCId | VPC ID |
| RDSEndpoint | RDS エンドポイント |
