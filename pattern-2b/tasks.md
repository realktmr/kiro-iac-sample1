# 実装計画: Well-Architected 3層アーキテクチャ CloudFormation テンプレート

## 概要

AWS Well-Architected Framework 6本柱に準拠した WEB三層アーキテクチャ（ALB → EC2 Apache → RDS MySQL 8.0）の CloudFormation テンプレートを単一 YAML ファイルとして実装する。テンプレート作成後、Python（pytest + Hypothesis）によるユニットテスト・プロパティベーステストを実装する。

## タスク

- [x] 1. テンプレート骨格とパラメータ定義の作成
  - [x] 1.1 `template.yaml` を作成し、AWSTemplateFormatVersion、Description、Metadata セクションを定義する
    - AWSTemplateFormatVersion: '2010-09-09' を指定
    - Description にアーキテクチャ概要を記載
    - Metadata に AWS::CloudFormation::Interface でパラメータグループ（環境設定、EC2設定、RDS設定、通知設定）を定義
    - _要件: 10.2, 10.3, 8.6_
  - [x] 1.2 Parameters セクションを定義する
    - EnvironmentName（dev/stg/prod、デフォルト: prod）
    - ProjectName（デフォルト: web3tier）
    - EC2InstanceType（AllowedValues: t4g.micro, t4g.small, t4g.medium, t4g.large、デフォルト: t4g.micro）
    - RDSInstanceClass（AllowedValues: db.t4g.micro, db.t4g.small, db.t4g.medium, db.t4g.large、デフォルト: db.t4g.micro）
    - NotificationEmail（アラーム通知先）
    - RDSAllocatedStorage（デフォルト: 20）
    - _要件: 8.1, 8.2, 8.3, 4.8, 5.8, 6.4, 9.4_

- [x] 2. VPC ネットワーク基盤の実装
  - [x] 2.1 VPC、InternetGateway、VPCGatewayAttachment を定義する
    - VPC CIDR: 10.0.0.0/16
    - DNS サポート・DNS ホスト名を有効化
    - Environment, Project, ManagedBy タグを付与
    - _要件: 1.1, 1.5, 8.4_
  - [x] 2.2 6つのサブネットを定義する
    - PublicSubnet1 (10.0.1.0/24, AZ-1a), PublicSubnet2 (10.0.2.0/24, AZ-1c)
    - PrivateWebSubnet1 (10.0.11.0/24, AZ-1a), PrivateWebSubnet2 (10.0.12.0/24, AZ-1c)
    - PrivateDBSubnet1 (10.0.21.0/24, AZ-1a), PrivateDBSubnet2 (10.0.22.0/24, AZ-1c)
    - 全サブネットにタグを付与
    - _要件: 1.2, 1.3, 1.4, 8.4_
  - [x] 2.3 NAT Gateway、Elastic IP、ルートテーブル、ルートを定義する
    - NAT Gateway を PublicSubnet1 に配置（コスト最適化）
    - パブリックルートテーブル: 0.0.0.0/0 → IGW
    - プライベートルートテーブル: 0.0.0.0/0 → NAT Gateway
    - 各サブネットにルートテーブルを関連付け
    - _要件: 1.6, 1.7, 9.3_
  - [x] 2.4 VPC フローログを定義する
    - VPCFlowLog リソースを作成し CloudWatch Logs に送信
    - VPCFlowLogGroup（RetentionInDays: 90）を作成
    - VPCFlowLogRole（CloudWatch Logs 書き込み権限）を作成
    - _要件: 1.8, 6.5, 7.4_

- [x] 3. セキュリティグループの実装
  - [x] 3.1 ALB 用、EC2 用、RDS 用セキュリティグループを定義する
    - ALB SG: インバウンド TCP 80, 443 (0.0.0.0/0)、アウトバウンド TCP 80 (EC2 SG)
    - EC2 SG: インバウンド TCP 80 (ALB SG)、アウトバウンド TCP 3306 (RDS SG), TCP 443 (0.0.0.0/0)
    - RDS SG: インバウンド TCP 3306 (EC2 SG)、アウトバウンドなし
    - 全セキュリティグループにタグを付与
    - _要件: 2.1, 2.2, 2.3, 2.4, 8.4_

