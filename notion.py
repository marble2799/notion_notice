import os
import datetime
from datetime import timedelta
from dotenv import load_dotenv
from notion_client import Client
import requests
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from linebot.v3.messaging import Configuration, ApiClient, MessagingApi, PushMessageRequest, TextMessage
from linebot.v3.exceptions import InvalidSignatureError
import pytz

# 環境変数の読み込み
load_dotenv()

# タイムゾーンの設定
JST = pytz.timezone('Asia/Tokyo')

# Notion API設定
NOTION_TOKEN = os.getenv('NOTION_TOKEN')
NOTION_DATABASE_ID = os.getenv('NOTION_DATABASE_ID')

# LINE Messaging API設定
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')
LINE_USER_ID = os.getenv('LINE_USER_ID')

# Slack設定
SLACK_BOT_TOKEN = os.getenv('SLACK_BOT_TOKEN')
SLACK_CHANNEL_ID = os.getenv('SLACK_CHANNEL_ID')

# デフォルトの通知時間（分）
DEFAULT_NOTIFY_BEFORE = 30

# Notionクライアントの初期化
notion = Client(auth=NOTION_TOKEN)

def validate_line_user_id(user_id):
    """LINE User IDの形式を検証する"""
    if not user_id:
        return False
    # LINE User IDは'U'で始まり、その後に英数字が続く形式
    return user_id.startswith('U') and len(user_id) > 1

def send_line_notification(message):
    """LINEに通知を送信する"""
    if not LINE_CHANNEL_ACCESS_TOKEN:
        print("Warning: LINE_CHANNEL_ACCESS_TOKENが設定されていません")
        return False
    
    if not LINE_USER_ID:
        print("Warning: LINE_USER_IDが設定されていません")
        return False
    
    if not validate_line_user_id(LINE_USER_ID):
        print(f"Error: 無効なLINE User ID形式です: {LINE_USER_ID}")
        print("LINE User IDは'U'で始まる必要があります（例：U1234567890abcdef）")
        return False
    
    print("\n=== LINE通知の設定 ===")
    print(f"USER_ID: {LINE_USER_ID}")
    print(f"メッセージ: {message}")
    
    try:
        # LINE Messaging API v3の設定
        configuration = Configuration(access_token=LINE_CHANNEL_ACCESS_TOKEN)
        
        with ApiClient(configuration) as api_client:
            # MessagingApiのインスタンスを作成
            messaging_api = MessagingApi(api_client)
            
            # メッセージを作成
            text_message = TextMessage(type="text", text=message)
            
            # プッシュ通知リクエストを作成
            request = PushMessageRequest(
                to=LINE_USER_ID,
                messages=[text_message]
            )
            
            print("\n=== LINE通知リクエスト ===")
            print(f"リクエスト: {request}")
            
            # プッシュ通知を送信
            response = messaging_api.push_message(request)
            print(f"\n=== LINE通知レスポンス ===")
            print(f"レスポンス: {response}")
        return True
    except Exception as e:
        print(f"\nLINE通知エラー: {str(e)}")
        if hasattr(e, 'status'):
            print(f"ステータスコード: {e.status}")
        if hasattr(e, 'reason'):
            print(f"理由: {e.reason}")
        if hasattr(e, 'body'):
            print(f"レスポンスボディ: {e.body}")
        return False

def send_slack_notification(message):
    """Slackに通知を送信する"""
    if not (SLACK_BOT_TOKEN and SLACK_CHANNEL_ID):
        return False
    
    try:
        client = WebClient(token=SLACK_BOT_TOKEN)
        response = client.chat_postMessage(
            channel=SLACK_CHANNEL_ID,
            text=message
        )
        return True
    except SlackApiError as e:
        print(f"Slack通知エラー: {e}")
        return False

def send_notification(title, datetime_str, is_daily_summary=False):
    """通知を送信する（LINEまたはSlack）"""
    if is_daily_summary:
        message = f"予定: {title}\n日時: {datetime_str}"
    else:
        message = f"\n予定の通知\n予定名: {title}\n日時: {datetime_str}"
    
    # LINEとSlackの両方を試みる（設定されている方を使用）
    line_success = send_line_notification(message)
    if not line_success:
        slack_success = send_slack_notification(message)
        if not slack_success:
            print("通知の送信に失敗しました")
            return False
    return True

