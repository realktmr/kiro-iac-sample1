# WEB三層アーキテクチャ 設計ドキュメント

## 概要

ALB → EC2 (Apache) → RDS (MySQL) のWEB三層アーキテクチャをCloudFormationで構築する。

## アーキテクチャ図

```
Internet
    │
    ▼
┌─────────┐
│   ALB   │  (Public Subnet x2)
└────┬────┘
     │
     ▼
┌─────────┐
│   EC2   │  (Private Subnet x2 / Apache + Hello World)
└────┬────┘
     │
     ▼
┌─────────┐
│   RDS   │  (Private Subnet x2 / MySQL 8.0)
└─────────┘
```

## リージョン・AZ構成

| 項目 | 値 |
|------|-----|
| リージョン | ap-northeast-1 (東京) |
| AZ-a | ap-northeast-1a |
| AZ-c | ap-northeast-1c |

## ネットワーク設計

| サブネット | CIDR | 用途 |
|-----------|------|------|
| VPC | 10.0.0.0/16 | 全体 |
| Public Subnet 1 (AZ-a) | 10.0.1.0/24 | ALB, NAT Gateway |
| Public Subnet 2 (AZ-c) | 10.0.2.0/24 | ALB |
| Private Subnet 1 (AZ-a) | 10.0.10.0/24 | EC2 |
| Private Subnet 2 (AZ-c) | 10.0.20.0/24 | EC2 |
| DB Subnet 1 (AZ-a) | 10.0.100.0/24 | RDS |
| DB Subnet 2 (AZ-c) | 10.0.200.0/24 | RDS |

## コンポーネント詳細

### ALB (Application Load Balancer)

- スキーム: internet-facing
- リスナー: HTTP (80)
- ヘルスチェック: / (HTTP 200)
- クロスゾーン負荷分散: 有効

### EC2

- AMI: Amazon Linux 2023 (SSMパラメータで最新取得)
- インスタンスタイプ: t3.micro (パラメータで変更可)
- 配置: Private Subnet
- UserDataでApacheインストール・Hello Worldページ配置
- NAT Gateway経由でインターネットアクセス

### RDS (MySQL)

- エンジン: MySQL 8.0
- インスタンスクラス: db.t3.micro (パラメータで変更可)
- Multi-AZ: 無効 (検証用)
- ストレージ: 20GB gp3
- 自動バックアップ: 7日間
- 削除保護: 無効 (検証用)

## セキュリティグループ設計

| SG | インバウンド | ソース |
|----|------------|--------|
| ALB SG | TCP 80 | 0.0.0.0/0 |
| EC2 SG | TCP 80 | ALB SG |
| RDS SG | TCP 3306 | EC2 SG |

## パラメータ一覧

| パラメータ | デフォルト値 | 説明 |
|-----------|------------|------|
| EnvironmentName | dev | 環境名 |
| EC2InstanceType | t3.micro | EC2インスタンスタイプ |
| DBInstanceClass | db.t3.micro | RDSインスタンスクラス |
| DBMasterUsername | admin | DBマスターユーザー名 |
| DBMasterPassword | (入力必須) | DBマスターパスワード |
| DBName | appdb | DB名 |
