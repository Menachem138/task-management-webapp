import asyncio
import os
from telegram.ext import ExtBot
from telegram.error import TimedOut, RetryAfter, NetworkError

async def verify_bot_token(token: str) -> bool:
    """Simple verification of bot token."""
    try:
        bot = ExtBot(token)
        # Try to get bot info with retries
        max_retries = 3
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                me = await bot.get_me()
                print(f"Successfully verified bot: @{me.username}")
                return True
            except (TimedOut, RetryAfter, NetworkError) as e:
                retry_count += 1
                if retry_count >= max_retries:
                    raise
                wait_time = getattr(e, 'retry_after', 1)
                print(f"Rate limited, waiting {wait_time}s (attempt {retry_count}/{max_retries})")
                await asyncio.sleep(wait_time)
            except Exception as e:
                print(f"Error verifying token: {e}")
                return False
        return False
    except Exception as e:
        print(f"Token verification failed: {e}")
        return False

async def check_token():
    # Check current token
    token = os.environ.get("BOT_TOKEN", "")
    print("\nChecking current token...")
    result = await verify_bot_token(token)
    
    # Check environment variables
    env_token = os.environ.get("BOT_TOKEN")
    if env_token and env_token != token:
        print("\nChecking environment token...")
        env_result = await verify_bot_token(env_token)
    else:
        print("\nNo different BOT_TOKEN environment variable found")
    
    if not result and not (env_token and env_result):
        print("\nNo valid token found. A new token is needed.")

if __name__ == "__main__":
    asyncio.run(check_token())