def update_notification_status(page_id):
    """通知済みステータスを更新する"""
    try:
        notion.pages.update(
            page_id=page_id,
            properties={
                "通知済み": {"checkbox": True}
            }
        )
        return True
    except Exception as e:
        print(f"ステータス更新エラー: {e}")
        return False

def send_daily_schedule():
    """1日の予定をまとめて通知する"""
    now = datetime.datetime.now(JST)
    tomorrow = now
    tomorrow_start = tomorrow.replace(hour=0, minute=0, second=0, microsecond=0)
    tomorrow_end = tomorrow.replace(hour=23, minute=59, second=59, microsecond=999999)

    try:
        print("\n=== 日次予定の取得 ===")
        print(f"取得期間: {tomorrow_start.strftime('%Y-%m-%d %H:%M:%S')} から {tomorrow_end.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # デバッグ用：データベースの全予定を取得
        debug_response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            sorts=[
                {
                    "property": "予定の日時",
                    "direction": "ascending"
                }
            ]
        )
        print(f"\nデータベース内の全予定数: {len(debug_response['results'])}件")
        
        # 明日の予定を取得（通知済みでない予定のみ）
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "予定の日時",
                        "date": {
                            "on_or_after": tomorrow_start.isoformat(),
                            "before": tomorrow_end.isoformat()
                        }
                    },
                    {
                        "property": "通知済み",
                        "checkbox": {
                            "equals": False
                        }
                    }
                ]
            },
            sorts=[
                {
                    "property": "予定の日時",
                    "direction": "ascending"
                }
            ]
        )

        if not response["results"]:
            print("予定が見つかりませんでした")
            # 予定がない場合もその旨を通知
            send_line_notification(f"{tomorrow.strftime('%Y年%m月%d日')}の予定はありません")
            return

        print(f"\n取得した予定: {len(response['results'])}件")
        
        # ヘッダーメッセージを送信
        send_line_notification(f"=== {tomorrow.strftime('%Y年%m月%d日')}の予定 ===")

        # 各予定を通知
        for page in response["results"]:
            properties = page["properties"]
            
            # デバッグ情報：ページの全プロパティを表示
            print("\n=== ページのプロパティ ===")
            for prop_name, prop_value in properties.items():
                print(f"{prop_name}: {prop_value}")
            
            # 予定名を取得（「名前」プロパティから）
            title_property = properties.get("名前")
            if not title_property or not isinstance(title_property, dict):
                print(f"Warning: 名前プロパティが無効です")
                continue  # 無効な予定はスキップ
            
            title_array = title_property.get("title", [])
            if not title_array:
                print(f"Warning: タイトルが空です")
                continue  # 空のタイトルはスキップ
            
            first_title = title_array[0]
            if not isinstance(first_title, dict):
                print(f"Warning: タイトル要素が無効です")
                continue  # 無効なタイトル要素はスキップ
            
            title = first_title.get("plain_text", "")
            if not title:  # 空文字列の場合はスキップ
                print(f"Warning: タイトルが空文字列です")
                continue
            
            # 予定の日時を取得
            schedule_date = properties.get("予定の日時", {}).get("date", {}).get("start")
            if not schedule_date:
                print(f"Warning: 予定の日時が設定されていません: {title}")
                continue
            
            try:
                # UTCの日時を取得し、JSTに変換
                schedule_datetime = datetime.datetime.fromisoformat(schedule_date.replace('Z', '+00:00'))
                schedule_datetime = schedule_datetime.astimezone(JST)
                print(f"予定: {title} - {schedule_datetime.strftime('%H:%M')}")
                send_notification(title, schedule_datetime.strftime("%H:%M"), True)
                # 通知済みフラグを更新
                # update_notification_status(page["id"])
            except Exception as e:
                print(f"Warning: 日時の変換エラー: {e}")
                continue

    except Exception as e:
        print(f"日次予定の取得エラー: {e}")
        import traceback
        print(traceback.format_exc())

