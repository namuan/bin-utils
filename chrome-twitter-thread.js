/* Enhancements to the Twitter Scraping Script:

This update to the script introduces a more robust mechanism for extracting detailed interaction data from tweets as they are scraped from Twitter. Previously, the script focused on collecting basic content such as the tweet's text. Now, it has been augmented to include a comprehensive extraction of interaction metrics, including replies, reposts, likes, bookmarks, and views, for each tweet.

Key Changes:

1. Improved Data Extraction:
   - The script now searches through all elements within a tweet that have an `aria-label` attribute, filtering for labels that contain key interaction terms (replies, reposts, likes, bookmarks, views). This ensures that only relevant `aria-labels` are considered for data extraction.

2. Flexible Interaction Data Parsing:
   - A new function, `extractInteractionDataFromString`, has been added. It uses regular expressions to parse the consolidated interaction data string found in the `aria-label`. This approach allows for a more accurate extraction of numeric values corresponding to each type of interaction, regardless of slight variations in the `aria-label` text format.

3. Auxiliary Function for Numeric Extraction:
   - An auxiliary function, `extractNumberForKeyword`, has been introduced to extract numbers based on specific keywords within the interaction data string. This function enhances the script's ability to accurately parse and convert interaction metrics from textual descriptions to numeric values.

4. MutationObserver Integration:
   - The use of `MutationObserver` remains to monitor DOM changes dynamically, ensuring that the script continues to capture tweets as the user scrolls through Twitter. The observer triggers the `updateTweets` function to process newly loaded tweets.

5. Efficient Tweet Uniqueness Check:
   - The logic for determining whether a tweet is new (and thus should be added to the collection) has been refined. This check now ensures that duplicates are effectively filtered out, maintaining the integrity of the scraped data set.

6. JSON Download Functionality:
   - The final step of the script, which involves compiling the scraped tweets into a JSON file and downloading it, has been preserved. This feature provides users with a convenient way to export the collected data for further analysis or archiving.

By implementing these enhancements, the script now offers a comprehensive solution for scraping detailed interaction data from X, making it a valuable tool for social media analysis, research, and data collection projects.

*/

let tweets = []; // Initialize an empty array to hold all tweet elements

const scrollInterval = 2000;
const scrollStep = 5000; // Pixels to scroll on each step

let previousTweetCount = 0;
let unchangedCount = 0;

const scrollToEndIntervalID = setInterval(() => {
    window.scrollBy(0, scrollStep);
    const currentTweetCount = tweets.length;
    if (currentTweetCount === previousTweetCount) {
        unchangedCount++;
        if (unchangedCount >= 2) { // Stop if the count has not changed 5 times
            console.log('Scraping complete');
            console.log('Total tweets scraped: ', tweets.length);
            console.log('Downloading tweets as JSON...');
            clearInterval(scrollToEndIntervalID); // Stop scrolling
            observer.disconnect(); // Stop observing DOM changes
            downloadTweetsAsJson(tweets); // Download the tweets list as a JSON file
        }
    } else {
        unchangedCount = 0; // Reset counter if new tweets were added
    }
    previousTweetCount = currentTweetCount; // Update previous count for the next check
}, scrollInterval);

function updateTweets() {
    document.querySelectorAll('article[data-testid="tweet"]').forEach(tweetElement => {
        const authorName = tweetElement.querySelector('[data-testid="User-Name"]')?.innerText;
        const handle = tweetElement.querySelector('[role="link"]').href.split('/').pop();
        const tweetText = tweetElement.querySelector('[data-testid="tweetText"]')?.innerText;
        const time = tweetElement.querySelector('time').getAttribute('datetime');
        const postUrl = tweetElement.querySelector('.css-175oi2r.r-18u37iz.r-1q142lx a')?.href;

        // Filter and extract interaction data in an enhanced way
        const interactionInfo = [...tweetElement.querySelectorAll('[aria-label]')]
            .map(element => element.getAttribute('aria-label'))
            .find(label => label && /replies|reposts|likes|bookmarks|views/.test(label));

        const {
            replies,
            reposts,
            likes,
            bookmarks,
            views
        } = interactionInfo ? extractInteractionDataFromString(interactionInfo) : {
            replies: 0,
            reposts: 0,
            likes: 0,
            bookmarks: 0,
            views: 0
        };

        const isTweetNew = !tweets.some(tweet => tweet.postUrl === postUrl);
        if (isTweetNew) {
            tweets.push({
                authorName,
                handle,
                tweetText,
                time,
                postUrl,
                interaction: {replies, reposts, likes, bookmarks, views}
            });
            console.log("Tweets capturados: ", tweets.length);
        }
    });
}

function extractInteractionDataFromString(infoString) {
    let replies = 0, reposts = 0, likes = 0, bookmarks = 0, views = 0;

    // Helper function to extract numbers based on a keyword
    function extractNumberForKeyword(text, keyword) {
        const regex = new RegExp(`(\\d+)\\s${keyword}`, "i");
        const match = text.match(regex);
        return match ? parseInt(match[1], 10) : 0;
    }

    if (infoString) {
        // Individually extract each interaction type using the helper function
        replies = extractNumberForKeyword(infoString, "replies");
        reposts = extractNumberForKeyword(infoString, "reposts");
        likes = extractNumberForKeyword(infoString, "likes");
        bookmarks = extractNumberForKeyword(infoString, "bookmarks");
        views = extractNumberForKeyword(infoString, "views");
    }

    return {replies, reposts, likes, bookmarks, views};
}


// Initially populate the tweets array
updateTweets();

// Create a MutationObserver to observe changes in the DOM
const observer = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        if (mutation.addedNodes.length) {
            updateTweets(); // Call updateTweets whenever new nodes are added to the DOM
        }
    });
});

// Start observing the document body for child list changes
observer.observe(document.body, {childList: true, subtree: true});

function downloadTweetsAsJson(tweetsArray) {
    const jsonData = JSON.stringify(tweetsArray); // Convert the array to JSON
    const blob = new Blob([jsonData], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'tweets.json'; // Specify the file name
    document.body.appendChild(link); // Append the link to the document
    link.click(); // Programmatically click the link to trigger the download
    document.body.removeChild(link); // Clean up and remove the link
}
