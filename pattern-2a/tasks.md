# Implementation Plan: WEB三層アーキテクチャ CloudFormation テンプレート

## Overview

ALB → EC2（Apache）→ RDS（MySQL 8.0）の WEB 三層アーキテクチャを構築する CloudFormation YAML テンプレート（`template.yaml`）を段階的に実装する。各タスクは前のタスクの成果物に依存し、最終的にすべてのリソースが統合された単一テンプレートを完成させる。テストは Python（pytest + PyYAML + Hypothesis）で実施する。

## Tasks

- [x] 1. テンプレート骨格と VPC・ネットワーク基盤の作成
  - [x] 1.1 テンプレート骨格（AWSTemplateFormatVersion, Description）と全パラメータ定義（8つ）を作成する
    - `template.yaml` を新規作成し、AWSTemplateFormatVersion: "2010-09-09"、Description を記述する
    - Parameters セクションに EnvironmentName, VpcCIDR, EC2InstanceType, DBInstanceClass, DBName, DBMasterUsername, NotificationEmail, CertificateArn を定義する
    - 各パラメータにデフォルト値、Type、AllowedPattern（該当するもの）を設定する
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6, 10.7, 10.8, 15.2, 15.3_
  - [x] 1.2 VPC、サブネット（6つ）、Internet Gateway、NAT Gateway、ルートテーブル、ルート、サブネット関連付けを作成する
    - VPC（DNS サポート・ホスト名有効）を作成する
    - Public Subnet x2（ap-northeast-1a, 1c、MapPublicIpOnLaunch: true）を作成する
    - Private Subnet x2（ap-northeast-1a, 1c）を作成する
    - DB Subnet x2（ap-northeast-1a, 1c）を作成する
    - Internet Gateway を作成し VPC にアタッチする
    - EIP と NAT Gateway（Public Subnet 1a に配置）を作成する
    - Public Route Table（IGW へのデフォルトルート）を作成し Public Subnet x2 に関連付ける
    - Private Route Table（NAT GW へのデフォルトルート）を作成し Private Subnet x2 + DB Subnet x2 に関連付ける
    - すべてのリソースに Environment タグと Project タグを付与する
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 1.6, 1.7, 1.8, 1.9, 14.1, 14.2, 14.3_

- [x] 2. セキュリティグループの作成
  - [x] 2.1 ALB・EC2・RDS の3つのセキュリティグループを作成する
    - ALB SG: TCP 80, 443 を 0.0.0.0/0 から許可
    - EC2 SG: TCP 80 を ALB SG から許可
    - RDS SG: TCP 3306 を EC2 SG から許可
    - 各 SG を VPC に関連付け、Environment タグと Project タグを付与する
    - _Requirements: 2.1, 2.2, 2.3, 2.4, 14.1, 14.2_

- [x] 3. ALB とリスナーの作成
  - [x] 3.1 ALB アクセスログ用 S3 バケットを作成する
    - バケット名: `!Sub "${AWS::StackName}-alb-access-logs-${AWS::AccountId}"`
    - SSE-S3（AES256）暗号化を有効にする
    - PublicAccessBlock で全ブロック有効にする
    - バージョニングを有効にする
    - ELB サービスアカウント（582318560864）からの書き込みを許可するバケットポリシーを作成する
    - _Requirements: 13.1, 13.2, 13.3, 13.4, 13.5_
  - [x] 3.2 ALB、ターゲットグループ、HTTPS/HTTP リスナーを作成する
    - Internet-facing ALB を Public Subnet x2 にデプロイし、ALB SG をアタッチする
    - ALB アクセスログを S3 バケットに出力する設定を追加する
    - ターゲットグループ（HTTP:80、ヘルスチェック: /health）を作成する
    - HTTPS:443 リスナー（ACM 証明書使用、ターゲットグループへフォワード）を作成する
    - HTTP:80 リスナー（HTTPS へ 301 リダイレクト）を作成する
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 14.1, 14.2_