- [x] 4. IAM ロールとポリシーの実装
  - [x] 4.1 EC2 用 IAM ロールとインスタンスプロファイルを定義する
    - CloudWatch Logs へのログ送信権限
    - SSM Session Manager 接続権限
    - ワイルドカード `*` を避け具体的な ARN を指定
    - _要件: 7.1, 7.2, 7.5_
  - [x] 4.2 RDS 拡張モニタリング用 IAM ロールを定義する
    - AmazonRDSEnhancedMonitoringRole マネージドポリシーをアタッチ
    - _要件: 7.3_

- [x] 5. チェックポイント - ネットワーク・セキュリティ基盤の確認
  - テンプレートの YAML 構文を確認し、全てのネットワーク・セキュリティリソースが正しく定義されていることを検証する。ユーザーに質問があれば確認する。

- [x] 6. ALB（プレゼンテーション層）の実装
  - [x] 6.1 ALB アクセスログ用 S3 バケットとバケットポリシーを定義する
    - ELB サービスからの書き込みを許可するバケットポリシー
    - DeletionPolicy: Retain を設定
    - _要件: 3.4_
  - [x] 6.2 ALB、HTTP リスナー、ターゲットグループを定義する
    - ALB: internet-facing スキーム、2つのパブリックサブネットに配置
    - 削除保護を有効化
    - アクセスログを S3 バケットに保存
    - HTTP リスナー（ポート80）→ ターゲットグループへ転送
    - ターゲットグループ: ヘルスチェックパス「/」、HTTP 200 確認
    - _要件: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 8.4_

- [x] 7. EC2 Auto Scaling（アプリケーション層）の実装
  - [x] 7.1 起動テンプレートを定義する
    - UserData: Apache インストール・起動スクリプト
    - IMDSv2 強制（HttpTokens: required）
    - EBS ボリューム暗号化有効化
    - EC2 用インスタンスプロファイルを関連付け
    - _要件: 4.1, 4.5, 4.6, 4.7_
  - [x] 7.2 Auto Scaling グループとスケーリングポリシーを定義する
    - 2つのプライベート Web サブネットに配置
    - Min: 2, Max: 4, Desired: 2
    - CPU 使用率 70% ターゲット追跡スケーリングポリシー
    - UpdatePolicy: AutoScalingRollingUpdate（MinInstancesInService: 1, MaxBatchSize: 1）
    - ALB ターゲットグループに関連付け
    - _要件: 4.2, 4.3, 4.4, 9.1_

- [x] 8. RDS MySQL 8.0（データ層）の実装
  - [x] 8.1 Secrets Manager シークレットと KMS キーを定義する
    - GenerateSecretString でマスターユーザー認証情報を自動生成
    - ExcludeCharacters: '"@/\\'
    - KMS キー（DeletionPolicy: Retain）
    - _要件: 5.7_
  - [x] 8.2 DB サブネットグループと RDS インスタンスを定義する
    - DB サブネットグループ: 2つの DB 層プライベートサブネット
    - MySQL 8.0 エンジン、Multi-AZ 有効
    - GP3 ストレージ、ストレージ暗号化（KMS）
    - 自動バックアップ保持期間: 7日
    - 削除保護有効、DeletionPolicy: Snapshot
    - パフォーマンスインサイト有効
    - 拡張モニタリング有効（間隔: 60秒）
    - SecretTargetAttachment で Secret と RDS を紐付け
    - _要件: 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.8, 5.9, 5.10, 9.2_

- [x] 9. 監視・通知基盤の実装
  - [x] 9.1 SNS トピックとサブスクリプションを定義する
    - メール通知サブスクリプション（NotificationEmail パラメータ使用）
    - _要件: 6.4_
  - [x] 9.2 CloudWatch Alarm を定義する
    - ALB 5xx エラー率 > 1% アラーム
    - RDS CPU 使用率 > 80% アラーム
    - RDS 空きストレージ < 10GB アラーム
    - 全アラームを SNS トピックに通知
    - _要件: 6.1, 6.2, 6.3_

