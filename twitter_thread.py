#!/usr/bin/env python3
"""
Collect tweets from a thread and save them to a file.

Usage:
./twitter_thread.py -h

./twitter_thread.py -v -u https://twitter.com/elonmusk/status/1320000000000000000 -o elonmusk.txt
"""
import logging
from argparse import ArgumentParser, RawDescriptionHelpFormatter

import snscrape.modules.twitter as sntwitter


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[
            logging.StreamHandler(),
        ],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "-u",
        "--url",
        type=str,
        help="URL of the thread to collect",
        required=True,
    )
    parser.add_argument(
        "-n",
        "--tweets-to-fetch",
        type=int,
        help="Number of tweets to fetch",
        default=100,
        required=False,
    )
    return parser.parse_args()


def collect_recent_tweets(user_from_thread_url, tweets_to_fetch):
    collected_tweets = []
    for tweet in sntwitter.TwitterUserScraper(user_from_thread_url).get_items():
        if len(collected_tweets) == tweets_to_fetch:
            break
        else:
            collected_tweets.append(tweet)

    return collected_tweets


def collect_tweets_in_thread(recent_tweets, user_from_thread_url, tweet_id_from_thread_url):
    tweets_in_thread = {}

    for tweet in recent_tweets:
        if tweet.id == tweet_id_from_thread_url:
            tweets_in_thread[tweet.id] = tweet

        if tweet.conversationId == tweet_id_from_thread_url:
            tweet_is_a_reply_to_same_user = (
                tweet.inReplyToUser and tweet.inReplyToUser.username.lower() == user_from_thread_url
            )
            if tweet_is_a_reply_to_same_user:
                tweets_in_thread[tweet.id] = tweet

    return tweets_in_thread


def save_tweets_to_file(tweets_in_thread, output_file_path):
    with open(output_file_path, "w") as output_file:
        for tweet in sorted(tweets_in_thread.values(), key=lambda x: x.id):
            output_file.write("---\n")
            output_file.write(
                f"#### [{tweet.date.strftime('%Y-%m-%d %H:%M:%S')} -> {tweet.user.username} 🗒️]({tweet.url})\n\n"
            )
            output_file.write(f"{tweet.rawContent}\n\n")


def main(args):
    thread_url = args.url
    user_from_thread_url = thread_url.split("/")[3]
    tweet_id_from_thread_url = int(thread_url.split("/")[5])
    recent_tweets = collect_recent_tweets(user_from_thread_url, args.tweets_to_fetch)
    logging.info(f"Total tweets collected: {len(recent_tweets)}")
    tweets_in_thread = collect_tweets_in_thread(recent_tweets, user_from_thread_url, tweet_id_from_thread_url)
    logging.info(f"Total tweets in thread: {len(tweets_in_thread)}")
    output_file = f"target/{tweet_id_from_thread_url}.md"
    save_tweets_to_file(tweets_in_thread, output_file)


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    main(args)