def mark_past_events_as_notified():
    """過去の予定を通知済みにマークする"""
    now = datetime.datetime.now(JST)
    
    try:
        # 過去の未通知の予定を検索
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "通知済み",
                        "checkbox": {
                            "equals": False
                        }
                    },
                    {
                        "property": "予定の日時",
                        "date": {
                            "before": now.isoformat()
                        }
                    }
                ]
            }
        )
        
        past_events_count = len(response["results"])
        if past_events_count > 0:
            print(f"\n=== 過去の未通知予定の処理 ===")
            print(f"過去の未通知予定: {past_events_count}件")
            
            # 各予定を通知済みにマーク
            updated_count = 0
            for page in response["results"]:
                if update_notification_status(page["id"]):
                    updated_count += 1
            
            print(f"通知済みにマークした予定: {updated_count}件")
    
    except Exception as e:
        print(f"過去の予定の更新中にエラーが発生しました: {e}")

def format_datetime(dt_str, timezone=JST):
    """
    日時文字列をタイムゾーン付きのdatetimeオブジェクトに変換する
    
    Args:
        dt_str (str): ISO形式の日時文字列
        timezone (tzinfo): 変換先のタイムゾーン（デフォルト：JST）
    
    Returns:
        datetime: タイムゾーン付きのdatetimeオブジェクト
    """
    try:
        # 文字列がUTCタイムゾーン情報を含んでいない場合はUTCとして解釈
        if 'Z' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
        elif '+' in dt_str or '-' in dt_str:
            dt = datetime.datetime.fromisoformat(dt_str)
        else:
            dt = datetime.datetime.fromisoformat(dt_str + '+00:00')
        
        # UTCからJSTに変換
        return dt.astimezone(timezone)
    except Exception as e:
        print(f"日時の変換エラー: {e} (入力: {dt_str})")
        return None

