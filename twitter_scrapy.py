import time
from argparse import ArgumentParser
from selenium import webdriver
from pathlib import Path


def since_query_param(since):
    return "since%3A{}".format(since)


def until_query_param(until):
    return "until%3A{}".format(until)


def from_account_query_param(from_account):
    return "from%3A{}".format(from_account)


def query_builder(from_account, since, until):
    s = since_query_param(since)
    u = until_query_param(until)
    f = from_account_query_param(from_account)
    return u'https://twitter.com/search?l=&q={0}%20{1}%20{2}&src=typd'.format(f, s, u)


def scroll_to_last_page(full_url):
    browser = webdriver.Chrome()
    browser.get(full_url)

    number_of_tweets = 0
    max_tweet_count = 60

    while number_of_tweets <= max_tweet_count:
        tweets_on_page = len(browser.find_elements_by_css_selector('div.original-tweet'))
        print("Total number of tweets on screen: {}".format(tweets_on_page))
        if number_of_tweets == tweets_on_page:
            print("No more tweets probably?")
            break

        number_of_tweets = tweets_on_page

        time.sleep(15)  # sleep for 20 seconds before scrolling
        browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)  # For the page to catch up before we count again
        print("Page should have scrolled")

    return browser.find_elements_by_css_selector('div.original-tweet')


def write_tweets(tweets, output_dir):
    for e in tweets:
        tweet_id = e.get_attribute('data-tweet-id')
        tweet_html = e.get_attribute('outerHTML')

        print("Writing tweet id: {0}".format(tweet_id))

        with open("{0}/{1}.txt".format(output_dir, tweet_id), 'w') as f:
            f.write(tweet_html)


def create_dir_if_needed(output_dir):
    if not output_dir.exists():
        output_dir.mkdir()


def parse_args():
    parser = ArgumentParser(
        description="A simple script to scrape tweets and export to output directory"
    )
    parser.add_argument('-o', '--output', type=str, help='Write tweets as individual files in this directory')
    parser.add_argument('-f', '--account', type=str, help='Scrape tweets for account')
    parser.add_argument('-s', '--since', type=str, help='Search from this date. Format YYYY-MM-DD')
    parser.add_argument('-u', '--until', type=str, help='Search to this data. Format YYYY-MM-DD')
    return parser.parse_args()


def main():
    args = parse_args()

    from_account = args.account
    since = args.since
    until = args.until
    output_dir = args.output

    create_dir_if_needed(Path(output_dir))
    full_url = query_builder(from_account, since, until)
    tweets_element = scroll_to_last_page(full_url)
    write_tweets(tweets_element, output_dir)


# Usage
# -o <output directory> -f twitter -s '2017-05-18' -u '2017-05-21'

if __name__ == '__main__':
    main()
