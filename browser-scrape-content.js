// Run this in browser console.
// Adjust according to the website content (Line 70 to 80)
function slowScrollToBottom() {
    return new Promise((resolve) => {
        let lastHeight = document.body.scrollHeight;
        let noChangeCount = 0;
        const maxNoChangeCount = 10; // Number of attempts before concluding no more content

        function scroll() {
            window.scrollTo(0, document.body.scrollHeight);
            setTimeout(() => {
                const newHeight = document.body.scrollHeight;
                if (newHeight > lastHeight) {
                    // New content loaded, reset counter
                    lastHeight = newHeight;
                    noChangeCount = 0;
                } else {
                    // No new content, increment counter
                    noChangeCount++;
                }

                if (noChangeCount < maxNoChangeCount) {
                    // Keep scrolling
                    scroll();
                } else {
                    // No new content after several attempts, assume we're at the bottom
                    console.log("Reached the bottom of the page");
                    resolve();
                }
            }, 2000); // Wait 2 seconds between scrolls
        }

        scroll();
    });
}

function getUniqueFileName() {
    const pageTitle = document.title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
    const date = new Date().toISOString().replace(/[:.]/g, '-');
    return `${pageTitle}_${date}.txt`;
}

function saveAsTextFile(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], {type: 'text/plain'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

function scrollToTop() {
    return new Promise((resolve) => {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
        // Wait for the scroll to complete
        setTimeout(resolve, 1000);
    });
}

slowScrollToBottom()
    .then(() => {
        console.log("Scrolling finished, now extracting data...");

        const postItems = document.querySelectorAll('div[data-test^="post-item"]');
        const extractedData = Array.from(postItems).map(div => {
            const anchor = div.querySelector('a');
            const voteButton = div.querySelector('button[data-test="vote-button"]');
            const voteCountDiv = voteButton ? voteButton.querySelector('div.text-12.font-semibold.text-light-gray') : null;
            return {
                href: anchor ? anchor.getAttribute('href') : null,
                ariaLabel: anchor ? anchor.getAttribute('aria-label') : null,
                voteCount: voteCountDiv ? parseInt(voteCountDiv.textContent.replace(/,/g, ''), 10) : null
            };
        });

        console.log("Data extracted, preparing download...");
        const fileName = getUniqueFileName();
        saveAsTextFile(extractedData, fileName);
        console.log(`File saved as: ${fileName}`);

        return scrollToTop();
    })
    .then(() => {
        console.log("Scrolled back to the top of the page");
        console.log("Script execution completed");
    })
    .catch(error => {
        console.error("An error occurred:", error);
    });