- [x] 10. Outputs セクションの実装
  - [x] 10.1 スタック出力を定義する
    - VPC ID、ALB DNS 名
    - 各サブネット ID（パブリック2、Web層2、DB層2）
    - RDS エンドポイント、Secrets Manager ARN
    - _要件: 8.5_

- [x] 11. チェックポイント - テンプレート全体の検証
  - cfn-lint でテンプレートの構文検証を実施する。全てのリソースが正しく定義され、依存関係が解決されていることを確認する。ユーザーに質問があれば確認する。

- [x] 12. テスト基盤のセットアップとユニットテストの実装
  - [x] 12.1 テストディレクトリとテスト基盤を作成する
    - `tests/` ディレクトリを作成
    - `tests/conftest.py` にテンプレートを YAML パースする共通フィクスチャを定義
    - `requirements-test.txt` に pytest, hypothesis, pyyaml, cfn-lint を記載
    - _要件: 10.1_
  - [x] 12.2 ユニットテストを実装する（`tests/test_template_unit.py`）
    - VPC CIDR 検証（要件 1.1）
    - サブネット数・CIDR 検証（要件 1.2-1.4）
    - セキュリティグループルール検証（要件 2.1-2.4）
    - ALB スキーム・削除保護検証（要件 3.1, 3.5）
    - ヘルスチェック設定検証（要件 3.3）
    - ASG Min/Max/Desired 検証（要件 4.3）
    - IMDSv2 強制検証（要件 4.5）
    - EBS 暗号化検証（要件 4.6）
    - RDS エンジン・Multi-AZ・暗号化・バックアップ検証（要件 5.1, 5.2, 5.4, 5.5）
    - RDS 削除保護検証（要件 5.6）
    - CloudWatch Alarm 閾値検証（要件 6.1-6.3）
    - AWSTemplateFormatVersion 検証（要件 10.2）
    - Metadata 存在検証（要件 10.3）
    - Outputs 検証（要件 8.5）
    - _要件: 1.1, 1.2-1.4, 2.1-2.4, 3.1, 3.3, 3.5, 4.3, 4.5, 4.6, 5.1, 5.2, 5.4, 5.5, 5.6, 6.1-6.3, 8.5, 10.2, 10.3_

- [ ] 13. プロパティベーステストの実装
  - [ ]* 13.1 Property 1: YAML ラウンドトリップテストを実装する
    - **Property 1: YAML ラウンドトリップ**
    - テンプレートを YAML パース → シリアライズ → 再パースし、元のデータ構造と等価であることを検証
    - **検証対象: 要件 10.1**
  - [ ]* 13.2 Property 2: 全 LogGroup の保持期間テストを実装する
    - **Property 2: 全 LogGroup の保持期間設定**
    - 全 AWS::Logs::LogGroup リソースの RetentionInDays が 90 であることを検証
    - **検証対象: 要件 6.5**
  - [ ]* 13.3 Property 3: IAM ポリシーのワイルドカード不使用テストを実装する
    - **Property 3: IAM ポリシーのワイルドカード不使用**
    - 全 IAM ポリシーステートメントの Resource に単独の `*` が使用されていないことを検証
    - **検証対象: 要件 7.5**
  - [ ]* 13.4 Property 4: 全リソースのタグ付けテストを実装する
    - **Property 4: 全リソースのタグ付け**
    - タグサポートリソースに Environment タグと Project タグが存在することを検証
    - **検証対象: 要件 8.4**

- [x] 14. 最終チェックポイント - 全テスト実行と最終確認
  - `pytest tests/ -v --tb=short` で全テストを実行し、全てパスすることを確認する。ユーザーに質問があれば確認する。

## 備考

- `*` マーク付きのタスクはオプションであり、MVP では省略可能
- 各タスクは要件定義書の具体的な要件番号を参照しており、トレーサビリティを確保
- チェックポイントでインクリメンタルな検証を実施
- プロパティベーステストは設計書の正当性プロパティに基づく
