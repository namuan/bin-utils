import os

import praw
from dotenv import load_dotenv

load_dotenv()

# Twitter
REDDIT_CLIENT_ID = os.getenv("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.getenv("REDDIT_CLIENT_SECRET")
REDDIT_USER = os.getenv("REDDIT_USER")
REDDIT_PASSWORD = os.getenv("REDDIT_PASSWORD")
REDDIT_USERAGENT = os.getenv("REDDIT_USERAGENT")

reddit = praw.Reddit(
    client_id=REDDIT_CLIENT_ID,
    client_secret=REDDIT_CLIENT_SECRET,
    username=REDDIT_USER,
    password=REDDIT_PASSWORD,
    user_agent=REDDIT_USERAGENT,
)

if __name__ == "__main__":
    # Reddit apps - https://www.reddit.com/prefs/apps/
    print(reddit.user.me())
