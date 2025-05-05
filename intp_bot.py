import tweepy
import requests
import os
import logging
import schedule
import time
from datetime import datetime
import pytz
from dotenv import load_dotenv
from config import BANNED_WORDS

load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Twitter v2クライアント初期化
client = tweepy.Client(
    consumer_key=os.getenv('X_API_KEY'),
    consumer_secret=os.getenv('X_API_SECRET'),
    access_token=os.getenv('X_ACCESS_TOKEN'),
    access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET'),
    bearer_token=os.getenv('X_BEARER_TOKEN'),
    wait_on_rate_limit=True
)

# Claude API 呼び出し
def get_claude_response(prompt):
    import time

    max_retries = 3
    retry_delay = 3  # 秒
    headers = {
        'x-api-key': os.getenv("ANTHROPIC_API_KEY"),
        'Content-Type': 'application/json',
        'anthropic-version': '2023-06-01'
    }

    data = {
        "model": "claude-3-7-sonnet-20250219",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 160
    }

    logging.info("Claude API リクエスト送信内容:")
    logging.info(f"URL: https://api.anthropic.com/v1/messages")
    logging.info(f"Headers: {headers}")
    logging.info(f"Payload: {data}")

    for attempt in range(1, max_retries + 1):
        response = None
        try:
            response = requests.post(
                'https://api.anthropic.com/v1/messages',
                json=data,
                headers=headers,
                timeout=30
            )
            response.raise_for_status()
            content_blocks = response.json().get('content', [])
            if content_blocks and content_blocks[0].get('type') == 'text':
                return content_blocks[0].get('text')
        except requests.exceptions.RequestException as e:
            logging.error(f"[{attempt}/{max_retries}] Claude API Error: {str(e)}")
            if response is not None:
                try:
                    error_content = response.text
                    logging.error(f"API Response Content: {error_content}")
                    if "overloaded" in error_content.lower() and attempt < max_retries:
                        logging.info("Claude APIが過負荷状態のためリトライします...")
                        time.sleep(retry_delay)
                        continue
                except:
                    pass
            break  # 他のエラーならループ終了

    return None

# 禁止ワードチェック
def content_check(text):
    return any(word in text.lower() for word in BANNED_WORDS)

# 重複チェック
def is_duplicate(text):
    if not os.path.exists("tweet_log.txt"):
        return False
    with open("tweet_log.txt", "r", encoding="utf-8") as f:
        return text.strip() in f.read()

# 応答をログに保存
def log_response(text):
    with open("tweet_log.txt", "a", encoding="utf-8") as f:
        f.write(f"{datetime.now()} >>> {text}\n\n")

# ツイート処理
def post_tweet():
    tokyo_tz = pytz.timezone('Asia/Tokyo')
    now = datetime.now(tokyo_tz)
    hour = now.hour

    logging.info(f"現在の日本時間: {hour}時")

    if 6 <= hour <= 24:
        prompt = """以下の条件でX投稿を作成：

- 対象: INTP
- 内容: INTPの自己肯定感を上げる自己啓発
- 目的: バズる
- 文字数: 130〜140字
- 文体: 論理的、感情少なめ、お前
- 差別化: 過去と異なる内容（バリエーション）
- 構成: 1投稿＝1メッセージ
- 口調: 知的で下品
- キャラ: 倫理1%, 安全1%, コンプラ1%
- 必須: 「INTP」という語を含む"""

        response = get_claude_response(prompt)
        if response and not content_check(response):
            if is_duplicate(response):
                logging.warning("重複ツイートの可能性があるためスキップします")
                return
            log_response(response)
            try:
                client.create_tweet(text=response)
                logging.info("ツイートを投稿しました")
            except tweepy.TweepyException as e:
                logging.error(f"ツイート投稿失敗: {e}")
                if hasattr(e, 'response') and e.response is not None:
                    logging.error(f"詳細エラー: {e.response.text}")
        else:
            logging.error("適切な応答が得られませんでした")
    else:
        logging.info("現在の時間は投稿対象外です")

# スケジュール設定（3時間ごと）
schedule.every(3).hours.at(":00").do(post_tweet)

if __name__ == "__main__":
    logging.info("スケジューラー起動中...")
    while True:
        schedule.run_pending()
        time.sleep(30)
