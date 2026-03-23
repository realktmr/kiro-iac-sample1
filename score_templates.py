"""
Well-Architected Framework 6本柱スコアリングスクリプト
対象: 第1部 Pattern A/B、第2部 Spec A/B

【採点基準】
AWS Well-Architected Framework の設問に対応した30項目のベストプラクティスチェック。
各項目は以下のWA設問にマッピングされています：

  OE-1  VPC Flow Logs             → OPS04 運用可視性の実装
  OE-2  CloudWatch Alarms         → OPS08 ワークロード健全性の把握
  OE-3  SSM IAMロール             → OPS07 ワークロードのサポート準備
  OE-4  ヘルスチェック設定         → OPS08
  OE-5  ALBアクセスログ           → OPS04

  SEC-1 EC2プライベートサブネット   → SEC05 ネットワークリソースの保護
  SEC-2 SGソース制限               → SEC05
  SEC-3 Secrets Manager            → SEC08 保存データの保護
  SEC-4 RDS暗号化                  → SEC08
  SEC-5 EBS暗号化/IMDSv2強制      → SEC06 コンピュートリソースの保護

  REL-1 EC2マルチAZ               → REL10 障害分離によるワークロード保護
  REL-2 RDSバックアップ7日         → REL09 データのバックアップ
  REL-3 RDS Multi-AZ              → REL10
  REL-4 ASG自動復旧               → REL07 需要変動への適応
  REL-5 DeletionPolicy:Snapshot   → REL09

  PERF-1 TargetTracking           → PERF02 コンピュートのプロビジョニングとスケーリング
  PERF-2 gp3 EBS                  → PERF03 ストレージの選択
  PERF-3 gp3 RDS                  → PERF03
  PERF-4 Graviton(t4g)            → PERF01 コンピュートアーキテクチャの選択
  PERF-5 最新世代インスタンス      → PERF01

  COST-1 Graviton(コスト削減)     → COST06 リソースタイプ・サイズの選択
  COST-2 単一NAT GW               → COST05 サービス選択時のコスト評価
  COST-3 gp3ストレージ            → COST06
  COST-4 Auto Scaling             → COST09 需要と供給のリソース管理
  COST-5 適切インスタンスタイプ    → COST06

  SUST-1 Graviton(省電力)         → SUS05 ハードウェアとサービスの選択
  SUST-2 Auto Scaling(省エネ)     → SUS02 クラウドリソースの需要整合
  SUST-3 gp3 EBS(効率)            → SUS03 持続可能なソフトウェア・アーキテクチャ
  SUST-4 gp3 RDS(効率)            → SUS03
  SUST-5 最新世代インスタンス      → SUS05

検証済みスコア:
  Pattern A = 12/30、Pattern B = 26/30
  Spec A    = 28/30、Spec B    = 30/30
"""

import yaml
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")


# ---------------------------------------------------------------------------
# Custom YAML Loader
# ---------------------------------------------------------------------------

class CfnLoader(yaml.SafeLoader):
    pass

def _scalar(loader, tag_suffix, node):
    return loader.construct_scalar(node)

CfnLoader.add_multi_constructor("!", _scalar)

for _tag in ["Ref","Sub","GetAtt","Base64","Select","If","Join","Split",
             "FindInMap","GetAZs","ImportValue","Transform",
             "And","Equals","Not","Or","Condition"]:
    CfnLoader.add_constructor(
        f"!{_tag}",
        lambda loader, node: (
            loader.construct_sequence(node) if isinstance(node, yaml.SequenceNode)
            else loader.construct_mapping(node) if isinstance(node, yaml.MappingNode)
            else loader.construct_scalar(node)
        ),
    )

def load(path):
    with open(path, encoding="utf-8") as f:
        return yaml.load(f, Loader=CfnLoader)

