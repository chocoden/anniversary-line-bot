import os
import datetime
from dotenv import load_dotenv

from dateutil.relativedelta import relativedelta
from fastapi import FastAPI, Request, HTTPException
from linebot.v3.webhook import WebhookHandler
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,  
    TextMessage
)
from apscheduler.schedulers.background import BackgroundScheduler
import pytz


# .envファイルから環境変数を読み込む
load_dotenv()
CHANNEL_ACCESS_TOKEN = os.getenv("LINE_CHANNEL_ACCESS_TOKEN")
CHANNEL_SECRET = os.getenv("LINE_CHANNEL_SECRET")
GROUP_ID = os.getenv("GROUP_ID")  # テスト用のユーザーID


# 送信先のID (テスト時は自分のユーザーID、本番はグループID) を設定
DESTINATION_ID = GROUP_ID 

# 記念日を設定
ANNIVERSARY_DATE = datetime.date(2022, 8, 24)

# 環境変数チェック
if not all([CHANNEL_ACCESS_TOKEN, CHANNEL_SECRET, DESTINATION_ID]):
    raise ValueError("環境変数と宛先IDを正しく設定してください")

# LINE Bot と FastAPI の初期設定 ---
configuration = Configuration(access_token=CHANNEL_ACCESS_TOKEN)
line_bot_api = MessagingApi(ApiClient(configuration))
handler = WebhookHandler(CHANNEL_SECRET)
app = FastAPI()

#  メイン機能（記念日メッセージを送信する関数） ---
def send_anniversary_message():
    try:
        today = datetime.date.today()

        # 今日の日付と記念日の日付を比較
        delta = relativedelta(today, ANNIVERSARY_DATE)
        years = delta.years
        months = delta.months

        # メッセージの内容を作成
        message_text = f"付き合ってから{years}年{months}ヶ月記念日です！おめでとう💖"

        # メッセージを送信
        line_bot_api.push_message(
            PushMessageRequest(
                to=DESTINATION_ID,
                messages=[TextMessage(text=message_text)]
            )
        )
        print(f"メッセージを送信しました: {message_text}")
    except Exception as e:
        print(f"メッセージ送信中にエラーが発生しました: {e}")

#  スケジューラーの設定 ---
scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Tokyo"))


 #本番用のスケジュール設定
scheduler.add_job(
     send_anniversary_message,
     'cron',
     day=24, # 毎月24日に実行
     hour=0, # 午前0時に実行
     minute=0, # 0分に実行
 )
print("スケジューラーが開始されました。毎月24日の00:00にメッセージを送信します!")

# スケジューラーを開始
scheduler.start()

# アプリ終了時にスケジューラーを停止
@app.on_event("shutdown")
def shutdown_event():
    scheduler.shutdown()
    print("スケジューラーが停止されました。")

# --- 5. Webhookエンドポイント ---
# LINEからの疎通確認のために、この部分は空のままで必要です
@app.post("/callback")
async def callback(request: Request):
    signature = request.headers.get("X-Line-Signature")
    if not signature:
        raise HTTPException(status_code=400, detail="X-Line-Signature header is missing")
    body = await request.body()
    try:
        handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=400, detail="Invalid signature")
    return 'OK'