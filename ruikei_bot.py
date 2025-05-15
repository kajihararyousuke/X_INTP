import tweepy
import openai
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

# OpenAI API キー設定
openai.api_key = os.getenv("OPENAI_API_KEY")

# Twitter v2クライアント初期化
client = tweepy.Client(
    consumer_key=os.getenv('X_API_KEY'),
    consumer_secret=os.getenv('X_API_SECRET'),
    access_token=os.getenv('X_ACCESS_TOKEN'),
    access_token_secret=os.getenv('X_ACCESS_TOKEN_SECRET'),
    bearer_token=os.getenv('X_BEARER_TOKEN'),
    wait_on_rate_limit=True
)

# OpenAI API 呼び出し
def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # または "gpt-3.5-turbo"
            messages=[
                {"role": "user", "content": prompt}
            ],
            max_tokens=160,
            temperature=0.8
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        logging.error(f"OpenAI API 呼び出しエラー: {str(e)}")
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
        prompt = """「X投稿作成」
目的：性格違いで盛り上がる
ターゲット：性格悪い若い女性
文頭：「類型別に聞きたい！」＋改行
文体：具体的
内容：ユニークな質問
文字数：130字以内
過去と異なる内容で
"""

        response = get_openai_response(prompt)
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

# スケジュール設定（12時と18時に1日2回投稿）
schedule.every().day.at("12:00").do(post_tweet)
schedule.every().day.at("18:00").do(post_tweet)

if __name__ == "__main__":
    logging.info("スケジューラー起動中...")
    while True:
        schedule.run_pending()
        time.sleep(30)
