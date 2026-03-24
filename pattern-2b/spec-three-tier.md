# WEB三層アーキテクチャ CloudFormation 生成 Spec

## Overview

ALB → EC2（Apache）→ RDS（MySQL 8.0）のWEB三層アーキテクチャをCloudFormationで構築する。
AWS Well-Architected Framework 6本柱すべてに対して最高水準で準拠すること。

---

## Requirements

### 1. ネットワーク設計

- **MUST**: リージョン ap-northeast-1、AZ ap-northeast-1a / ap-northeast-1c の2AZ構成
- **MUST**: VPC（10.0.0.0/16）を作成し、以下6サブネットを配置すること
  - パブリックサブネット ×2（ALB・NAT Gateway用）
  - プライベートサブネット ×2（EC2用）
  - DBサブネット ×2（RDS用）
- **MUST**: NAT Gatewayは1つ（コスト最適化のため冗長化しない）
- **MUST**: EC2・RDSはプライベートサブネットに配置し、インターネットから直接到達できないこと

### 2. セキュリティグループ

- **MUST**: ALB SGはインターネットからの80/443のみ許可
- **MUST**: EC2 SGはALB SGからの80のみ許可（インターネット直接不可）
- **MUST**: RDS SGはEC2 SGからの3306のみ許可

### 3. ALB（Application Load Balancer）

- **MUST**: インターネット向け、パブリックサブネット2つにまたがって配置
- **MUST**: HTTPSリスナー（ポート443）を作成し、ACM証明書をアタッチすること
- **MUST**: HTTPリスナー（ポート80）はHTTPSへリダイレクト（301）すること
- **MUST**: ターゲットグループのヘルスチェックパスは `/health`
- **MUST**: ALBアクセスログをS3に保存すること

### 4. EC2（Webサーバー）

- **MUST**: OS は Amazon Linux 2023、アーキテクチャは **arm64（Gravitonインスタンス）**
- **MUST**: インスタンスタイプは `t4g.small`（Graviton世代）
- **MUST**: Auto Scaling Group（Min:2 / Max:4 / Desired:2）で起動すること
- **MUST**: LaunchTemplateを使用すること
- **MUST**: IMDSv2を強制すること（`HttpTokens: required`）
- **MUST**: EBSボリュームはgp3・20GB・暗号化（KMS）必須
- **MUST**: IAMロールに以下のポリシーをアタッチすること
  - `AmazonSSMManagedInstanceCore`（SSM Session Manager経由のアクセス、SSH鍵不要）
  - `CloudWatchAgentServerPolicy`（CloudWatchエージェント用）
- **MUST**: UserDataでApacheとphp・php-mysqlndをインストールし、DBへの接続確認ページ（index.php）を配置すること
- **MUST**: TargetTrackingScaling（CPU使用率 70%目標）を設定すること

### 5. データベース（RDS MySQL）

- **MUST**: エンジン MySQL 8.0、インスタンスクラス `db.t4g.small`（Graviton世代）
- **MUST**: Multi-AZ 有効
- **MUST**: ストレージ暗号化（StorageEncrypted: true）
- **MUST**: DeletionPolicy は `Snapshot`（削除時にスナップショットを取得）
- **MUST**: バックアップ保持期間 7日間
- **MUST**: ストレージオートスケーリング（MaxAllocatedStorage: 100）
- **MUST**: DBの認証情報（ユーザー名・パスワード）は **AWS Secrets Manager** で管理すること
  - パスワードは32文字以上の自動生成
  - RDSとSecrets Managerのローテーション連携は任意

### 6. セキュリティ強化

- **MUST**: VPC Flow LogsをCloudWatch Logsに記録すること（保持期間30日）
- **MUST**: すべてのEBSボリュームを暗号化すること
- **MUST**: すべてのRDSストレージを暗号化すること
- **MUST**: IAMロールは最小権限原則に基づき、必要なポリシーのみアタッチすること

### 7. 監視・通知（Operational Excellence）

- **MUST**: SNS Topicを作成し、通知先メールアドレスをパラメータで受け取ること
- **MUST**: 以下のCloudWatchアラームをすべてSNS Topicに紐づけること（AlarmActions必須）
  - EC2 CPU使用率 > 80%（5分×2回）
  - RDS CPU使用率 > 80%（5分×2回）
  - ALB UnhealthyHostCount > 0（1分×2回）
  - RDS FreeStorageSpace < 5GB（5分×2回）
- **MUST**: CloudWatchエージェントのカスタムメトリクス取得ができるようIAMロールを設定すること

### 8. コスト最適化

- **MUST**: Graviton（arm64）インスタンスを使用し、x86比でコスト効率を向上させること
- **MUST**: NAT Gatewayは1つに集約すること
- **MUST**: Auto Scalingで不要時のリソースを自動削減すること
- **MUST**: RDSストレージオートスケーリングで過剰プロビジョニングを防ぐこと

### 9. パラメータ

以下をCloudFormationパラメータとして外部から指定可能にすること。

| パラメータ名 | 説明 | デフォルト値 |
|------------|------|------------|
| EnvironmentName | 環境名（タグ・リソース名に使用） | dev |
| VpcCIDR | VPCのCIDRブロック | 10.0.0.0/16 |
| EC2InstanceType | EC2インスタンスタイプ | t4g.small |
| DBInstanceClass | RDSインスタンスクラス | db.t4g.small |
| DBName | データベース名 | appdb |
| DBMasterUsername | DBマスターユーザー名 | admin |
| NotificationEmail | アラーム通知先メールアドレス | （必須入力） |
| CertificateArn | ALBにアタッチするACM証明書ARN | （必須入力） |

### 10. 出力（Outputs）

- ALB DNS名（アクセスURL）
- VPC ID
- RDSエンドポイント
- Secrets Manager ARN

---

## Design Notes

- **HTTPS必須**：HTTPリスナーはHTTPSへのリダイレクトのみ。アプリケーション通信はすべて暗号化。
- **Secrets Manager**：DBパスワードをパラメータで受け取ることを禁止。必ずSecrets Managerで自動生成・管理すること。
- **Graviton優先**：x86（t3系）ではなく arm64（t4g系）インスタンスを使用すること。コストと持続可能性の両面から優れる。
- **通知の実効性**：CloudWatchアラームはAlarmActionsが未設定のままにしてはならない。すべてのアラームにSNS通知を設定すること。
- **SSM前提**：SSH鍵は作成しない。すべてのEC2接続はSSM Session Manager経由とする。

---

## Tasks

1. VPC・サブネット・ルートテーブル・NAT Gatewayの作成
2. セキュリティグループ（ALB・EC2・RDS）の作成
3. ACM証明書ARNを受け取るパラメータ設定とALB（HTTPS/HTTPリスナー）の作成
4. IAMロール（SSM + CloudWatchAgent）とインスタンスプロファイルの作成
5. Secrets Manager（DBパスワード自動生成）の作成
6. EC2 LaunchTemplate（arm64・IMDSv2・EBS暗号化）とAuto Scaling Groupの作成
7. TargetTracking スケーリングポリシーの設定
8. RDS（MySQL 8.0・Multi-AZ・暗号化・Secrets Manager連携）の作成
9. VPC Flow Logs（CloudWatch Logs）の設定
10. SNS TopicとEmailサブスクリプションの作成
11. CloudWatchアラーム4つ（すべてSNS通知付き）の作成
12. Outputsの設定
13. YAMLの構文チェックと検証