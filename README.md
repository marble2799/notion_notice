# Notion予定通知システム

Notionのデータベースから予定を取得し、指定のタイミングでLINEまたはSlackに通知を送信するシステムです。

## 機能
- 指定した時間に予定を通知
- 日付が変わった時点（00:00）で翌日の予定一覧を通知
- LINE Messaging APIまたはSlackを使用した通知
- Notionデータベースとの連携

## 前提条件
- Python 3.8以上
- Debian/Ubuntu系のLinux環境（他の環境の場合はコマンドを適宜読み替えてください）

## セットアップ手順

### 1. 必要なパッケージのインストール
```bash
# Python仮想環境作成に必要なパッケージをインストール
sudo apt update
sudo apt install python3-venv
```

### 2. リポジトリのクローンとディレクトリ移動
```bash
git clone [リポジトリURL]
cd notion_notice
```

### 3. Python仮想環境のセットアップ
```bash
# 仮想環境の作成
python3 -m venv venv

# 仮想環境の有効化
source venv/bin/activate

# 必要なパッケージのインストール
pip install -r requirements.txt
```

注意: 仮想環境を有効化すると、プロンプトの先頭に`(venv)`が表示されます。
これ以降のPythonコマンドは、必ず仮想環境が有効化された状態で実行してください。

### 4. 環境変数の設定
以下の内容で`.env`ファイルを作成してください：
```
# Notion API設定
NOTION_TOKEN=your_notion_integration_token
NOTION_DATABASE_ID=your_database_id

# LINE Messaging API設定
LINE_CHANNEL_ACCESS_TOKEN=your_channel_access_token
LINE_USER_ID=your_user_id

# Slack設定
SLACK_BOT_TOKEN=your_slack_bot_token
SLACK_CHANNEL_ID=your_slack_channel_id
```

### 5. Notionの設定
1. Notionインテグレーションを作成し、トークンを取得
   - [My integrations](https://www.notion.so/my-integrations)にアクセス
   - 「+ New integration」をクリック
   - 必要な情報を入力して作成
   - 表示される「Internal Integration Token」を保存

2. データベースにインテグレーションを追加
   - データベースページを開く
   - 右上の「...」をクリック
   - 「Connections」から作成したインテグレーションを追加

3. データベースIDの取得
   - データベースのURLから取得
   - 例: `https://www.notion.so/workspace-name/[database-id]?v=[version]`
   - `[database-id]`部分が必要なID

### 6. LINE Messaging APIの設定
1. [LINE Developers Console](https://developers.line.biz/console/)にアクセス
2. 新規プロバイダーを作成（または既存のものを選択）
3. 新規チャネルを作成（Messaging API）
4. チャネルアクセストークンを発行（長期のものを選択）
5. LINE Official Accountマネージャーで以下の設定を行う：
   - 応答設定を「応答メッセージ」を「オフ」に
   - 応答設定の「webhookの利用」を「オン」に
6. ボットと友だちになり、あなたのユーザーIDを取得
   - 開発者のユーザーIDは[LINE Developersコンソール](https://developers.line.biz/console/)のチャネル基本設定から確認可能

### 7. cronの設定
```bash
# crontabを編集
crontab -e

# 以下の行を追加（パスは実際の環境に合わせて変更してください）
* * * * * cd /path/to/notion_notice && /path/to/notion_notice/venv/bin/python /path/to/notion_notice/notion.py >> /path/to/notion_notice/cron.log 2>&1
```

注意点：
- パスは必ず絶対パスで指定してください
- `/path/to/notion_notice`は実際のプロジェクトディレクトリのパスに置き換えてください
- ログファイル（cron.log）は自動的に作成されます
- cronの書式は「分 時 日 月 曜日」の順です（* * * * *は毎分実行を意味します）

## Notionデータベースの設定

以下のプロパティを持つデータベースを作成してください：
- 予定名 (タイトル)
- 予定の日時 (日付)
- 通知時間 (数値) - 予定の何分前に通知するか
- 通知済み (チェックボックス)

## 動作の仕組み

1. 毎分、スクリプトが実行されます
2. 00:00の場合、翌日の予定一覧を通知します
3. それ以外の時間は、以下の処理を行います：
   - 未通知の予定のうち、現在時刻が通知時間と一致するものを検索
   - 該当する予定があれば、LINEまたはSlackに通知を送信
   - 通知が成功したら、その予定の通知済みフラグをONに更新

## トラブルシューティング

### 仮想環境関連
- 仮想環境の再有効化: `source venv/bin/activate`
- 仮想環境の終了: `deactivate`
- パッケージの再インストール: `pip install -r requirements.txt`

### 通知関連
- LINE通知が届かない場合:
  - ボットが友だち追加されているか確認
  - トークンとユーザーIDが正しいか確認
- Slack通知が届かない場合:
  - ボットがチャンネルに招待されているか確認
  - トークンとチャンネルIDが正しいか確認

## セキュリティ注意事項
- `.env`ファイルは決してGitにコミットしないでください
- 各種トークンは厳重に管理し、他人と共有しないでください
- トークンが漏洩した場合は、直ちに再発行してください