// First open the thread as "Article" mode. Click on the 📖 icon
// Use json_to_markdown.py to convert the json file to markdown

let tweets = []; // Initialize an empty array to hold all tweet data

const scrollInterval = 2000;
const scrollStep = 500; // 500 pixels to scroll on each step

let previousTweetCount = 0;
let unchangedCount = 0;

// Function to scroll to the top of the page
function scrollToTop() {
    return new Promise((resolve) => {
        window.scrollTo(0, 0);
        setTimeout(resolve, 1000); // Wait for 1 second after scrolling to top
    });
}

// Main function to start the scraping process
async function startScraping() {
    console.log("Scrolling to the top of the page...");
    await scrollToTop();
    console.log("Starting tweet collection...");

    const scrollToEndIntervalID = setInterval(() => {
        window.scrollBy(0, scrollStep);
        const currentTweetCount = tweets.length;
        if (currentTweetCount === previousTweetCount) {
            unchangedCount++;
            if (unchangedCount >= 2) { // Stop if the count has not changed 2 times
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
}

function updateTweets() {
    const tweetArticles = document.querySelectorAll('article[data-testid="tweet"]');
    tweetArticles.forEach(article => {
        const tweetTextElement = article.querySelector('div[data-testid="tweetText"]');
        const imgElements = article.querySelectorAll('img');

        if (tweetTextElement || imgElements.length > 0) {
            const tweetText = tweetTextElement ? tweetTextElement.innerText : '';
            const imgSrcs = Array.from(imgElements).map(img => img.src);

            const tweetData = {
                text: tweetText,
                images: imgSrcs
            };

            if (!tweets.some(tweet =>
                tweet.text === tweetText &&
                JSON.stringify(tweet.images) === JSON.stringify(imgSrcs)
            )) {
                tweets.push(tweetData);
                console.log("New tweet captured:");
                console.log("Text:", tweetText);
                console.log("Image URLs:", imgSrcs);
                console.log("Total tweets captured: ", tweets.length);
                console.log("-------------------");
            }
        }
    });
}

function downloadTweetsAsJson(tweetsArray) {
    const jsonData = JSON.stringify(tweetsArray, null, 2); // Convert the array to JSON with pretty-printing
    const blob = new Blob([jsonData], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'tweets.json'; // Specify the file name
    document.body.appendChild(link); // Append the link to the document
    link.click(); // Programmatically click the link to trigger the download
    document.body.removeChild(link); // Clean up and remove the link
}

// Start the scraping process
startScraping();
