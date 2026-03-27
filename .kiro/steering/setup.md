# プロジェクトセットアップ

## cfn-lint

cfn-lint はプロジェクトルートの `.venv` 内にインストールされています。

実行コマンド：
- Windows: `.venv/Scripts/cfn-lint`
- Mac/Linux: `.venv/bin/cfn-lint`

グローバルに `cfn-lint` コマンドが使えない場合は上記のパスを使用してください。

## セットアップ手順（初回のみ）

**Windows:**
```powershell
python -m venv .venv
.venv\Scripts\pip install cfn-lint
```

**Mac/Linux:**
```bash
python3 -m venv .venv
.venv/bin/pip install cfn-lint
```

## 検証対象

- `pattern-3/template.yaml` : CloudFormation テンプレート（本リポジトリのメインテンプレート）
