# Requirements Document

## Introduction

AWS CloudFormation を使用して、ALB → EC2（Apache）→ RDS（MySQL 8.0）の WEB 三層アーキテクチャを構築するテンプレートを生成する。AWS Well-Architected Framework の6本柱（運用上の優秀性、セキュリティ、信頼性、パフォーマンス効率、コスト最適化、持続可能性）すべてに最高水準で準拠する。

## Glossary

- **CFn_Template**: CloudFormation YAML テンプレートファイル。本機能で生成されるインフラ定義の成果物
- **VPC**: Virtual Private Cloud。10.0.0.0/16 の CIDR ブロックを持つ仮想ネットワーク
- **Public_Subnet**: インターネットゲートウェイへのルートを持つサブネット。ALB および NAT Gateway を配置する
- **Private_Subnet**: NAT Gateway 経由でのみインターネットにアクセス可能なサブネット。EC2 インスタンスを配置する
- **DB_Subnet**: インターネットへのアクセスを持たないサブネット。RDS インスタンスを配置する
- **ALB**: Application Load Balancer。インターネットからのトラフィックを EC2 インスタンスに分散する
- **EC2_Instance**: Amazon Linux 2023（arm64）上で Apache を実行する Web サーバー
- **RDS_Instance**: MySQL 8.0 エンジンを使用するリレーショナルデータベースサービスインスタンス
- **ASG**: Auto Scaling Group。EC2 インスタンスの自動スケーリングを管理するグループ
- **Launch_Template**: EC2 インスタンスの起動設定を定義するテンプレート
- **Security_Group**: VPC 内のリソースへのインバウンド・アウトバウンドトラフィックを制御するファイアウォールルール
- **NAT_Gateway**: プライベートサブネットからインターネットへのアウトバウンド通信を可能にするゲートウェイ
- **Secrets_Manager**: AWS Secrets Manager。DB 認証情報の自動生成・管理・ローテーションを行うサービス
- **SNS_Topic**: Amazon SNS トピック。CloudWatch アラームの通知先として使用する
- **CloudWatch_Alarm**: Amazon CloudWatch アラーム。メトリクスの閾値超過を検知し SNS_Topic に通知する
- **VPC_Flow_Logs**: VPC 内のネットワークトラフィックをキャプチャし CloudWatch Logs に記録する機能
- **SSM_Session_Manager**: AWS Systems Manager Session Manager。SSH 鍵なしで EC2 インスタンスに接続する機能
- **KMS**: AWS Key Management Service。EBS ボリュームおよび RDS ストレージの暗号化に使用する鍵管理サービス

## Requirements

### Requirement 1: VPC およびネットワーク基盤の構築

**User Story:** As a インフラエンジニア, I want CloudFormation で VPC とサブネットを自動構築したい, so that 再現可能で一貫性のあるネットワーク基盤を迅速にデプロイできる

#### Acceptance Criteria

1. THE CFn_Template SHALL create a VPC with the CIDR block specified by the VpcCIDR parameter (default: 10.0.0.0/16) in the ap-northeast-1 region
2. THE CFn_Template SHALL create 2 Public_Subnets in ap-northeast-1a and ap-northeast-1c with MapPublicIpOnLaunch set to true
3. THE CFn_Template SHALL create 2 Private_Subnets in ap-northeast-1a and ap-northeast-1c
4. THE CFn_Template SHALL create 2 DB_Subnets in ap-northeast-1a and ap-northeast-1c
5. THE CFn_Template SHALL create an Internet Gateway and attach it to the VPC
6. THE CFn_Template SHALL create a single NAT_Gateway in one Public_Subnet with an Elastic IP address
7. THE CFn_Template SHALL create a public route table with a default route (0.0.0.0/0) to the Internet Gateway and associate it with both Public_Subnets
8. THE CFn_Template SHALL create a private route table with a default route (0.0.0.0/0) to the NAT_Gateway and associate it with both Private_Subnets and both DB_Subnets
9. WHEN the CFn_Template is deployed, THE VPC SHALL have DNS support and DNS hostnames enabled

### Requirement 2: セキュリティグループの構成

**User Story:** As a セキュリティエンジニア, I want 最小権限の原則に基づいたセキュリティグループを定義したい, so that 各層間の通信を必要最小限に制限できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an ALB Security_Group that allows inbound traffic on ports 80 and 443 from 0.0.0.0/0 only
2. THE CFn_Template SHALL create an EC2 Security_Group that allows inbound traffic on port 80 from the ALB Security_Group only
3. THE CFn_Template SHALL create an RDS Security_Group that allows inbound traffic on port 3306 from the EC2 Security_Group only
4. THE CFn_Template SHALL associate each Security_Group with the VPC created in Requirement 1

### Requirement 3: ALB の構築

