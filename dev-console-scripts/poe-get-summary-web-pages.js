// Select Poe in Browser with Gemini-1.5-Flash model
// Function to click the button with class containing "ChatMessageInputFooter_chatBreakButton"
function clickChatBreakButton() {
    const button = document.querySelector('button[class*="ChatMessageInputFooter_chatBreakButton"]');
    if (button) {
        button.click();
        console.log("Chat break button clicked");
    } else {
        console.log("Chat break button not found");
    }
}

// Function to enter text in the textarea with class containing "GrowingTextArea"
function enterText(text) {
    const textarea = document.querySelector('textarea[class*="GrowingTextArea"]');
    if (textarea) {
        textarea.value = text;
        textarea.dispatchEvent(new Event('input', {bubbles: true}));
        console.log(`Text "${text}" entered in textarea`);
    } else {
        console.log("Textarea not found");
    }
}

// Function to click the send button with class containing "ChatMessageSendButton"
function clickSendButton() {
    const sendButton = document.querySelector('button[class*="ChatMessageSendButton"]');
    if (sendButton) {
        sendButton.click();
        console.log("Send button clicked");
    } else {
        console.log("Send button not found");
    }
}

// Main function to perform all actions
function performActions() {
    clickChatBreakButton();
    setTimeout(() => {
        enterText("As instructed before, Summarise it using only bullet points in markdown syntax. No headings, just bullet points. I want it as raw markdown so that I can use it in README.md file. Make sure it is in raw markdown block to make it easy to copy. https://github.com/MightyMoud/sidekick");
        setTimeout(clickSendButton, 500);
    }, 500);
}

// Run the main function
performActions();
