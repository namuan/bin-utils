import logging
import os
import time

import tweepy
from dotenv import load_dotenv

load_dotenv()

# Twitter
TWITTER_CONSUMER_KEY = os.getenv("TWITTER_CONSUMER_KEY")
TWITTER_CONSUMER_SECRET = os.getenv("TWITTER_CONSUMER_SECRET")
TWITTER_ACCESS_TOKEN_KEY = os.getenv("TWITTER_ACCESS_TOKEN_KEY")
TWITTER_ACCESS_TOKEN_SECRET = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")

auth = tweepy.OAuthHandler(TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET)
auth.set_access_token(TWITTER_ACCESS_TOKEN_KEY, TWITTER_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)


def get_tweet(tweet_id):
    return with_limit_handled(lambda: api.get_status(id=tweet_id))


def get_twitter_home_timeline():
    return with_limit_handled(lambda: api.home_timeline(count=200, exclude_replies=True))


def with_limit_handled(func):
    try:
        return func()
    except tweepy.client.TooManyRequests:
        logging.warning("Hit Limit, waiting for 15 minutes")
        time.sleep(15 * 60)
        return func()


if __name__ == "__main__":
    print(get_twitter_home_timeline())