**User Story:** As a インフラエンジニア, I want HTTPS 対応の ALB を構築したい, so that ユーザーからの通信を暗号化し安全にバックエンドへ転送できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an internet-facing ALB deployed across both Public_Subnets
2. THE CFn_Template SHALL create an HTTPS listener on port 443 with the ACM certificate specified by the CertificateArn parameter
3. WHEN a request arrives on port 80, THE ALB SHALL redirect the request to HTTPS (port 443) with HTTP status code 301
4. THE CFn_Template SHALL create a target group with health check path set to /health and protocol HTTP on port 80
5. THE CFn_Template SHALL configure ALB access logging to an S3 bucket with a lifecycle policy
6. THE CFn_Template SHALL attach the ALB Security_Group to the ALB

### Requirement 4: EC2 Web サーバーの構築

**User Story:** As a インフラエンジニア, I want Graviton ベースの EC2 インスタンスで Apache Web サーバーを自動構築したい, so that コスト効率の高い Web サーバー層を実現できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create a Launch_Template with Amazon Linux 2023 arm64 AMI and the instance type specified by the EC2InstanceType parameter (default: t4g.small)
2. THE Launch_Template SHALL enforce IMDSv2 by setting HttpTokens to required and HttpPutResponseHopLimit to 2
3. THE Launch_Template SHALL configure an EBS root volume of type gp3, size 20 GB, with KMS encryption enabled
4. THE Launch_Template SHALL include UserData that installs Apache (httpd) and php with php-mysqlnd, starts the httpd service, and deploys an index.php page that verifies database connectivity
5. THE CFn_Template SHALL create an ASG with MinSize 2, MaxSize 4, and DesiredCapacity 2, spanning both Private_Subnets
6. THE CFn_Template SHALL associate the ASG with the ALB target group created in Requirement 3
7. THE CFn_Template SHALL configure a TargetTrackingScaling policy on the ASG targeting average CPU utilization of 70 percent

### Requirement 5: IAM ロールとインスタンスプロファイルの構築

**User Story:** As a セキュリティエンジニア, I want 最小権限の IAM ロールを EC2 に付与したい, so that SSM 接続と CloudWatch メトリクス送信のみを許可し不要な権限を排除できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an IAM Role for EC2 with AssumeRolePolicyDocument allowing ec2.amazonaws.com to assume the role
2. THE CFn_Template SHALL attach the AmazonSSMManagedInstanceCore managed policy to the IAM Role
3. THE CFn_Template SHALL attach the CloudWatchAgentServerPolicy managed policy to the IAM Role
4. THE CFn_Template SHALL create an Instance Profile and associate it with the IAM Role
5. THE Launch_Template SHALL reference the Instance Profile for all EC2_Instances launched by the ASG

### Requirement 6: Secrets Manager による DB 認証情報管理

**User Story:** As a セキュリティエンジニア, I want DB パスワードを Secrets Manager で自動生成・管理したい, so that 認証情報がテンプレートやパラメータに平文で含まれることを防止できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create a Secrets_Manager secret with an auto-generated password of 32 characters or more
2. THE Secrets_Manager secret SHALL exclude characters that are incompatible with MySQL passwords (quotes, backslash, at-sign, slash)
3. THE CFn_Template SHALL reference the Secrets_Manager secret for the RDS_Instance MasterUserPassword property
4. THE CFn_Template SHALL NOT accept the database password as a CloudFormation parameter

### Requirement 7: RDS MySQL データベースの構築

**User Story:** As a インフラエンジニア, I want Multi-AZ 対応の暗号化された RDS MySQL インスタンスを構築したい, so that 高可用性とデータ保護を両立したデータベース層を実現できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an RDS_Instance with MySQL 8.0 engine and the instance class specified by the DBInstanceClass parameter (default: db.t4g.small)
2. THE RDS_Instance SHALL have Multi-AZ enabled
3. THE RDS_Instance SHALL have StorageEncrypted set to true
4. THE RDS_Instance SHALL have a DeletionPolicy of Snapshot
5. THE RDS_Instance SHALL have BackupRetentionPeriod set to 7 days
6. THE RDS_Instance SHALL have MaxAllocatedStorage set to 100 for storage auto-scaling
7. THE CFn_Template SHALL create a DB Subnet Group using both DB_Subnets
8. THE RDS_Instance SHALL be associated with the RDS Security_Group and the DB Subnet Group
9. THE RDS_Instance SHALL use the database name specified by the DBName parameter (default: appdb) and the master username specified by the DBMasterUsername parameter (default: admin)

### Requirement 8: VPC Flow Logs の設定

**User Story:** As a セキュリティエンジニア, I want VPC のネットワークトラフィックを記録したい, so that セキュリティインシデント発生時に通信ログを調査できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create VPC_Flow_Logs that capture all traffic (ALL) for the VPC
2. THE VPC_Flow_Logs SHALL deliver logs to a CloudWatch Logs log group
3. THE CloudWatch Logs log group SHALL have a retention period of 30 days
4. THE CFn_Template SHALL create an IAM Role for VPC_Flow_Logs with permissions to publish logs to CloudWatch Logs

### Requirement 9: 監視・通知の構築