- [x] 4. IAM ロールとインスタンスプロファイルの作成
  - [x] 4.1 EC2 用 IAM ロールとインスタンスプロファイルを作成する
    - ec2.amazonaws.com を信頼する IAM ロールを作成する
    - AmazonSSMManagedInstanceCore マネージドポリシーをアタッチする
    - CloudWatchAgentServerPolicy マネージドポリシーをアタッチする
    - インスタンスプロファイルを作成し IAM ロールを関連付ける
    - _Requirements: 5.1, 5.2, 5.3, 5.4_

- [x] 5. Secrets Manager シークレットの作成
  - [x] 5.1 DB パスワード自動生成用の Secrets Manager シークレットを作成する
    - 32文字以上の自動生成パスワードを設定する
    - MySQL 非互換文字（`"'@/\`）を除外する
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [x] 6. EC2 Launch Template と Auto Scaling Group の作成
  - [x] 6.1 Launch Template を作成する
    - Amazon Linux 2023 arm64 AMI（SSM パラメータで解決）を指定する
    - IMDSv2 強制（HttpTokens=required, HttpPutResponseHopLimit=2）を設定する
    - EBS: gp3, 20GB, KMS 暗号化を設定する
    - EC2 SG とインスタンスプロファイルを関連付ける
    - UserData で Apache + PHP + php-mysqlnd インストール、httpd 起動、index.php デプロイを行う
    - _Requirements: 4.1, 4.2, 4.3, 4.4, 5.5, 14.1, 14.2_
  - [x] 6.2 Auto Scaling Group を作成する
    - MinSize: 2, MaxSize: 4, DesiredCapacity: 2 で Private Subnet x2 に配置する
    - ALB ターゲットグループに関連付ける
    - _Requirements: 4.5, 4.6, 12.3_
  - [x] 6.3 TargetTracking スケーリングポリシーを作成する
    - CPU 平均使用率 70% をターゲットとする TargetTrackingScaling ポリシーを設定する
    - _Requirements: 4.7_

- [x] 7. Checkpoint - テンプレートの中間検証
  - Ensure all tests pass, ask the user if questions arise.

- [x] 8. RDS MySQL インスタンスの作成
  - [x] 8.1 DB Subnet Group と RDS インスタンスを作成する
    - DB Subnet Group を DB Subnet x2 で作成する
    - MySQL 8.0 エンジン、Multi-AZ 有効、ストレージ暗号化有効で RDS インスタンスを作成する
    - DeletionPolicy: Snapshot を設定する
    - BackupRetentionPeriod: 7、MaxAllocatedStorage: 100 を設定する
    - Secrets Manager シークレットから MasterUserPassword を参照する
    - RDS SG と DB Subnet Group を関連付ける
    - DBName、DBMasterUsername パラメータを参照する
    - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.7, 7.8, 7.9, 6.3, 12.1, 12.4, 14.1, 14.2_

- [x] 9. VPC Flow Logs の設定
  - [x] 9.1 VPC Flow Logs と関連リソースを作成する
    - CloudWatch Logs ロググループ（保持期間 30日）を作成する
    - VPC Flow Logs 用 IAM ロール（vpc-flow-logs.amazonaws.com 信頼、CloudWatch Logs 書き込み権限）を作成する
    - VPC Flow Logs（ALL トラフィック、CloudWatch Logs 送信先）を作成する
    - _Requirements: 8.1, 8.2, 8.3, 8.4_

- [x] 10. SNS Topic と CloudWatch アラームの作成
  - [x] 10.1 SNS Topic と Email サブスクリプションを作成する
    - SNS Topic を作成する
    - NotificationEmail パラメータを使用した Email サブスクリプションを作成する
    - _Requirements: 9.1_
  - [x] 10.2 CloudWatch アラーム4つを作成する
    - EC2 CPU 使用率アラーム（> 80%、5分 x 2回、SNS 通知）を作成する
    - RDS CPU 使用率アラーム（> 80%、5分 x 2回、SNS 通知）を作成する
    - ALB UnhealthyHostCount アラーム（> 0、1分 x 2回、SNS 通知）を作成する
    - RDS FreeStorageSpace アラーム（< 5GB、5分 x 2回、SNS 通知）を作成する
    - _Requirements: 9.2, 9.3, 9.4, 9.5_

- [x] 11. Outputs セクションの作成
  - [x] 11.1 CloudFormation 出力を定義する
    - ALB DNS 名（アプリケーションアクセス URL）を出力する
    - VPC ID を出力する
    - RDS エンドポイントアドレスを出力する
    - Secrets Manager シークレット ARN を出力する
    - _Requirements: 11.1, 11.2, 11.3, 11.4_

- [x] 12. Checkpoint - テンプレート完成検証
  - Ensure all tests pass, ask the user if questions arise.

- [x] 13. YAML 構文チェックとユニットテストの作成
  - [x] 13.1 テスト環境をセットアップする
    - `tests/` ディレクトリを作成する
    - `requirements-test.txt` に pytest, pyyaml, hypothesis を記載する
  - [x] 13.2 ユニットテストを作成する（`tests/test_template_unit.py`）
    - YAML パース可能性の検証テストを作成する
    - AWSTemplateFormatVersion と Description の存在検証テストを作成する
    - 全8パラメータの定義・デフォルト値検証テストを作成する
    - VPC・サブネット・ルートテーブル等ネットワークリソースの検証テストを作成する
    - セキュリティグループのルール検証テストを作成する
    - ALB・リスナー・ターゲットグループの検証テストを作成する
    - IAM ロール・インスタンスプロファイルの検証テストを作成する
    - Secrets Manager シークレットの検証テストを作成する
    - Launch Template（IMDSv2、EBS 暗号化）の検証テストを作成する
    - ASG・スケーリングポリシーの検証テストを作成する
    - RDS インスタンス（Multi-AZ、暗号化、バックアップ）の検証テストを作成する
    - VPC Flow Logs の検証テストを作成する
    - SNS・CloudWatch アラームの検証テストを作成する
    - S3 バケット（暗号化、パブリックアクセスブロック）の検証テストを作成する
    - Outputs の検証テストを作成する
    - _Requirements: 1.1〜15.4_
  - [x] 13.3 プロパティベーステストを作成する（`tests/test_template_properties.py`）
    - **Property 1: 全タグ付け可能リソースに必須タグが存在する**
    - **Validates: Requirements 14.1, 14.2**
  - [x] 13.4 プロパティベーステストを作成する（`tests/test_template_properties.py`）
    - **Property 2: 全セキュリティグループが VPC に関連付けられている**
    - **Validates: Requirements 2.4**
  - [x] 13.5 プロパティベーステストを作成する（`tests/test_template_properties.py`）
    - **Property 3: パスワード系パラメータが存在しない**
    - **Validates: Requirements 6.4**
  - [x] 13.6 プロパティベーステストを作成する（`tests/test_template_properties.py`）
    - **Property 4: テンプレートの構造的整合性（Ref/GetAtt 参照先の存在検証）**
    - **Validates: Requirements 15.1, 15.4**
  - [x] 13.7 プロパティベーステストを作成する（`tests/test_template_properties.py`）
    - **Property 5: 全コンピュートリソースが Graviton (arm64) を使用する**
    - **Validates: Requirements 12.1**

- [x] 14. Final checkpoint - 最終検証
  - Ensure all tests pass, ask the user if questions arise.

## Notes

- タスクに `*` が付いているものはオプションであり、MVP では省略可能です
- 各タスクは特定の要件を参照しており、トレーサビリティを確保しています
- チェックポイントで段階的な検証を行います
- プロパティテストは設計書の Correctness Properties（Property 1〜5）に対応しています
- ユニットテストは各受け入れ基準の具体的な検証を行います
- テンプレートは単一ファイル（`template.yaml`）として実装します
- テストは Python（pytest + PyYAML + Hypothesis）で実施します
