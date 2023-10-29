#### bin-utils
Collection of helpful scripts and apps

###### Setting up python3 and dependencies with VirtualEnv

```
 make setup
```

### Scripts

<!-- START makefile-doc -->
[_hn_links.py_](https://namuan.github.io/bin-utils/hn_links.html)
```
usage: hn_links.py [-h] -l HN_LINK -b BLOG_DIRECTORY [-v]

Grab links from HN Post and generate Markdown post with image thumbnails
It also creates a Hugo blog post from Markdown and images generated

SUPPORT: To regenerate thumbnail, just delete the image file under thumbnails folder inside the post directory.
SUPPORT: To remove any link from the blog post, delete the entry after the post is created **in the blog directory**
Note down all the links somewhere then run the following command from blog directory to delete them
E.g. Image links will be like

![](/images/2021/12/21/httpsunixstackexchangecoma88682.png)
![](/images/2021/12/21/httpscleaveapp.png)

$ pbpaste | awk -F\/ '{print $6}' | tr -d ')' | while read img; do find . -name $img -delete; done # noqa: W605

Usage:
$ python hn-links.py -l https://news.ycombinator.com/item?id=25381191 -b <blog_directory> --open-in-editor

options:
  -h, --help            show this help message and exit
  -l HN_LINK, --hn-link HN_LINK
                        Link to HN Post
  -b BLOG_DIRECTORY, --blog-directory BLOG_DIRECTORY
                        Full path to blog directory
  -v, --verbose         Display context variables at each step

```
[_template_py_scripts.py_](https://namuan.github.io/bin-utils/template_py_scripts.html)
```
usage: template_py_scripts.py [-h] [-v]

A simple script

Usage:
./template_py_scripts.py -h

./template_py_scripts.py -v # To log INFO messages
./template_py_scripts.py -vv # To log DEBUG messages

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity of logging output

```
[_fret-desktop-window.py_](https://namuan.github.io/bin-utils/fret-desktop-window.html)
```

```
[_txt_to_audio_polly.py_](https://namuan.github.io/bin-utils/txt_to_audio_polly.html)
```
usage: txt_to_audio_polly.py [-h] -i INPUT [-p PROFILE] [-v]

Convert text to audio using AWS Polly

Usage:
./txt_to_audio_polly.py -i input.txt

It is also possible to use the AWS_PROFILE environment variable to specify the AWS profile to use.
Otherwise you can use the -p/--profile option to specify the profile to use.
./txt_to_audio_polly.py -i input.txt -p my_profile

options:
  -h, --help            show this help message and exit
  -i INPUT, --input INPUT
                        Input file
  -p PROFILE, --profile PROFILE
                        AWS Profile to use. If not provided then it'll use the
                        AWS_PROFILE environment variable
  -v, --verbose         Increase verbosity of logging output

```
[_csv-markwhen.py_](https://namuan.github.io/bin-utils/csv-markwhen.html)
```
usage: csv-markwhen.py [-h] csv_file

Process a CSV file and generate formatted output for MarkWhen.

./csv-markwhen.py ~/Downloads/main.csv > ~/Downloads/main_timeline.mw
npx -i @markwhen/mw ~/Downloads/main_timeline.mw ~/Downloads/main_timeline.html
open ~/Downloads/main_timeline.html

positional arguments:
  csv_file    Path to the CSV file

options:
  -h, --help  show this help message and exit

```
[_twitter_login.py_](https://namuan.github.io/bin-utils/twitter_login.html)
```
usage: twitter_login.py [-h] [-v] [-i]

options:
  -h, --help       show this help message and exit
  -v, --verbose    Increase verbosity of logging output
  -i, --invisible  Run session in headless mode

```
[_media_manager.py_](https://namuan.github.io/bin-utils/media_manager.html)
```
usage: media_manager.py [-h] [-f SOURCE_FILE] [-s SOURCE_DIRECTORY] -t
                        TARGET_DIRECTORY [-r]

[] Organise photos and videos

TODO:
Handle ignored files

options:
  -h, --help            show this help message and exit
  -f SOURCE_FILE, --source-file SOURCE_FILE
                        Source file
  -s SOURCE_DIRECTORY, --source-directory SOURCE_DIRECTORY
                        Source directory
  -t TARGET_DIRECTORY, --target-directory TARGET_DIRECTORY
                        Target directory
  -r, --remove-source   Remove source file

```
[_thumbnail_generator.py_](https://namuan.github.io/bin-utils/thumbnail_generator.html)
```
usage: thumbnail_generator.py [-h] -i INPUT_URL -o OUTPUT_FILE_PATH
                              [-w WAIT_IN_SECS_BEFORE_CAPTURE] [-s]

options:
  -h, --help            show this help message and exit
  -i INPUT_URL, --input-url INPUT_URL
                        Web Url
  -o OUTPUT_FILE_PATH, --output-file-path OUTPUT_FILE_PATH
                        Output file path
  -w WAIT_IN_SECS_BEFORE_CAPTURE, --wait-in-secs-before-capture WAIT_IN_SECS_BEFORE_CAPTURE
                        Wait (in secs) before capturing screenshot
  -s, --headless        Run headless (no browser window)

```
[_links_to_hugo.py_](https://namuan.github.io/bin-utils/links_to_hugo.html)
```
usage: links_to_hugo.py [-h] -l LINKS_FILE -t POST_TITLE -b BLOG_DIRECTORY
                        [-e] [-v]

Read a list of links from a file (Each line should contain a single link to a webpage)
Check if the link is still valid
Grab title of the webpage
Grab screenshot/thumbnail of the webpage
Create a blog post with list of links along with the thumbnail

Usage:
$ python3 links_to_hugo.py -l links.txt -t "<blog title>" -b <blog_directory> --open-in-editor

Process:
1. Use curl to download the webpage
$ curl -s <page-url> > .temp/<filename>.html

2. Use pup to extract links and output to a file
$ cat <filename>.html | pup 'a attr{href}' >> links.txt

3. Run this script
$ EDITOR=/usr/local/bin/idea ./links_to_hugo.py --links-file .temp/links.txt --post-title "Post title"     --blog-directory "<full-path-to-blog-directory"  --open-in-editor

4. Review blog post in the editor and remove any links if necessary

5. Run this script to clean up any images that are left behind due to deleted links
$ ./unused_files.py -s <blog-root>/static/images -t <blog-root>/content -d

6. make deploy from blog directory
7. make commit-all from blog directory

options:
  -h, --help            show this help message and exit
  -l LINKS_FILE, --links-file LINKS_FILE
                        Path to links file
  -t POST_TITLE, --post-title POST_TITLE
                        Blog post title
  -b BLOG_DIRECTORY, --blog-directory BLOG_DIRECTORY
                        Full path to blog directory
  -e, --open-in-editor  Open blog site in editor
  -v, --verbose         Display context variables at each step

```
[_fret-animation.py_](https://namuan.github.io/bin-utils/fret-animation.html)
```

```
[_publish_vnote_to_hugo.py_](https://namuan.github.io/bin-utils/publish_vnote_to_hugo.html)
```
usage: publish_vnote_to_hugo.py [-h] [-b BLOG_DIRECTORY] -n VNOTE_FILE_PATH
                                [-e]

Publish vNote to Hugo blog post
$ python publish_vnote_to_hugo.py <<blog-root>> <<vnote-location>>

options:
  -h, --help            show this help message and exit
  -b BLOG_DIRECTORY, --blog-directory BLOG_DIRECTORY
                        Blog directory
  -n VNOTE_FILE_PATH, --vnote-file-path VNOTE_FILE_PATH
                        vNote file path
  -e, --open-in-editor  Open blog site in editor

```
[_readme_docs.py_](https://namuan.github.io/bin-utils/readme_docs.html)
```
usage: readme_docs.py [-h]

Generates documentation for the readme.md file

options:
  -h, --help  show this help message and exit

```
[_hn-vader-sentiment.py_](https://namuan.github.io/bin-utils/hn-vader-sentiment.html)
```
usage: hn-vader-sentiment.py [-h] -s STORY_ID [-v]

Analyse a HackerNews post by looking at the comments and calculating the sentiment

options:
  -h, --help            show this help message and exit
  -s STORY_ID, --story-id STORY_ID
                        Hacker News Story ID
  -v, --verbose         Display context variables at each step

```
[_twitter_thread.py_](https://namuan.github.io/bin-utils/twitter_thread.html)
```
usage: twitter_thread.py [-h] [-v] -u URL [-n TWEETS_TO_FETCH]

Collect tweets from a thread and save them to a file.

Usage:
./twitter_thread.py -h

./twitter_thread.py -v -u https://twitter.com/elonmusk/status/1320000000000000000 -o elonmusk.txt

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase verbosity of logging output
  -u URL, --url URL     URL of the thread to collect
  -n TWEETS_TO_FETCH, --tweets-to-fetch TWEETS_TO_FETCH
                        Number of tweets to fetch

```
[_template_executable_docs.py_](https://namuan.github.io/bin-utils/template_executable_docs.html)
```
usage: template_executable_docs.py [-h] -u USERNAME [-v]

Shows an example of executable documentation.

Usage:
./executable_docs.py -h

./executable_docs.py --username johndoe

options:
  -h, --help            show this help message and exit
  -u USERNAME, --username USERNAME
                        User name
  -v, --verbose         Display context variables at each step

```
[_py_carbon_clip.py_](https://namuan.github.io/bin-utils/py_carbon_clip.html)
```
usage: py_carbon_clip.py [-h]

Generate beautiful screenshots of code using carbon.now.sh and puts it on the clipboard.

options:
  -h, --help  show this help message and exit

```
[_playwright_browser.py_](https://namuan.github.io/bin-utils/playwright_browser.html)
```
usage: playwright_browser.py [-h] [-v] [-f INPUT_FILE] [-i INPUT_URL]
                             [-a AUTH_SESSION_FILE] [-p]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase verbosity of logging output
  -f INPUT_FILE, --input-file INPUT_FILE
                        Input file with URLs
  -i INPUT_URL, --input-url INPUT_URL
                        Web Url
  -a AUTH_SESSION_FILE, --auth-session-file AUTH_SESSION_FILE
                        Playwright authentication session
  -p, --convert-to-pdf  Convert to PDF

```
[_webpage_to_pdf.py_](https://namuan.github.io/bin-utils/webpage_to_pdf.html)
```
usage: webpage_to_pdf.py [-h] -i INPUT_URL [-o OUTPUT_FILE_PATH]
                         [-w WAIT_IN_SECS_BEFORE_CAPTURE] [-s]

Generate PDF from a webpage

options:
  -h, --help            show this help message and exit
  -i INPUT_URL, --input-url INPUT_URL
                        Web Url
  -o OUTPUT_FILE_PATH, --output-file-path OUTPUT_FILE_PATH
                        Full output file path for PDF
  -w WAIT_IN_SECS_BEFORE_CAPTURE, --wait-in-secs-before-capture WAIT_IN_SECS_BEFORE_CAPTURE
                        Wait (in secs) before capturing screenshot
  -s, --headless        Run headless (no browser window)

```
[_fret-play.py_](https://namuan.github.io/bin-utils/fret-play.html)
```

```
[_java_parser.py_](https://namuan.github.io/bin-utils/java_parser.html)
```
usage: java_parser.py [-h] -s SOURCE_DIRECTORY

Parses the java files and creates a list of all the classes and their methods.

options:
  -h, --help            show this help message and exit
  -s SOURCE_DIRECTORY, --source-directory SOURCE_DIRECTORY
                        Input source directory

```
[_jsondoc_parser.py_](https://namuan.github.io/bin-utils/jsondoc_parser.html)
```
usage: jsondoc_parser.py [-h] [-i INFILE] [-o OUTFILE]

Extract all paths from jsondoc file
Usage: $ curl -s -X GET http://some-url/restapidoc.json | python jsondoc_parser.py

options:
  -h, --help            show this help message and exit
  -i INFILE, --infile INFILE
  -o OUTFILE, --outfile OUTFILE

```
[_arch-animate.py_](https://namuan.github.io/bin-utils/arch-animate.html)
```
pygame 2.5.1 (SDL 2.28.2, Python 3.10.13)
Hello from the pygame community. https://www.pygame.org/contribute.html
usage: arch-animate.py [-h] [-c] [-v]

Simple script to demonstrate animating software architecture diagrams using PyGame

Requires
* brew install imagemagick

Usage:
./arch-animate.py -h

options:
  -h, --help            show this help message and exit
  -c, --convert-to-animation
                        Generate animated gif
  -v, --verbose         Increase verbosity of logging output

```
[_playwright_thumbnails.py_](https://namuan.github.io/bin-utils/playwright_thumbnails.html)
```
usage: playwright_thumbnails.py [-h] [-v] -i INPUT_URL -o OUTPUT_FILE_PATH
                                [-a AUTH_SESSION_FILE] [-s]
                                [-w WAIT_IN_SECS_BEFORE_CAPTURE]

options:
  -h, --help            show this help message and exit
  -v, --verbose         Increase verbosity of logging output
  -i INPUT_URL, --input-url INPUT_URL
                        Web Url
  -o OUTPUT_FILE_PATH, --output-file-path OUTPUT_FILE_PATH
                        Output file path
  -a AUTH_SESSION_FILE, --auth-session-file AUTH_SESSION_FILE
                        Playwright authentication session
  -s, --headless        Run in headless mode (no browser window)
  -w WAIT_IN_SECS_BEFORE_CAPTURE, --wait-in-secs-before-capture WAIT_IN_SECS_BEFORE_CAPTURE
                        Wait (in secs) before capturing screenshot

```
[_csv-checker.py_](https://namuan.github.io/bin-utils/csv-checker.html)
```
usage: csv-checker.py [-h] start_balance end_balance csv_path

Verify a csv file.

positional arguments:
  start_balance  The starting balance.
  end_balance    The ending balance.
  csv_path       The path to the CSV file.

options:
  -h, --help     show this help message and exit

```
[_unused_files.py_](https://namuan.github.io/bin-utils/unused_files.html)
```
usage: unused_files.py [-h] -s SOURCE -t TARGET [-d] [-v]

Find/Delete files from source directory that are not used in any file in the target directory.

options:
  -h, --help            show this help message and exit
  -s SOURCE, --source SOURCE
                        Source directory
  -t TARGET, --target TARGET
                        Target directory
  -d, --delete          Delete unused files
  -v, --verbose

```
[_textual-rich-play.py_](https://namuan.github.io/bin-utils/textual-rich-play.html)
```

```
[_auto-drive-chatgpt.py_](https://namuan.github.io/bin-utils/auto-drive-chatgpt.html)
```
usage: auto-drive-chatgpt.py [-h] [-v]

A simple script

Usage:
./template_py_scripts.py -h

./template_py_scripts.py -v # To log INFO messages
./template_py_scripts.py -vv # To log DEBUG messages

options:
  -h, --help     show this help message and exit
  -v, --verbose  Increase verbosity of logging output

```
[_helium_selenium_wrapper.py_](https://namuan.github.io/bin-utils/helium_selenium_wrapper.html)
```
usage: helium_selenium_wrapper.py [-h]

Demonstrates how to use helium to automate a web browser.

options:
  -h, --help  show this help message and exit

```
<!-- END makefile-doc -->

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
