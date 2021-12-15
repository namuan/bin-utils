#### bin-utils
Collection of helpful scripts and apps.

###### Setting up python3 with VirtualEnv

```
virtualenv -p python3 pyenv
```

For running python examples

```
pip install -r requirements.txt
```

_tweet_parser.py_

Converts a tweet in HTML to JSON.

_download_html_to_file.py_

Downloads Webpage from a URL to a file

_generate_paypal_errors.py_

Extract error codes from Paypal documentation webpage to JSON

_twitter_scrapy.py_

Scrapes tweets from twitter and writes out html as individual files to the output directory


### DEV: Setting up Pre-commit hooks

Add following dependencies in requirements/dev.txt
```
pre-commit
black
flake8
```

Run `make deps` to update dependencies

Create following files and add appropriate configurations
```
touch .flake8
touch .pre-commit-config.yaml
touch .pyproject.toml
```

Run `pre-commit install` to setup git hooks.

Commit and push all the changes
