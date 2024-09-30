// List of URLs to process
const urls = [
    'https://deskriders.dev/',
];

// Function to click the button with class containing "ChatMessageInputFooter_chatBreakButton"
function clickChatBreakButton() {
    return new Promise((resolve) => {
        const button = document.querySelector('button[class*="ChatMessageInputFooter_chatBreakButton"]');
        if (button) {
            button.click();
            console.log("Chat break button clicked");
        } else {
            console.log("Chat break button not found");
        }
        setTimeout(resolve, 1000);
    });
}

// Function to enter text in the textarea with class containing "GrowingTextArea"
function enterText(text) {
    return new Promise((resolve) => {
        const textarea = document.querySelector('textarea[class*="GrowingTextArea"]');
        if (textarea) {
            textarea.value = text;
            textarea.dispatchEvent(new Event('input', { bubbles: true }));
            console.log(`Text entered in textarea`);
        } else {
            console.log("Textarea not found");
        }
        setTimeout(resolve, 1000);
    });
}

// Function to click the send button with class containing "ChatMessageSendButton"
function clickSendButton() {
    return new Promise((resolve) => {
        const sendButton = document.querySelector('button[class*="ChatMessageSendButton"]');
        if (sendButton) {
            sendButton.click();
            console.log("Send button clicked");
        } else {
            console.log("Send button not found");
        }
        setTimeout(resolve, 1000);
    });
}

// Main function to perform all actions for a single URL
async function performActions(url) {
    await clickChatBreakButton();
    await enterText(`As instructed before, Summarise it using only bullet points in markdown syntax. No headings, just bullet points. I want it as raw markdown so that I can use it in README.md file. Make sure it is in raw markdown block to make it easy to copy. ${url}`);
    await clickSendButton();
}

// Function to process all URLs
async function processAllUrls() {
    for (const url of urls) {
        console.log(`Processing URL: ${url}`);
        await performActions(url);
        // Wait for 5 seconds before processing the next URL
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
    console.log("All URLs processed");
}

// Run the main function to process all URLs
processAllUrls();