from argparse import ArgumentParser
from pathlib import Path
import json
from bs4 import BeautifulSoup
import re

# Usage
# -i sample/tweet_sample.txt -o tweet_data.json

def parse_args():
	parser = ArgumentParser(
			description="A simple script to export from tweet html"
		)
	
	parser.add_argument('-i', '--input', type=str, help="Input tweet HTML")	
	parser.add_argument('-o', '--output', type=str, help='Output json file')
	return parser.parse_args()
	
def extract_tweet_id(soup):
	return soup.div['data-tweet-id']
	
def extract_date_time(soup):
	date_time = soup.select_one('.js-short-timestamp')['data-time']
	import time
	# convert date_time into time object
	return date_time
	
def extract_tweet_text(soup):
	tweet_text_html = soup.select_one('.tweet-text')
	return tweet_text_html.get_text()
	
def extract_links_in_tweet_text(soup):
	soup_tweet_text = soup.select_one('.tweet-text')
	links_in_tweets = []
	for a in soup_tweet_text.select('a'):
		links_in_tweets.append(a['data-expanded-url'])
		
	return links_in_tweets

def extract_from_action_text(action_text):
	action_text_regex = re.compile(r'(\d+).*')
	match = action_text_regex.search(action_text)
	return int(match.group(1))
		
def extract_stats(soup):
	replies = 0
	likes = 0
	retweets = 0
	
	for s in soup.select('span .ProfileTweet-actionCountForAria'):
		action_text = s.get_text()
		if action_text.find('replies') > 0:
			replies = extract_from_action_text(action_text)
		elif action_text.find('like') > 0:
			likes = extract_from_action_text(action_text)
		elif action_text.find('retweets') > 0:
			retweets = extract_from_action_text(action_text)

	return [replies, likes, retweets]
	
def extract_tweet_data(tweet_html):
	soup = BeautifulSoup(tweet_html, 'html.parser')
	tweet_id = extract_tweet_id(soup)
	date_time = extract_date_time(soup)
	tweet_text = extract_tweet_text(soup)
	links_in_tweet = extract_links_in_tweet_text(soup)
	[replies, likes, retweets] = extract_stats(soup)
	
	return {
		'tweet_id': tweet_id,
		'date_time': date_time,
		'tweet_text': tweet_text,
		'links_in_tweets': links_in_tweet,
		'replies': replies,
		'likes': likes,
		'retweets': retweets	
	}
	
def read_tweet(tweet_html_file):
	return Path(tweet_html_file).read_text(encoding='utf-8')
		
def main():
	args = parse_args()
	tweet_html_file = args.input
	json_output_file = Path(args.output)
		
	tweet_html = read_tweet(tweet_html_file)
	tweet_data = extract_tweet_data(tweet_html)
	
	tweet_data_json = json.dumps(tweet_data)
	json_output_file.write_text(tweet_data_json)


if __name__ == '__main__':
	main()
