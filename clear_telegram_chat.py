import requests, os
from dotenv import load_dotenv

load_dotenv()
token = os.getenv('TELEGRAM_BOT_TOKEN')
chat_id = os.getenv('TELEGRAM_CHAT_ID')

if not token or not chat_id:
    print("Telegram credentials missing in .env")
    exit(1)

# Send dummy message to find latest message_id
url = f'https://api.telegram.org/bot{token}/sendMessage'
res = requests.post(url, json={'chat_id': chat_id, 'text': '🧹 Clearing bot history...'}).json()
latest_id = res.get('result', {}).get('message_id', 0)

print(f"Latest Telegram Message ID: {latest_id}")
print("Deleting recent messages...")

deleted = 0
for msg_id in range(latest_id, max(1, latest_id - 500), -1):
    del_url = f'https://api.telegram.org/bot{token}/deleteMessage'
    r = requests.post(del_url, json={'chat_id': chat_id, 'message_id': msg_id}).json()
    if r.get('ok'):
        deleted += 1

print(f"🎉 Deleted {deleted} messages from Telegram chat!")