**User Story:** As a 運用エンジニア, I want CloudWatch アラームと SNS 通知を設定したい, so that インフラの異常を即座に検知しメールで通知を受け取れる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an SNS_Topic and an email subscription using the NotificationEmail parameter
2. THE CFn_Template SHALL create a CloudWatch_Alarm for EC2 CPU utilization exceeding 80 percent, evaluated over 2 consecutive periods of 5 minutes, with AlarmActions set to the SNS_Topic
3. THE CFn_Template SHALL create a CloudWatch_Alarm for RDS CPU utilization exceeding 80 percent, evaluated over 2 consecutive periods of 5 minutes, with AlarmActions set to the SNS_Topic
4. THE CFn_Template SHALL create a CloudWatch_Alarm for ALB UnhealthyHostCount exceeding 0, evaluated over 2 consecutive periods of 1 minute, with AlarmActions set to the SNS_Topic
5. THE CFn_Template SHALL create a CloudWatch_Alarm for RDS FreeStorageSpace falling below 5 GB, evaluated over 2 consecutive periods of 5 minutes, with AlarmActions set to the SNS_Topic

### Requirement 10: CloudFormation パラメータの定義

**User Story:** As a インフラエンジニア, I want テンプレートのパラメータを外部から指定可能にしたい, so that 環境ごとに異なる設定値で同一テンプレートを再利用できる

#### Acceptance Criteria

1. THE CFn_Template SHALL define an EnvironmentName parameter of type String with default value "dev"
2. THE CFn_Template SHALL define a VpcCIDR parameter of type String with default value "10.0.0.0/16"
3. THE CFn_Template SHALL define an EC2InstanceType parameter of type String with default value "t4g.small"
4. THE CFn_Template SHALL define a DBInstanceClass parameter of type String with default value "db.t4g.small"
5. THE CFn_Template SHALL define a DBName parameter of type String with default value "appdb"
6. THE CFn_Template SHALL define a DBMasterUsername parameter of type String with default value "admin"
7. THE CFn_Template SHALL define a NotificationEmail parameter of type String with no default value
8. THE CFn_Template SHALL define a CertificateArn parameter of type String with no default value


### Requirement 11: CloudFormation 出力の定義

**User Story:** As a インフラエンジニア, I want スタックの主要リソース情報を Outputs で確認したい, so that デプロイ後に必要な接続情報を即座に取得できる

#### Acceptance Criteria

1. THE CFn_Template SHALL output the ALB DNS name as the application access URL
2. THE CFn_Template SHALL output the VPC ID
3. THE CFn_Template SHALL output the RDS endpoint address
4. THE CFn_Template SHALL output the Secrets_Manager secret ARN

### Requirement 12: コスト最適化

**User Story:** As a インフラエンジニア, I want コスト効率の高いリソース構成を採用したい, so that 不要なコストを削減しつつ必要な性能と可用性を維持できる

#### Acceptance Criteria

1. THE CFn_Template SHALL use Graviton (arm64) instance types for both EC2_Instances and RDS_Instance
2. THE CFn_Template SHALL deploy a single NAT_Gateway to minimize fixed costs
3. THE ASG SHALL automatically scale EC2_Instances based on demand to avoid over-provisioning
4. THE RDS_Instance SHALL use storage auto-scaling to prevent excessive storage provisioning

### Requirement 13: ALB アクセスログ用 S3 バケットの構築

**User Story:** As a セキュリティエンジニア, I want ALB のアクセスログを S3 に安全に保存したい, so that アクセスパターンの分析やセキュリティ監査に活用できる

#### Acceptance Criteria

1. THE CFn_Template SHALL create an S3 bucket for ALB access logs with a unique bucket name derived from the stack name
2. THE S3 bucket SHALL have BucketEncryption enabled with SSE-S3 (AES256)
3. THE S3 bucket SHALL have PublicAccessBlock configured to block all public access
4. THE S3 bucket SHALL have a bucket policy that grants the ELB service account (for ap-northeast-1) permission to write access logs
5. THE S3 bucket SHALL have versioning enabled

### Requirement 14: リソースタグ付け

**User Story:** As a インフラエンジニア, I want すべてのリソースに一貫したタグを付与したい, so that コスト配分やリソース管理を容易にできる

#### Acceptance Criteria

1. THE CFn_Template SHALL tag all taggable resources with an "Environment" tag using the EnvironmentName parameter value
2. THE CFn_Template SHALL tag all taggable resources with a "Project" tag with value "WebThreeTier"
3. THE CFn_Template SHALL use the EnvironmentName parameter in resource naming where applicable

### Requirement 15: YAML テンプレートの構文整合性

**User Story:** As a インフラエンジニア, I want 構文的に正しい CloudFormation テンプレートを生成したい, so that デプロイ時にテンプレートエラーが発生しないことを保証できる

#### Acceptance Criteria

1. THE CFn_Template SHALL be a valid YAML document conforming to the AWS CloudFormation template syntax
2. THE CFn_Template SHALL use AWSTemplateFormatVersion "2010-09-09"
3. THE CFn_Template SHALL include a Description field summarizing the stack purpose
4. THE CFn_Template SHALL use Fn::Sub, Fn::Ref, Fn::GetAtt, and Fn::Select intrinsic functions correctly where cross-resource references are needed
