// Function to get the page title and sanitize it for use as a filename
function getSanitizedPageTitle() {
    const title = document.title || 'Chat_Transcript';
    return title.replace(/[^a-z0-9]/gi, '_').toLowerCase();
}

// Select all chat-message elements
const chatMessages = document.querySelectorAll('chat-message');

// Function to extract content from user messages
function extractUserContent(message) {
    const contentDiv = message.querySelector('.from-user-container .message-text-content');
    return contentDiv ? contentDiv.textContent.trim() : '';
}

// Function to extract content from response messages
function extractResponseContent(message) {
    const contentDiv = message.querySelector('.to-user-container .message-text-content');
    return contentDiv ? contentDiv.textContent.trim() : '';
}

// Initialize variables
let userMessageCount = 0;
let responseMessageCount = 0;
let outputText = '';

// Iterate through each chat-message element
chatMessages.forEach((message) => {
    if (message.querySelector('.from-user-container')) {
        const messageContent = extractUserContent(message);

        if (messageContent) {
            userMessageCount++;
            outputText += `❓ ${messageContent}\n---\n`;
        }
    } else if (message.querySelector('.to-user-container')) {
        const messageContent = extractResponseContent(message);

        if (messageContent) {
            responseMessageCount++;
            outputText += `🤖 ${messageContent}\n---\n`;
        }
    }
});

// Function to download the text as a file
function downloadTextAsFile(text, filename) {
    const blob = new Blob([text], {type: 'text/plain'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
}

// Get the sanitized page title for the filename
const fileName = `${getSanitizedPageTitle()}_transcript.txt`;

// Download the file
downloadTextAsFile(outputText, fileName);

console.log("File download initiated.");