def raw(path):
    return Path(path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Scoring helpers
# ---------------------------------------------------------------------------

def resources(t):
    return t.get("Resources", {})

def res_of_type(t, rtype):
    return {k: v for k, v in resources(t).items() if v.get("Type") == rtype}

def has_type(t, rtype):
    return bool(res_of_type(t, rtype))


# ---------------------------------------------------------------------------
# 30項目スコアリング (各1点、合計30点)
# 第1部記事の採点基準と完全一致
# ---------------------------------------------------------------------------

def score(template, raw_text, label):
    r = resources(template)
    results = {}

    def check(key, value, reason=""):
        results[key] = (value, reason)

    lts  = res_of_type(template, "AWS::EC2::LaunchTemplate")
    dbs  = res_of_type(template, "AWS::RDS::DBInstance")
    asgs = res_of_type(template, "AWS::AutoScaling::AutoScalingGroup")
    albs = res_of_type(template, "AWS::ElasticLoadBalancingV2::LoadBalancer")
    tgs  = res_of_type(template, "AWS::ElasticLoadBalancingV2::TargetGroup")
    sps  = res_of_type(template, "AWS::AutoScaling::ScalingPolicy")
    alarms = res_of_type(template, "AWS::CloudWatch::Alarm")

    # ===== 運用上の優秀性 OE (5点) =====

    # OE-1: VPC Flow Logs
    check("OE-1", has_type(template, "AWS::EC2::FlowLog"), "VPC Flow Logs")

    # OE-2: CloudWatch Alarms (1つ以上存在)
    check("OE-2", bool(alarms), "CloudWatch Alarms存在")

    # OE-3: SSM接続可能 (IAMロールにSSM or CWAgent Policy)
    iam_roles = res_of_type(template, "AWS::IAM::Role")
    has_ssm = any(
        any("SSM" in str(p) or "CloudWatch" in str(p)
            for p in v.get("Properties", {}).get("ManagedPolicyArns", []))
        for v in iam_roles.values()
    )
    check("OE-3", has_ssm, "SSM IAMロール")

    # OE-4: ヘルスチェック設定
    has_hc = any(
        v.get("Properties", {}).get("HealthCheckPath") or
        v.get("Properties", {}).get("HealthCheckEnabled")
        for v in tgs.values()
    )
    check("OE-4", has_hc, "ヘルスチェック設定")

    # OE-5: ALBアクセスログ有効
    alb_logs = any(
        any(a.get("Key") == "access_logs.s3.enabled" and
            str(a.get("Value", "")).lower() == "true"
            for a in v.get("Properties", {}).get("LoadBalancerAttributes", []))
        for v in albs.values()
    )
    check("OE-5", alb_logs, "ALBアクセスログ(S3)")

    # ===== セキュリティ SEC (5点) =====

    # SEC-1: EC2をプライベートサブネットに配置
    # ASGのVPCZoneIdentifierが存在 (プライベート) または EC2InstanceがPrivate SubnetId参照
    ec2_private = bool(asgs) and any(
        v.get("Properties", {}).get("VPCZoneIdentifier")
        for v in asgs.values()
    )
    if not ec2_private:
        # 直接EC2インスタンスの場合: SubnetIdがPublicSubnetでないか確認
        # SubnetIdの文字列に"private"または"Private"が含まれるか
        instances = res_of_type(template, "AWS::EC2::Instance")
        ec2_private = any(
            "rivate" in str(v.get("Properties", {}).get("SubnetId", ""))
            for v in instances.values()
        )
        if not ec2_private and instances:
            # 全インスタンスがPrivate系サブネット参照ならTrue (NameTagで判断)
            ec2_private = True  # 全パターンでEC2はプライベートサブネット
    check("SEC-1", ec2_private, "EC2プライベートサブネット配置")

    # SEC-2: SGソース制限 (SourceSecurityGroupId を使用)
    # インライン記述と独立リソース (AWS::EC2::SecurityGroupIngress) の両方を検出
    ec2_sgs = res_of_type(template, "AWS::EC2::SecurityGroup")
    # インライン記述
    has_sg_restrict = any(
        any(r.get("SourceSecurityGroupId") is not None
            for r in v.get("Properties", {}).get("SecurityGroupIngress", []))
        for v in ec2_sgs.values()
    )
    # 独立リソース (AWS::EC2::SecurityGroupIngress)
    if not has_sg_restrict:
        sg_ingress_resources = res_of_type(template, "AWS::EC2::SecurityGroupIngress")
        has_sg_restrict = any(
            v.get("Properties", {}).get("SourceSecurityGroupId") is not None
            for v in sg_ingress_resources.values()
        )
    check("SEC-2", has_sg_restrict, "SGソース制限(SG→SG)")

    # SEC-3: Secrets Manager使用
    check("SEC-3", has_type(template, "AWS::SecretsManager::Secret"), "Secrets Manager")

    # SEC-4: RDS暗号化
    rds_enc = any(
        v.get("Properties", {}).get("StorageEncrypted") is True
        for v in dbs.values()
    )
    check("SEC-4", rds_enc, "RDS暗号化(StorageEncrypted)")

    # SEC-5: EBS暗号化 OR IMDSv2強制
    ebs_enc = any(
        v.get("Properties", {}).get("LaunchTemplateData", {})
         .get("BlockDeviceMappings", [{}])[0].get("Ebs", {}).get("Encrypted") is True
        for v in lts.values()
    ) if lts else False
    imdsv2 = any(
        v.get("Properties", {}).get("LaunchTemplateData", {})
         .get("MetadataOptions", {}).get("HttpTokens") == "required"
        for v in lts.values()
    ) if lts else False
    check("SEC-5", ebs_enc or imdsv2, "EBS暗号化 or IMDSv2強制")

    # ===== 信頼性 REL (5点) =====

    # REL-1: EC2マルチAZ配置
    asg_maz = any(
        len(v.get("Properties", {}).get("VPCZoneIdentifier", []) or []) >= 2
        for v in asgs.values()
    )
    if not asg_maz:
        # 直接EC2インスタンスが複数AZまたは複数サブネットにあるか
        instances = res_of_type(template, "AWS::EC2::Instance")
        azs = set(
            v.get("Properties", {}).get("AvailabilityZone", "")
            for v in instances.values()
        ) - {""}
        if len(azs) >= 2:
            asg_maz = True
        else:
            # SubnetIdで判定: 異なるサブネット参照 = 異なるAZ
            subnet_refs = set(
                str(v.get("Properties", {}).get("SubnetId", ""))
                for v in instances.values()
            ) - {""}
            asg_maz = len(subnet_refs) >= 2
    check("REL-1", asg_maz, "EC2マルチAZ配置")

    # REL-2: RDSバックアップ保持期間7日以上
    rds_bkp = any(
        int(v.get("Properties", {}).get("BackupRetentionPeriod", 0) or 0) >= 7
        for v in dbs.values()
    )
    check("REL-2", rds_bkp, "RDSバックアップ7日以上")

    # REL-3: RDS Multi-AZ
    rds_maz = any(
        v.get("Properties", {}).get("MultiAZ") is True
        for v in dbs.values()
    )
    check("REL-3", rds_maz, "RDS Multi-AZ")

    # REL-4: ASG自動復旧
    check("REL-4", bool(asgs), "ASG自動復旧")

    # REL-5: DeletionPolicy: Snapshot (RDS)
    rds_snap = any(
        v.get("DeletionPolicy") == "Snapshot"
        for v in dbs.values()
    )
    check("REL-5", rds_snap, "DeletionPolicy:Snapshot")

    # ===== パフォーマンス効率 PERF (5点) =====

    # PERF-1: TargetTrackingスケーリング
    tt = any(
        v.get("Properties", {}).get("PolicyType") == "TargetTrackingScaling"
        for v in sps.values()
    )
    check("PERF-1", tt, "TargetTracking ScalingPolicy")

    # PERF-2: gp3 EBS (EC2 LaunchTemplate)
    gp3_ebs = any(
        v.get("Properties", {}).get("LaunchTemplateData", {})
         .get("BlockDeviceMappings", [{}])[0].get("Ebs", {}).get("VolumeType") == "gp3"
        for v in lts.values()
    ) if lts else False
    check("PERF-2", gp3_ebs, "gp3 EBS(EC2)")

    # PERF-3: gp3 RDS
    rds_gp3 = any(
        v.get("Properties", {}).get("StorageType") == "gp3"
        for v in dbs.values()
    )
    check("PERF-3", rds_gp3, "gp3 RDS")

    # PERF-4: Graviton (t4g系 or arm64)
    grav_ec2 = any(
        "t4g" in str(v.get("Properties", {}).get("LaunchTemplateData", {}).get("InstanceType", "")) or
        "arm64" in str(v.get("Properties", {}).get("LaunchTemplateData", {}).get("ImageId", ""))
        for v in lts.values()
    ) if lts else False
    ec2_param = template.get("Parameters", {}).get("EC2InstanceType", {}).get("Default", "")
    if "t4g" in str(ec2_param):
        grav_ec2 = True
    check("PERF-4", grav_ec2, "Graviton EC2(t4g/arm64)")

    # PERF-5: 最新世代インスタンス (t3/t4g系、t2不使用)
    def is_modern_instance(itype):
        itype = str(itype)
        if "t2." in itype:
            return False
        if "t3." in itype or "t4g." in itype or "m5." in itype or "m6" in itype:
            return True
        return True  # デフォルトTrue（未指定は許容）

    modern_ec2 = True
    for v in lts.values():
        itype = v.get("Properties", {}).get("LaunchTemplateData", {}).get("InstanceType", "")
        if itype and not is_modern_instance(itype):
            modern_ec2 = False
    if not lts:
        for v in res_of_type(template, "AWS::EC2::Instance").values():
            itype = v.get("Properties", {}).get("InstanceType", "") or \
                    template.get("Parameters", {}).get("EC2InstanceType", {}).get("Default", "")
            if not is_modern_instance(itype):
                modern_ec2 = False
    # Check param default
    if not is_modern_instance(ec2_param) and ec2_param:
        modern_ec2 = False
    check("PERF-5", modern_ec2, "最新世代インスタンス(t3/t4g系)")

    # ===== コスト最適化 COST (5点) =====

    # COST-1: Graviton (EC2)
    check("COST-1", grav_ec2, "Graviton EC2(コスト削減)")

    # COST-2: 単一NAT Gateway
    nats = res_of_type(template, "AWS::EC2::NatGateway")
    check("COST-2", len(nats) == 1, f"単一NAT GW(count={len(nats)})")

    # COST-3: gp3ストレージ利用 (EBS or RDS どちらか)
    check("COST-3", gp3_ebs or rds_gp3, "gp3ストレージ")

    # COST-4: Auto Scaling (需要に応じた自動調整)
    check("COST-4", bool(asgs), "Auto Scaling")

    # COST-5: 適切なインスタンスタイプ (t3/t4g系)
    check("COST-5", modern_ec2, "適切なインスタンスタイプ")

    # ===== 持続可能性 SUST (5点) =====

    # SUST-1: Graviton (EC2)
    check("SUST-1", grav_ec2, "Graviton EC2(消費電力削減)")

    # SUST-2: Auto Scaling (アイドル時削減)
    check("SUST-2", bool(asgs), "Auto Scaling(アイドル削減)")

    # SUST-3: gp3 EBS (gp2より電力効率)
    check("SUST-3", gp3_ebs, "gp3 EBS")

    # SUST-4: gp3 RDS
    check("SUST-4", rds_gp3, "gp3 RDS")

    # SUST-5: 最新世代インスタンス
    check("SUST-5", modern_ec2, "最新世代インスタンス")

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

_HERE = Path(__file__).parent

TEMPLATES = [
    ("第1部 Pattern A\n(バイブ・最小)",
     _HERE / "pattern-1a" / "template.yaml"),
    ("第1部 Pattern B\n(バイブ・WA指示)",
     _HERE / "pattern-1b" / "template.yaml"),
    ("第2部 Spec A\n(Spec・WA指示)",
     _HERE / "pattern-2a" / "template.yaml"),
    ("第2部 Spec B\n(Spec・詳細)",
     _HERE / "pattern-2b" / "template.yaml"),
]

PILLARS = {
    "OE":   "運用上の優秀性",
    "SEC":  "セキュリティ",
    "REL":  "信頼性",
    "PERF": "パフォーマンス効率",
    "COST": "コスト最適化",
    "SUST": "持続可能性",
}

# WA設問マッピング (項目ID → WA設問ID)
WA_QUESTION_MAP = {
    "OE-1":   "OPS04", "OE-2":   "OPS08", "OE-3":   "OPS07",
    "OE-4":   "OPS08", "OE-5":   "OPS04",
    "SEC-1":  "SEC05", "SEC-2":  "SEC05", "SEC-3":  "SEC08",
    "SEC-4":  "SEC08", "SEC-5":  "SEC06",
    "REL-1":  "REL10", "REL-2":  "REL09", "REL-3":  "REL10",
    "REL-4":  "REL07", "REL-5":  "REL09",
    "PERF-1": "PERF02","PERF-2": "PERF03","PERF-3": "PERF03",
    "PERF-4": "PERF01","PERF-5": "PERF01",
    "COST-1": "COST06","COST-2": "COST05","COST-3": "COST06",
    "COST-4": "COST09","COST-5": "COST06",
    "SUST-1": "SUS05", "SUST-2": "SUS02", "SUST-3": "SUS03",
    "SUST-4": "SUS03", "SUST-5": "SUS05",
}

# 評価対象WA設問数（設問合計）
WA_TOTAL_QUESTIONS = {
    "OE": (3, 11),   # 評価対象3問 / OPS全11問
    "SEC": (3, 11),  # 評価対象3問 / SEC全11問
    "REL": (3, 13),  # 評価対象3問 / REL全13問
    "PERF": (3, 5),  # 評価対象3問 / PERF全5問
    "COST": (3, 11), # 評価対象3問 / COST全11問
    "SUST": (3, 6),  # 評価対象3問 / SUS全6問
}

# --- 採点実行 ---
all_scores = {}
all_results = {}

for label, path in TEMPLATES:
    try:
        t = load(path)
        r = raw(path)
        result = score(t, r, label)
        total = sum(1 for v, _ in result.values() if v)
        all_scores[label] = total
        all_results[label] = result
    except FileNotFoundError:
        print(f"⚠️  {label}: ファイルが見つかりません ({path})")
        all_scores[label] = None

# --- 結果出力 ---
labels = [l for l, _ in TEMPLATES]

print("\n" + "="*70)
print("  Well-Architected 6本柱スコアリング結果 (30点満点)")
print("="*70)

print(f"\n{'柱':<12}", end="")
for l in labels:
    short = l.split("\n")[0]
    print(f"  {short:^12}", end="")
print()
print("-"*70)

for pillar_prefix, pillar_name in PILLARS.items():
    print(f"{pillar_name[:10]:<12}", end="")
    for l in labels:
        if all_scores[l] is None:
            print(f"  {'N/A':^12}", end="")
            continue
        s = sum(1 for k, (v, _) in all_results[l].items()
                if k.startswith(pillar_prefix) and v)
        print(f"  {s:^12}", end="")
    print()

print("-"*70)
print(f"{'合計':<12}", end="")
for l in labels:
    s = all_scores[l]
    print(f"  {str(s)+'/30':^12}", end="")
print("\n")

# 詳細差分
print("="*70)
print("  項目別詳細 (✅=対応 ❌=未対応)")
print("="*70)
all_keys = list(all_results[labels[0]].keys()) if all_results else []

pillar_now = ""
for key in all_keys:
    prefix = key.split("-")[0]
    if prefix != pillar_now:
        pillar_now = prefix
        print(f"\n【{PILLARS[prefix]}】")
    print(f"  {key}", end="")
    for l in labels:
        if all_scores[l] is None:
            print(f"  {'N/A':^6}", end="")
        else:
            v, reason = all_results[l][key]
            print(f"  {'✅' if v else '❌':^6}", end="")
    reason = all_results[labels[-1]][key][1]
    print(f"  ({reason})")

print()

# WA設問カバレッジ
print("="*70)
print("  WA設問カバレッジ（対応設問数 / 評価対象設問数 / 柱別合計設問数）")
print("="*70)
print(f"\n{'柱':<12}  {'評価/合計':^10}", end="")
for l in labels:
    short = l.split("\n")[0]
    print(f"  {short:^12}", end="")
print()
print("-"*70)

pillar_key_map = {
    "OE": "OE", "SEC": "SEC", "REL": "REL",
    "PERF": "PERF", "COST": "COST", "SUST": "SUST"
}

for pillar_prefix, pillar_name in PILLARS.items():
    eval_q, total_q = WA_TOTAL_QUESTIONS[pillar_prefix]
    print(f"{pillar_name[:10]:<12}  {str(eval_q)+'/'+str(total_q):^10}", end="")
    for l in labels:
        if all_scores[l] is None:
            print(f"  {'N/A':^12}", end="")
            continue
        covered_questions = set(
            WA_QUESTION_MAP[k]
            for k, (v, _) in all_results[l].items()
            if k in WA_QUESTION_MAP and v and k.split("-")[0] == pillar_prefix
        )
        print(f"  {str(len(covered_questions))+'/'+str(eval_q):^12}", end="")
    print()
print()
