let tweets = new Map(); // Initialize a Map to hold all tweet elements, keyed by tweetId

const scrollInterval = 2000;
const scrollStep = 1000; // Pixels to scroll on each step

let previousTweetCount = 0;
let unchangedCount = 0;

// Function to scroll to the top of the page
function scrollToTop() {
    window.scrollTo(0, 0);
}

// Function to start the scraping process
function startScraping() {
    console.log("Starting the scraping process...");

    const scrollToEndIntervalID = setInterval(() => {
        window.scrollBy(0, scrollStep);
        const currentTweetCount = tweets.size;
        if (currentTweetCount === previousTweetCount) {
            unchangedCount++;
            if (unchangedCount >= 2) { // Stop if the count has not changed 5 times
                console.log('Scraping complete');
                console.log('Total tweets scraped: ', tweets.size);
                console.log('Downloading tweets as JSON...');
                clearInterval(scrollToEndIntervalID); // Stop scrolling
                observer.disconnect(); // Stop observing DOM changes
                downloadTweetsAsJson(tweets); // Download the tweets Map as a JSON file
            }
        } else {
            unchangedCount = 0; // Reset counter if new tweets were added
        }
        previousTweetCount = currentTweetCount; // Update previous count for the next check
    }, scrollInterval);

    // Initially populate the tweets Map
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
}

function updateTweets() {
    document.querySelectorAll('article[data-testid="tweet"]').forEach(tweetElement => {
        const authorName = tweetElement.querySelector('[data-testid="User-Name"]')?.innerText;
        const handle = tweetElement.querySelector('[role="link"]').href.split('/').pop();
        const tweetText = tweetElement.querySelector('[data-testid="tweetText"]')?.innerText;
        const time = tweetElement.querySelector('time').getAttribute('datetime');
        const postUrl = tweetElement.querySelector('.css-175oi2r.r-18u37iz.r-1q142lx a')?.href;

        // Extract tweet ID from the href attribute
        const tweetIdLink = tweetElement.querySelector('a[href*="/status/"]');
        const tweetId = tweetIdLink ? tweetIdLink.href.split('/').pop() : null;

        if (!tweetId) {
            console.log("Skipping tweet without ID");
            return;
        }

        console.log(`Author: ${authorName}, Handle: @${handle}, Tweet ID: ${tweetId}`);

        // Extract and separate profile image and tweet images
        const allImages = Array.from(tweetElement.querySelectorAll('img')).map(img => img.src);
        const profileImage = allImages.find(src => src.startsWith('https://pbs.twimg.com/profile_images')) || '';
        const tweetImages = allImages.find(src => src.startsWith('https://pbs.twimg.com/media')) || [];

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

        const tweetData = {
            authorName,
            handle,
            tweetText,
            time,
            postUrl,
            tweetId,
            profileImage,
            tweetImages,
            interaction: {replies, reposts, likes, bookmarks, views}
        };

        tweets.set(tweetId, tweetData);
        console.log("Tweets captured: ", tweets.size);
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

function downloadTweetsAsJson(tweetsMap) {
    const sortedTweets = Array.from(tweetsMap.values())
        .sort((a, b) => new Date(a.time) - new Date(b.time));

    const jsonData = JSON.stringify(sortedTweets, null, 2);
    const blob = new Blob([jsonData], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;

    // Create a formatted date-time string for the filename
    const now = new Date();
    const formattedDateTime = now.toISOString().replace(/[:.]/g, '-').slice(0, 19); // Format: YYYY-MM-DDTHH-mm-ss

    link.download = `tweets.json`; // Use the formatted date-time in the filename
    document.body.appendChild(link); // Append the link to the document
    link.click(); // Programmatically click the link to trigger the download
    document.body.removeChild(link); // Clean up and remove the link
}

// Main execution
scrollToTop(); // Scroll to the top of the page
console.log("Scrolled to the top of the page. Waiting for 1 second...");
setTimeout(startScraping, 1000); // Wait for 1 second before starting the scraping process
