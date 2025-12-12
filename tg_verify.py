import os
import json
import urllib.request
import urllib.error
import urllib.parse
import sys
from dotenv import load_dotenv

load_dotenv()


def make_request(url, method='GET', data=None, headers=None):
    if headers is None:
        headers = {}

    if data:
        data = json.dumps(data).encode('utf-8')
        headers['Content-Type'] = 'application/json'

    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode('utf-8'))
    except urllib.error.URLError as e:
        print(f"Network error: {e}")
        sys.exit(1)


def main():
    print("=== Telegram Auth Verification ===")

    # 1. Load Config
    token = os.getenv('TELEGRAM_BOT_TOKEN')

    if not token:
        print("Error: TELEGRAM_BOT_TOKEN not found in .env")
        sys.exit(1)

    # 2. Get Bot Info
    print("Checking Bot Status...")
    code, bot_info = make_request(f"https://api.telegram.org/bot{token}/getMe")

    if code != 200:
        print(f"Error: Invalid Bot Token. Telegram API returned {code}")
        print(bot_info)
        sys.exit(1)

    bot_username = bot_info['result']['username']
    bot_link = f"https://t.me/{bot_username}"

    print(f"\nSUCCESS: Bot is active (@{bot_username})")
    print(f"1. Open this link: {bot_link}")
    print("2. Click 'Start' and then 'Share Contact' button.")

    input("\nPress Enter after you have shared your contact with the bot...")

    # 3. Request Phone
    phone = input("\nEnter your phone number (format +380...): ").strip()

    # 4. Send OTP
    print(f"\nRequesting OTP for {phone} from http://127.0.0.1/auth/otp/send ...")
    code, res = make_request(
        "http://127.0.0.1/auth/otp/send",
        method='POST',
        data={"phone_number": phone}
    )

    if code != 200:
        print(f"FAILED to send OTP. Status: {code}")
        print("Response:", res)
        print("\nPossible causes:")
        print("- You didn't share contact with the bot.")
        print("- The phone number doesn't match the one used in Telegram.")
        print("- Services are not running (check docker logs).")
        sys.exit(1)

    print("SUCCESS: OTP sent.")

    # 5. Verify OTP
    otp_code = input("\nEnter the 6-digit OTP code received in Telegram: ").strip()

    print(f"\nVerifying OTP {otp_code}...")
    code, res = make_request(
        "http://127.0.0.1/auth/otp/verify",
        method='POST',
        data={"phone_number": phone, "code": otp_code}
    )

    if code != 200:
        print(f"FAILED to verify OTP. Status: {code}")
        print("Response:", res)
        sys.exit(1)

    print("\nSUCCESS: Authentication Complete!")
    print(f"Access Token: {res.get('access_token')}")
    print(f"Token Type: {res.get('token_type')}")


if __name__ == "__main__":
    main()