def main():
    # 実行開始時刻を記録
    start_time = datetime.datetime.now(JST)
    print(f"\n=== 実行開始: {start_time.strftime('%Y-%m-%d %H:%M:%S')} ===")
    
    # 環境変数の確認
    if not NOTION_TOKEN:
        print("Error: NOTION_TOKEN が設定されていません")
        return
    if not NOTION_DATABASE_ID:
        print("Error: NOTION_DATABASE_ID が設定されていません")
        return
    
    # 現在時刻を取得（JSTで）
    now = datetime.datetime.now(JST)
    print(f"現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # 過去の予定を通知済みにマーク
    mark_past_events_as_notified()
    
    # 日付が変わった直後（00:00）かどうかをチェック
    if  now.hour == 0 and now.minute == 0:
        print("日次スケジュールの通知を実行します")
        send_daily_schedule()
    
    # デフォルト値使用のカウンター
    default_notify_count = 0
    # 通知送信カウンター
    notification_count = 0
    # 通知対象外の予定カウンター（デバッグ用）
    skipped_count = 0
    
    # Notionデータベースをクエリ
    try:
        print("\n=== データベースのクエリを実行 ===")
        print("クエリ条件:")
        print(f"- 現在時刻以降: {now.isoformat()}")
        print("- 通知済みでない予定")
        
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            filter={
                "and": [
                    {
                        "property": "通知済み",
                        "checkbox": {
                            "equals": False
                        }
                    },
                    {
                        "property": "予定の日時",
                        "date": {
                            "on_or_after": now.astimezone(datetime.timezone.utc).isoformat()
                        }
                    }
                ]
            },
            sorts=[
                {
                    "property": "予定の日時",
                    "direction": "ascending"
                }
            ]
        )
        
        if not response or "results" not in response:
            print("Warning: 有効な応答が得られませんでした")
            return
        
        total_events = len(response['results'])
        print(f"\n取得した予定: {total_events}件")
        
        if total_events == 0:
            print("\nデバッグ情報: データベース全体の未通知予定を確認")
            debug_response = notion.databases.query(
                database_id=NOTION_DATABASE_ID,
                filter={
                    "property": "通知済み",
                    "checkbox": {
                        "equals": False
                    }
                }
            )
            debug_total = len(debug_response['results'])
            print(f"未通知予定の総数: {debug_total}件")
            if debug_total > 0:
                print("\n最初の予定の生データ:")
                print(debug_response['results'][0])
        
        # 各予定をチェック
        for page in response["results"]:
            if not isinstance(page, dict):
                print(f"Warning: ページデータが辞書形式ではありません: {type(page)}")
                continue
                
            properties = page.get("properties")
            if not properties:
                print(f"Warning: プロパティが見つかりません")
                print("生データ:", page)
                continue
            
            # 予定の日時を取得
            date_property = properties.get("予定の日時")
            if not date_property or not isinstance(date_property, dict):
                print(f"Warning: 予定の日時プロパティが無効です")
                print("生データ:", date_property)
                continue
                
            date_value = date_property.get("date")
            if not date_value or not isinstance(date_value, dict):
                print(f"Warning: 日時の値が無効です")
                print("生データ:", date_property)
                continue
                
            schedule_date = date_value.get("start")
            if not schedule_date:
                print(f"Warning: 開始日時が設定されていません")
                print("生データ:", date_value)
                continue
            
            # 予定の日時をJSTに変換
            schedule_datetime = format_datetime(schedule_date)
            if not schedule_datetime:
                continue
            
            # 予定名を取得（"名前"プロパティを使用）
            title_property = properties.get("名前")
            if not title_property or not isinstance(title_property, dict):
                print(f"Warning: 名前プロパティが無効です")
                title = "無題"
            else:
                title_array = title_property.get("title", [])
                if not title_array:
                    print(f"Warning: タイトルが空です")
                    title = "無題"
                else:
                    first_title = title_array[0]
                    if not isinstance(first_title, dict):
                        print(f"Warning: タイトル要素が無効です")
                        title = "無題"
                    else:
                        title = first_title.get("plain_text", "無題")
            
            # 通知時間（分前）を取得
            notify_property = properties.get("通知時間")
            if not notify_property or not isinstance(notify_property, dict):
                default_notify_count += 1
                notify_before = DEFAULT_NOTIFY_BEFORE
            else:
                notify_before = notify_property.get("number")
                if notify_before is None:
                    default_notify_count += 1
                    notify_before = DEFAULT_NOTIFY_BEFORE
            
            # 通知すべき時刻を計算
            notify_datetime = schedule_datetime - timedelta(minutes=notify_before)
            
            # デバッグ情報を出力
            print(f"\n--- 予定の詳細 ---")
            print(f"タイトル: {title}")
            print(f"予定日時: {schedule_datetime.strftime('%Y-%m-%d %H:%M:%S')} ({schedule_datetime.tzname()})")
            print(f"元の日時: {schedule_date}")
            print(f"通知時刻: {notify_datetime.strftime('%Y-%m-%d %H:%M:%S')} ({notify_datetime.tzname()})")
            print(f"現在時刻: {now.strftime('%Y-%m-%d %H:%M:%S')} ({now.tzname()})")
            print(f"通知時間: {notify_before}分前")
            
            # 現在時刻が通知時刻を過ぎているかチェック
            if now >= notify_datetime and now < schedule_datetime:
                print("→ 通知条件を満たしています")
                print(f"通知を送信します: {title} - {schedule_datetime.strftime('%Y-%m-%d %H:%M')}")
                # 通知を送信
                if send_notification(title, schedule_datetime.strftime("%Y-%m-%d %H:%M")):
                    # 通知済みフラグを更新
                    if update_notification_status(page["id"]):
                        notification_count += 1
                        print("→ 通知の送信と更新に成功しました")
                    else:
                        print("→ 通知済みフラグの更新に失敗しました")
                else:
                    print("→ 通知の送信に失敗しました")
            else:
                skipped_count += 1
                if now < notify_datetime:
                    print("→ まだ通知時刻になっていません")
                else:
                    print("→ すでに予定時刻を過ぎています")
        
        # 処理結果のサマリーを表示
        print("\n=== 処理結果のサマリー ===")
        print(f"総予定数: {total_events}件")
        print(f"処理済み: {notification_count + skipped_count}件")
        print(f"- 通知送信: {notification_count}件")
        print(f"- 通知対象外: {skipped_count}件")
        if default_notify_count > 0:
            print(f"- デフォルト通知時間使用: {default_notify_count}件")
        
        # 通知の実行結果を表示
        if notification_count > 0:
            print(f"\nInfo: {notification_count}件の通知を送信しました")
        else:
            print("\nInfo: 通知対象の予定はありませんでした")
    
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        import traceback
        print(traceback.format_exc())
        return
    
    # 実行終了時刻を記録
    end_time = datetime.datetime.now(JST)
    execution_time = end_time - start_time
    print(f"\n=== 実行終了: {end_time.strftime('%Y-%m-%d %H:%M:%S')} (所要時間: {execution_time.total_seconds():.2f}秒) ===\n")

if __name__ == "__main__":
    main()
