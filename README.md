# Notion予定通知システム

Notionのデータベースから予定を取得し、指定のタイミングでLINEまたはSlackに通知を送信するシステムです。

## セットアップ手順

1. 必要なパッケージのインストール:
```bash
pip install -r requirements.txt
```

2. 環境変数の設定:
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

3. Notionの設定:
- Notionインテグレーションを作成し、トークンを取得
- データベースにインテグレーションを追加
- データベースIDを取得

4. LINE Messaging APIの設定:
- [LINE Developers Console](https://developers.line.biz/console/)にアクセス
- 新規プロバイダーを作成（または既存のものを選択）
- 新規チャネルを作成（Messaging API）
- チャネルアクセストークンを発行（長期のものを選択）
- LINE Official Accountマネージャーで以下の設定を行う：
  - 応答設定を「応答メッセージ」を「オフ」に
  - 応答設定の「webhookの利用」を「オン」に
- ボットと友だちになり、あなたのユーザーIDを取得
  - 開発者のユーザーIDは[LINE Developersコンソール](https://developers.line.biz/console/)のチャネル基本設定から確認可能

5. Slack設定（Slackを使用する場合）:
- Slackアプリを作成し、ボットトークンとチャンネルIDを取得

## Notionデータベースの設定

以下のプロパティを持つデータベースを作成してください：
- 予定名 (タイトル)
- 予定の日時 (日付)
- 通知時間 (数値) - 予定の何分前に通知するか
- 通知済み (チェックボックス)

## cronの設定

以下のコマンドでcrontabを編集:
```bash
crontab -e
```

以下の行を追加して毎分実行:
```
* * * * * cd /path/to/project && python notion.py
```

## 動作の仕組み

1. 毎分、スクリプトが実行されます
2. 未通知の予定のうち、現在時刻が通知時間と一致するものを検索
3. 該当する予定があれば、LINEまたはSlackに通知を送信
4. 通知が成功したら、その予定の通知済みフラグをONに更新