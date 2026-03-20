# WEB三層アーキテクチャ 設計ドキュメント

## 1. アーキテクチャ概要

ALB → EC2 (Apache + Hello World) → RDS (MySQL) の三層構成をAWS上に構築する。

```
Internet
    │
    ▼
┌─────────────────────────────────────────────────┐
│  VPC (10.0.0.0/16) - ap-northeast-1             │
│                                                   │
│  ┌─── Public Subnet (AZ-a) ──┐  ┌─── Public Subnet (AZ-c) ──┐  │
│  │  NAT Gateway               │  │                             │  │
│  │  ALB Node                  │  │  ALB Node                   │  │
│  └────────────────────────────┘  └─────────────────────────────┘  │
│                                                                     │
│  ┌─── Private Subnet (AZ-a) ─┐  ┌─── Private Subnet (AZ-c) ─┐  │
│  │  EC2 (Apache)              │  │  EC2 (Apache)               │  │
│  │  Auto Scaling Group        │  │  Auto Scaling Group          │  │
│  └────────────────────────────┘  └─────────────────────────────┘  │
│                                                                     │
│  ┌─── DB Subnet (AZ-a) ──────┐  ┌─── DB Subnet (AZ-c) ──────┐  │
│  │  RDS Primary (MySQL)       │  │  RDS Standby (Multi-AZ)     │  │
│  └────────────────────────────┘  └─────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. リージョン・AZ構成

| 項目 | 値 |
|------|-----|
| リージョン | ap-northeast-1 (東京) |
| AZ | ap-northeast-1a, ap-northeast-1c |
| VPC CIDR | 10.0.0.0/16 |

## 3. サブネット設計

| サブネット | CIDR | AZ | 用途 |
|-----------|------|-----|------|
| Public Subnet 1 | 10.0.1.0/24 | ap-northeast-1a | ALB, NAT Gateway |
| Public Subnet 2 | 10.0.2.0/24 | ap-northeast-1c | ALB |
| Private Subnet 1 | 10.0.11.0/24 | ap-northeast-1a | EC2 (Web/App) |
| Private Subnet 2 | 10.0.12.0/24 | ap-northeast-1c | EC2 (Web/App) |
| DB Subnet 1 | 10.0.21.0/24 | ap-northeast-1a | RDS |
| DB Subnet 2 | 10.0.22.0/24 | ap-northeast-1c | RDS |

## 4. 使用AWSサービス一覧

| サービス | 用途 | 設定 |
|---------|------|------|
| VPC | ネットワーク分離 | 10.0.0.0/16, DNS有効 |
| Internet Gateway | インターネット接続 | VPCにアタッチ |
| NAT Gateway | プライベートサブネットの外部通信 | Public Subnet 1に配置 |
| ALB | トラフィック分散 | Public Subnet 1,2に配置, HTTP(80) |
| EC2 | Webサーバー | Amazon Linux 2023, t3.small, Apache |
| Auto Scaling Group | スケーリング | Min:2, Max:4, Desired:2 |
| RDS | データベース | MySQL 8.0, db.t3.small, Multi-AZ |
| CloudWatch | 監視 | CPU使用率アラーム |
| SNS | 通知 | アラーム通知先 |

## 5. セキュリティ設計

### セキュリティグループ

| SG名 | インバウンド | アウトバウンド | 用途 |
|------|------------|-------------|------|
| ALB SG | 0.0.0.0/0:80 | EC2 SG:80 | ALB用 |
| EC2 SG | ALB SG:80 | 0.0.0.0/0:443 (HTTPS), DB SG:3306 | EC2用 |
| RDS SG | EC2 SG:3306 | なし | RDS用 |

### IAM
- EC2インスタンスプロファイル: SSM接続用の最小権限ポリシー
- SSH鍵不要（SSM Session Manager経由でアクセス）

## 6. AWS Well-Architected Framework 6本柱への対応

### 6.1 運用上の優秀性 (Operational Excellence)
- CloudFormationによるIaC管理（変更管理の自動化）
- CloudWatchによるCPU使用率の監視とSNSアラーム通知
- SSM Session Managerによるセキュアなインスタンスアクセス（SSH不要）
- Auto Scaling Groupによる自動復旧

### 6.2 セキュリティ (Security)
- VPCによるネットワーク分離（Public/Private/DBサブネット）
- EC2をプライベートサブネットに配置（直接インターネットアクセス不可）
- RDSをDBサブネットに配置（EC2からのみアクセス可能）
- セキュリティグループによる最小権限のネットワークアクセス制御
- RDSのストレージ暗号化（KMS）
- IAMインスタンスプロファイルによる最小権限のアクセス制御
- RDSパスワードはNoEchoパラメータで保護

### 6.3 信頼性 (Reliability)
- Multi-AZ構成（2つのAZに分散配置）
- ALBによるヘルスチェックと自動フェイルオーバー
- Auto Scaling Groupによる自動復旧（最小2台維持）
- RDS Multi-AZによる自動フェイルオーバー
- RDS自動バックアップ（7日間保持）

### 6.4 パフォーマンス効率 (Performance Efficiency)
- ALBによるトラフィック分散
- Auto Scalingによる需要に応じたスケーリング（CPU 70%閾値）
- 適切なインスタンスタイプの選択（t3.small）
- RDS適切なインスタンスクラス（db.t3.small）

### 6.5 コスト最適化 (Cost Optimization)
- Auto Scalingによる需要に応じたリソース調整
- NAT Gatewayは1つに集約（コスト削減）
- パラメータによるインスタンスタイプの変更が可能
- 不要時はスタック削除で全リソース削除可能
- DeletionPolicy: Snapshotで削除時もデータ保護

### 6.6 持続可能性 (Sustainability)
- Auto Scalingによる必要最小限のリソース使用
- 適切なインスタンスサイズの選択（過剰プロビジョニング回避）
- 東京リージョン使用によるレイテンシ最小化（日本向けサービスの場合）

## 7. パラメータ一覧

| パラメータ | デフォルト値 | 説明 |
|-----------|------------|------|
| EnvironmentName | dev | 環境名（タグ付けに使用） |
| VpcCIDR | 10.0.0.0/16 | VPCのCIDR |
| EC2InstanceType | t3.small | EC2インスタンスタイプ |
| DBInstanceClass | db.t3.small | RDSインスタンスクラス |
| DBName | appdb | データベース名 |
| DBMasterUsername | admin | DBマスターユーザー名 |
| DBMasterPassword | (入力必須) | DBマスターパスワード |
| NotificationEmail | (入力必須) | アラーム通知先メールアドレス |

## 8. デプロイ手順

```bash
# スタック作成
aws cloudformation create-stack \
  --stack-name three-tier-app \
  --template-body file://cfn-three-tier.yaml \
  --parameters \
    ParameterKey=DBMasterPassword,ParameterValue=<パスワード> \
    ParameterKey=NotificationEmail,ParameterValue=<メールアドレス> \
  --capabilities CAPABILITY_IAM \
  --region ap-northeast-1

# スタック状態確認
aws cloudformation describe-stacks \
  --stack-name three-tier-app \
  --region ap-northeast-1

# スタック削除
aws cloudformation delete-stack \
  --stack-name three-tier-app \
  --region ap-northeast-1
```

## 9. 出力値

| 出力名 | 説明 |
|--------|------|
| ALBDNSName | ALBのDNS名（アプリケーションアクセスURL） |
| VpcId | VPC ID |
| RDSEndpoint | RDSエンドポイント |
