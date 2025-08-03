// Leo Chat Bot - Main Application Script
// ===================================

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const sendButton = document.getElementById('sendButton');
const typingIndicator = document.getElementById('typingIndicator');
const sidebar = document.getElementById('sidebar');
const toggleSidebar = document.getElementById('toggleSidebar');
const sidebarToggleMain = document.getElementById('sidebarToggleMain');
const newChatButton = document.getElementById('newChatButton');
const sessionsList = document.getElementById('sessionsList');
const showMeButton = document.getElementById('showMeButton');
const dropdownContent = document.getElementById('dropdownContent');
const themeToggle = document.getElementById('themeToggle');
const themeIcon = document.getElementById('themeIcon');
const themeText = document.getElementById('themeText');
const soundToggle = document.getElementById('soundToggle');
const soundIcon = document.getElementById('soundIcon');
const soundText = document.getElementById('soundText');
const searchInput = document.getElementById('searchInput');
const searchClear = document.getElementById('searchClear');
const searchResults = document.getElementById('searchResults');

// Global Variables
let audioContext = null;
let userSoundPreference = localStorage.getItem('soundNotifications') !== 'disabled';
let currentTheme = localStorage.getItem('theme') || 'light';
let searchTimeout = null;
let allMessages = []; // Cache for all messages across sessions
let currentSessionId = null;
let sessions = [];
let commandHistory = [];
let historyIndex = -1;
let currentInput = '';

// Audio Notification System
// ========================

function initAudioContext() {
    if (!audioContext) {
        try {
            audioContext = new (window.AudioContext || window.webkitAudioContext)();
        } catch (e) {
            console.warn('Web Audio API not supported:', e.message || e);
        }
    }
}

function playNotificationSound() {
    if (!userSoundPreference) return;
    
    initAudioContext();
    if (!audioContext) return;

    // Resume audio context if suspended (required by modern browsers)
    if (audioContext.state === 'suspended') {
        audioContext.resume().then(() => {
            playSound();
        }).catch(err => {
            console.error('Failed to resume audio context:', err);
        });
    } else {
        playSound();
    }

    function playSound() {
        try {
            // Create a pleasant notification tone (major chord)
            const oscillator1 = audioContext.createOscillator();
            const oscillator2 = audioContext.createOscillator();
            const oscillator3 = audioContext.createOscillator();
            const gainNode = audioContext.createGain();

            // Connect oscillators to gain node
            oscillator1.connect(gainNode);
            oscillator2.connect(gainNode);
            oscillator3.connect(gainNode);
            gainNode.connect(audioContext.destination);

            // Set frequencies for a pleasant C major chord
            oscillator1.frequency.setValueAtTime(523.25, audioContext.currentTime); // C5
            oscillator2.frequency.setValueAtTime(659.25, audioContext.currentTime); // E5
            oscillator3.frequency.setValueAtTime(783.99, audioContext.currentTime); // G5

            // Set wave type for a softer sound
            oscillator1.type = 'sine';
            oscillator2.type = 'sine';
            oscillator3.type = 'sine';

            // Configure volume envelope (increased volume)
            gainNode.gain.setValueAtTime(0, audioContext.currentTime);
            gainNode.gain.linearRampToValueAtTime(0.3, audioContext.currentTime + 0.05);
            gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.6);

            // Start and stop the oscillators
            const startTime = audioContext.currentTime;
            const endTime = startTime + 0.6;

            oscillator1.start(startTime);
            oscillator2.start(startTime);
            oscillator3.start(startTime);

            oscillator1.stop(endTime);
            oscillator2.stop(endTime);
            oscillator3.stop(endTime);

        } catch (error) {
            console.error('Failed to play notification sound:', error);
        }
    }
}

function toggleSoundNotifications() {
    userSoundPreference = !userSoundPreference;
    localStorage.setItem('soundNotifications', userSoundPreference ? 'enabled' : 'disabled');
    updateSoundButton();
    return userSoundPreference;
}

// Theme Management
// ===============

function updateThemeButton() {
    if (currentTheme === 'dark') {
        themeIcon.textContent = '☀️';
        themeText.textContent = 'Light';
    } else {
        themeIcon.textContent = '🌙';
        themeText.textContent = 'Dark';
    }
}

function updateSoundButton() {
    if (userSoundPreference) {
        soundIcon.textContent = '🔊';
        soundText.textContent = 'Sound';
        soundToggle.classList.remove('muted');
    } else {
        soundIcon.textContent = '🔇';
        soundText.textContent = 'Muted';
        soundToggle.classList.add('muted');
    }
}

// Search Functionality
// ===================

async function performSearch(query) {
    const searchScope = document.querySelector('input[name="searchScope"]:checked').value;
    
    try {
        let results = [];
        
        if (searchScope === 'current' && currentSessionId) {
            results = await searchCurrentSession(query);
        } else {
            results = await searchAllSessions(query);
        }
        
        displaySearchResults(results, query);
    } catch (error) {
        console.error('Search error:', error);
        showSearchError();
    }
}

async function searchCurrentSession(query) {
    if (!currentSessionId) return [];
    
    try {
        const response = await fetch(`/sessions/${currentSessionId}`);
        if (!response.ok) return [];
        
        const sessionData = await response.json();
        const results = [];
        
        sessionData.messages.forEach((message, index) => {
            if (message.content.toLowerCase().includes(query.toLowerCase())) {
                results.push({
                    sessionId: currentSessionId,
                    messageIndex: index,
                    content: message.content,
                    role: message.role,
                    timestamp: message.timestamp,
                    sessionPreview: 'Current chat'
                });
            }
        });
        
        return results;
    } catch (error) {
        console.error('Error searching current session:', error);
        return [];
    }
}

async function searchAllSessions(query) {
    try {
        const sessionsResponse = await fetch('/sessions');
        if (!sessionsResponse.ok) return [];
        
        const allSessions = await sessionsResponse.json();
        const results = [];
        
        for (const session of allSessions) {
            try {
                const sessionResponse = await fetch(`/sessions/${session.id}`);
                if (sessionResponse.ok) {
                    const sessionData = await sessionResponse.json();
                    
                    sessionData.messages.forEach((message, index) => {
                        if (message.content.toLowerCase().includes(query.toLowerCase())) {
                            results.push({
                                sessionId: session.id,
                                messageIndex: index,
                                content: message.content,
                                role: message.role,
                                timestamp: message.timestamp,
                                sessionPreview: session.first_message
                            });
                        }
                    });
                }
            } catch (error) {
                console.error(`Error searching session ${session.id}:`, error);
            }
        }
        
        results.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
        return results;
    } catch (error) {
        console.error('Error searching all sessions:', error);
        return [];
    }
}

function displaySearchResults(results, query) {
    searchResults.innerHTML = '';
    
    if (results.length === 0) {
        searchResults.innerHTML = '<div class="search-no-results">No messages found</div>';
        searchResults.style.display = 'block';
        return;
    }
    
    results.forEach(result => {
        const resultDiv = document.createElement('div');
        resultDiv.className = 'search-result-item';
        
        const highlightedContent = highlightSearchTerm(result.content, query);
        const timeAgo = getTimeAgo(result.timestamp);
        
        resultDiv.innerHTML = `
            <div class="search-result-preview">${highlightedContent}</div>
            <div class="search-result-meta">
                <span>${result.role === 'user' ? '👤 You' : '🦁 Leo'}</span>
                <span>${timeAgo}</span>
            </div>
        `;
        
        resultDiv.addEventListener('click', () => {
            loadSessionAndScrollToMessage(result.sessionId, result.messageIndex);
            hideSearchResults();
            searchInput.value = '';
            searchClear.style.display = 'none';
        });
        
        searchResults.appendChild(resultDiv);
    });
    
    searchResults.style.display = 'block';
}

function highlightSearchTerm(text, query) {
    if (!query) return text;
    
    const escapedQuery = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(${escapedQuery})`, 'gi');
    
    return text.replace(regex, '<span class="search-highlight">$1</span>');
}

function hideSearchResults() {
    searchResults.style.display = 'none';
    searchResults.innerHTML = '';
}

function showSearchError() {
    searchResults.innerHTML = '<div class="search-no-results">Search error occurred</div>';
    searchResults.style.display = 'block';
}

async function loadSessionAndScrollToMessage(sessionId, messageIndex) {
    try {
        if (sessionId !== currentSessionId) {
            await loadSession(sessionId);
        }
        
        setTimeout(() => {
            const messages = chatMessages.querySelectorAll('.message');
            if (messages[messageIndex]) {
                messages[messageIndex].scrollIntoView({ 
                    behavior: 'smooth', 
                    block: 'center' 
                });
                
                messages[messageIndex].style.backgroundColor = 'var(--bg-session-active)';
                setTimeout(() => {
                    messages[messageIndex].style.backgroundColor = '';
                }, 2000);
            }
        }, 100);
    } catch (error) {
        console.error('Error loading session and scrolling to message:', error);
    }
}

// Session Management
// =================

async function loadSessions() {
    try {
        const response = await fetch('/sessions');
        if (response.ok) {
            sessions = await response.json();
            renderSessions();
        } else {
            console.warn('Failed to load sessions');
        }
    } catch (error) {
        console.error('Error loading sessions:', error);
    }
}

function renderSessions() {
    sessionsList.innerHTML = '';
    
    sessions.forEach(session => {
        const sessionDiv = document.createElement('div');
        sessionDiv.className = 'session-item';
        if (session.id === currentSessionId) {
            sessionDiv.classList.add('active');
        }
        
        const preview = session.first_message.length > 50 
            ? session.first_message.substring(0, 50) + '...' 
            : session.first_message;
        
        const timeAgo = getTimeAgo(session.last_activity);
        
        sessionDiv.innerHTML = `
            <div class="session-preview">${preview}</div>
            <div class="session-time">${timeAgo}</div>
        `;
        
        sessionDiv.addEventListener('click', () => loadSession(session.id));
        sessionsList.appendChild(sessionDiv);
    });
}

function getTimeAgo(timestamp) {
    const now = new Date();
    const time = new Date(timestamp);
    const diffMs = now - time;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);
    
    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return time.toLocaleDateString();
}

async function loadSession(sessionId) {
    try {
        const response = await fetch(`/sessions/${sessionId}`);
        if (response.ok) {
            const sessionData = await response.json();
            currentSessionId = sessionId;
            
            chatMessages.innerHTML = '';
            
            sessionData.messages.forEach(msg => {
                addMessage(msg.content, msg.role === 'user' ? 'user' : 'bot');
            });
            
            renderSessions();
            console.log('Loaded session:', sessionId);
        } else {
            console.error('Failed to load session');
        }
    } catch (error) {
        console.error('Error loading session:', error);
    }
}

function startNewChat() {
    currentSessionId = null;
    chatMessages.innerHTML = `
        <div class="message bot">
            <div class="message-content">
                Hello! I'm Leo, your AI assistant. How can I help you today?
            </div>
        </div>
    `;
    renderSessions();
    console.log('Started new chat');
}

// Command History
// ==============

function navigateHistory(direction) {
    if (commandHistory.length === 0) return;

    if (direction === 'up') {
        if (historyIndex === -1) {
            currentInput = chatInput.value;
            historyIndex = commandHistory.length - 1;
        } else if (historyIndex > 0) {
            historyIndex--;
        }
        chatInput.value = commandHistory[historyIndex];
    } else if (direction === 'down') {
        if (historyIndex === -1) return;
        
        if (historyIndex < commandHistory.length - 1) {
            historyIndex++;
            chatInput.value = commandHistory[historyIndex];
        } else {
            historyIndex = -1;
            chatInput.value = currentInput;
        }
    }
    
    chatInput.setSelectionRange(chatInput.value.length, chatInput.value.length);
}

function addToHistory(command) {
    if (!command.trim() || (commandHistory.length > 0 && commandHistory[commandHistory.length - 1] === command)) {
        return;
    }
    
    commandHistory.push(command);
    
    if (commandHistory.length > 50) {
        commandHistory.shift();
    }
    
    historyIndex = -1;
    currentInput = '';
}

// Message Handling
// ===============

async function sendMessage() {
    const message = chatInput.value.trim();
    if (!message) return;

    addToHistory(message);

    const lowerMessage = message.toLowerCase();
    
    if (lowerMessage.startsWith('show me ')) {
        const item = lowerMessage.substring(8).trim();
        handleShowMeCommand(item, message);
        return;
    }

    processNormalMessage(message);
}

async function processNormalMessage(message) {
    chatInput.disabled = true;
    sendButton.disabled = true;
    chatInput.value = '';

    addMessage(message, 'user');
    showTypingIndicator();

    try {
        const requestBody = { message: message };
        if (currentSessionId) {
            requestBody.session_id = currentSessionId;
        }

        const response = await fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        
        if (!currentSessionId) {
            currentSessionId = data.session_id;
            console.log('Session ID:', currentSessionId);
            await loadSessions();
        }
        
        hideTypingIndicator();
        addMessage(data.response, 'bot');
        playNotificationSound();

    } catch (error) {
        console.error('Error:', error);
        hideTypingIndicator();
        addErrorMessage('Sorry, there was an error processing your request. Please try again.');
    } finally {
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }
}

function addMessage(text, sender) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${sender}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    if (sender === 'bot') {
        contentDiv.innerHTML = formatBotMessage(text);
    } else {
        contentDiv.textContent = text;
    }
    
    messageDiv.appendChild(contentDiv);
    chatMessages.appendChild(messageDiv);
    
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatBotMessage(text) {
    text = formatCodeBlocks(text);
    
    let formatted = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/(?<!<code[^>]*>)`([^`]+)`(?![^<]*<\/code>)/g, '<code>$1</code>')
        .replace(/^\*\s+(.*)$/gm, '<li>$1</li>')
        .replace(/(\d+)\.\s\*\*(.*?)\*\*:\s(.*?)(?=\n\d+\.|\n\n|$)/gms, '<li><strong>$2:</strong> $3</li>')
        .replace(/(\d+)\.\s(.*?)(?=\n\d+\.|\n\n|$)/gms, '<li>$2</li>')
        .replace(/^([A-Za-z][^\n]*?)\s*\n\s*:\s*(.*?)$/gm, '$1: $2')
        .replace(/(<li>.*?<\/li>)(\s*<li>.*?<\/li>)*/gs, function(match) {
            if (match.includes('<strong>') || /\d+\./.test(text)) {
                return '<ol>' + match + '</ol>';
            } else {
                return '<ul>' + match + '</ul>';
            }
        })
        .replace(/\n\n/g, '<br><br>')
        .replace(/\n/g, '<br>')
        .replace(/<\/li><br>/g, '</li>')
        .replace(/<\/(ol|ul)><br><br>/g, '</$1><br>')
        .replace(/(<strong>.*?<\/strong>:?)<br><br>/g, '$1<br>')
        .replace(/<br><br><br>/g, '<br><br>');

    return formatted;
}

function formatCodeBlocks(text) {
    const codeBlockRegex = /```(\w+)?\n?([\s\S]*?)```/g;
    
    return text.replace(codeBlockRegex, (match, language, code) => {
        const lang = language || 'text';
        const trimmedCode = code.trim();
        const blockId = 'code-' + Date.now() + '-' + Math.random().toString(36).substring(2, 9);
        
        return `
            <div class="code-block-container" data-language="${lang}">
                <div class="code-block-header">
                    <span class="code-block-language">${lang}</span>
                    <div class="code-block-actions">
                        <button class="code-action-btn" onclick="copyCodeToClipboard('${blockId}')">
                            📋 Copy
                        </button>
                    </div>
                </div>
                <div class="code-block-content">
                    <pre class="code-block" id="${blockId}">${escapeHtml(trimmedCode)}</pre>
                </div>
            </div>
        `;
    });
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Make functions available globally for onclick handlers
window.copyCodeToClipboard = async function(blockId) {
    try {
        const codeElement = document.getElementById(blockId);
        const code = codeElement.textContent;
        await navigator.clipboard.writeText(code);
        
        // Find the button that was clicked by looking for the one in the same container
        const container = codeElement.closest('.code-block-container');
        const button = container.querySelector('.code-action-btn');
        const originalText = button.innerHTML;
        button.innerHTML = '✅ Copied!';
        button.classList.add('success');
        
        setTimeout(() => {
            button.innerHTML = originalText;
            button.classList.remove('success');
        }, 2000);
        
    } catch (error) {
        console.error('Failed to copy code:', error);
        const codeElement = document.getElementById(blockId);
        const range = document.createRange();
        range.selectNode(codeElement);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        
        try {
            await navigator.clipboard.writeText(codeElement.textContent);
            const container = codeElement.closest('.code-block-container');
            const button = container.querySelector('.code-action-btn');
            button.innerHTML = '✅ Copied!';
            button.classList.add('success');
            setTimeout(() => {
                button.innerHTML = '📋 Copy';
                button.classList.remove('success');
            }, 2000);
        } catch (fallbackError) {
            console.error('Fallback copy failed:', fallbackError);
        }
    }
};

async function copyCodeToClipboard(blockId) {
    return window.copyCodeToClipboard(blockId);
}

async function executeCode(blockId, language) {
    const codeElement = document.getElementById(blockId);
    const code = codeElement.textContent;
    const container = codeElement.closest('.code-block-container');
    
    const existingOutput = container.querySelector('.code-output');
    if (existingOutput) {
        existingOutput.remove();
    }
    
    // Find the button in the container
    const button = container.querySelector('.code-action-btn');
    const originalText = button.innerHTML;
    button.innerHTML = '⏳ Running...';
    button.disabled = true;
    
    try {
        let output = '';
        let success = true;
        
        if (language === 'javascript') {
            try {
                const originalConsoleLog = console.log;
                const logs = [];
                
                console.log = (...args) => {
                    logs.push(args.map(arg => 
                        typeof arg === 'object' ? JSON.stringify(arg, null, 2) : String(arg)
                    ).join(' '));
                };
                
                const result = eval(code);
                console.log = originalConsoleLog;
                
                if (logs.length > 0) {
                    output = logs.join('\n');
                }
                
                if (result !== undefined && logs.length === 0) {
                    output = String(result);
                }
                
                if (!output) {
                    output = 'Code executed successfully (no output)';
                }
                
            } catch (jsError) {
                output = `Error: ${jsError.message}`;
                success = false;
            }
            
        } else if (language === 'python') {
            output = await executePythonCode(code);
            success = !output.startsWith('Error:');
        }
        
        const outputElement = document.createElement('pre');
        outputElement.className = `code-output ${success ? 'success' : 'error'}`;
        outputElement.textContent = output;
        container.querySelector('.code-block-content').appendChild(outputElement);
        
    } catch (error) {
        const outputElement = document.createElement('pre');
        outputElement.className = 'code-output error';
        outputElement.textContent = `Execution Error: ${error.message}`;
        container.querySelector('.code-block-content').appendChild(outputElement);
    } finally {
        button.innerHTML = originalText;
        button.disabled = false;
    }
}

async function executePythonCode(code) {
    try {
        if (typeof pyodide !== 'undefined') {
            return pyodide.runPython(code);
        }
        
        const response = await fetch('/execute-python', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ code: code })
        });
        
        if (response.ok) {
            const result = await response.json();
            return result.output || result.error || 'No output';
        } else {
            return 'Error: Could not execute Python code';
        }
        
    } catch (error) {
        console.warn('Python execution fallback:', error);
        return simulatePythonExecution(code);
    }
}

function simulatePythonExecution(code) {
    try {
        const printMatch = code.match(/print\((.*?)\)/);
        if (printMatch) {
            let arg = printMatch[1].trim();
            if (arg.startsWith('"') && arg.endsWith('"')) {
                return arg.slice(1, -1);
            }
            if (arg.startsWith("'") && arg.endsWith("'")) {
                return arg.slice(1, -1);
            }
        }
        
        const mathMatch = code.match(/^(\d+\s*[+\-*/]\s*\d+)$/);
        if (mathMatch) {
            return String(eval(mathMatch[1]));
        }
        
        return 'Python code simulation - install Pyodide or backend execution for full support';
    } catch (error) {
        return `Simulation Error: ${error.message}`;
    }
}

function addErrorMessage(text) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = text;
    chatMessages.appendChild(errorDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showTypingIndicator() {
    typingIndicator.style.display = 'flex';
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function hideTypingIndicator() {
    typingIndicator.style.display = 'none';
}

// Show Me Commands & Visual Effects
// ================================

function handleShowMeCommand(item, originalMessage) {
    chatInput.disabled = true;
    sendButton.disabled = true;
    chatInput.value = '';
    
    addMessage(originalMessage, 'user');
    
    let responseMessage = '';
    let effectType = '';
    
    if (item.match(/balloo?ns?|baloons?/i)) {
        responseMessage = "🎈 Here are some colorful balloons for you! 🎈";
        effectType = 'balloons';
    } else if (item.match(/stars?/i)) {
        responseMessage = "⭐ Look at these twinkling stars! ⭐";
        effectType = 'stars';
    } else if (item.match(/hearts?|love/i)) {
        responseMessage = "💖 Sending you some love with hearts! 💖";
        effectType = 'hearts';
    } else if (item.match(/confetti|celebration|party/i)) {
        responseMessage = "🎉 Let's celebrate with confetti! 🎉";
        effectType = 'confetti';
    } else if (item.match(/fireworks?/i)) {
        responseMessage = "🎆 Enjoy these beautiful fireworks! 🎆";
        effectType = 'fireworks';
    } else {
        responseMessage = `I'd love to show you ${item}, but I can currently display: balloons, stars, hearts, confetti, or fireworks! Try "Show me balloons" 🎈`;
        effectType = 'none';
    }
    
    setTimeout(() => {
        addMessage(responseMessage, 'bot');
        
        if (effectType !== 'none') {
            showVisualEffect(effectType);
        }
        
        chatInput.disabled = false;
        sendButton.disabled = false;
        chatInput.focus();
    }, 500);
}

function triggerShowMeEffect(effectType, effectName) {
    addMessage(`Show me ${effectName.toLowerCase()}`, 'user');
    
    let responseMessage = '';
    
    if (effectType === 'balloons') {
        responseMessage = "🎈 Here are some colorful balloons for you! 🎈";
    } else if (effectType === 'stars') {
        responseMessage = "⭐ Look at these twinkling stars! ⭐";
    } else if (effectType === 'hearts') {
        responseMessage = "💖 Sending you some love with hearts! 💖";
    } else if (effectType === 'confetti') {
        responseMessage = "🎉 Let's celebrate with confetti! 🎉";
    } else if (effectType === 'fireworks') {
        responseMessage = "🎆 Enjoy these beautiful fireworks! 🎆";
    }
    
    setTimeout(() => {
        addMessage(responseMessage, 'bot');
        showVisualEffect(effectType);
    }, 300);
}

function showVisualEffect(type) {
    const container = document.querySelector('.chat-container');
    const effects = [];
    
    const count = type === 'confetti' ? 20 : 8;
    
    for (let i = 0; i < count; i++) {
        const effect = document.createElement('div');
        
        let effectClass = '';
        if (type === 'balloons') {
            effectClass = 'balloon';
        } else if (type === 'stars') {
            effectClass = 'star';
        } else if (type === 'hearts') {
            effectClass = 'heart';
        } else if (type === 'confetti') {
            effectClass = 'confetti';
        } else if (type === 'fireworks') {
            effectClass = 'firework';
        }
        
        effect.className = `visual-effect ${effectClass}`;
        
        const left = Math.random() * (container.offsetWidth - 50);
        const animationDelay = Math.random() * 2;
        
        effect.style.position = 'absolute';
        effect.style.left = left + 'px';
        effect.style.animationDelay = animationDelay + 's';
        effect.style.zIndex = '1000';
        
        if (type === 'balloons') {
            const colors = ['red', 'blue', 'yellow', 'green', 'purple'];
            effect.classList.add(colors[Math.floor(Math.random() * colors.length)]);
            effect.style.top = (container.offsetHeight - 100) + 'px';
        } else if (type === 'confetti') {
            const colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#95e1d3', '#a8e6cf'];
            effect.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            effect.style.top = '-10px';
        } else if (type === 'fireworks') {
            const colors = ['#ff6b6b', '#4ecdc4', '#ffe66d', '#95e1d3', '#a8e6cf', '#ffd700'];
            effect.style.backgroundColor = colors[Math.floor(Math.random() * colors.length)];
            effect.style.top = Math.random() * (container.offsetHeight / 2) + 'px';
        } else {
            effect.style.top = Math.random() * (container.offsetHeight - 100) + 'px';
        }
        
        container.appendChild(effect);
        effects.push(effect);
    }
    
    setTimeout(() => {
        effects.forEach(effect => {
            if (effect.parentNode) {
                effect.parentNode.removeChild(effect);
            }
        });
    }, 4000);
}

// Event Listeners & Initialization
// ===============================

function initializeApp() {
    // Apply saved theme on page load
    document.documentElement.setAttribute('data-theme', currentTheme);
    updateThemeButton();
    updateSoundButton();
    
    // Focus on input when page loads
    chatInput.focus();
    
    // Load sessions on page load
    loadSessions();
    
    // Theme toggle functionality
    themeToggle.addEventListener('click', function() {
        currentTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', currentTheme);
        localStorage.setItem('theme', currentTheme);
        updateThemeButton();
    });

    // Sound toggle functionality
    soundToggle.addEventListener('click', function() {
        userSoundPreference = !userSoundPreference;
        localStorage.setItem('soundNotifications', userSoundPreference ? 'enabled' : 'disabled');
        updateSoundButton();
        
        // Give user feedback about the change
        if (userSoundPreference) {
            // Play a quick test sound when enabling
            playNotificationSound();
        }
    });

    // Search functionality
    searchInput.addEventListener('input', function(e) {
        const query = e.target.value.trim();
        
        searchClear.style.display = query ? 'flex' : 'none';
        
        if (searchTimeout) {
            clearTimeout(searchTimeout);
        }
        
        if (query.length >= 2) {
            searchTimeout = setTimeout(() => {
                performSearch(query);
            }, 300);
        } else {
            hideSearchResults();
        }
    });

    searchClear.addEventListener('click', function() {
        searchInput.value = '';
        searchClear.style.display = 'none';
        hideSearchResults();
        searchInput.focus();
    });

    // Handle search scope change
    document.querySelectorAll('input[name="searchScope"]').forEach(radio => {
        radio.addEventListener('change', function() {
            const query = searchInput.value.trim();
            if (query.length >= 2) {
                performSearch(query);
            }
        });
    });

    // Sidebar toggle functionality
    toggleSidebar.addEventListener('click', function() {
        sidebar.classList.add('collapsed');
    });

    sidebarToggleMain.addEventListener('click', function() {
        sidebar.classList.toggle('collapsed');
    });

    // New chat button
    newChatButton.addEventListener('click', function() {
        startNewChat();
    });

    // Show me dropdown functionality
    showMeButton.addEventListener('click', function(e) {
        e.stopPropagation();
        dropdownContent.classList.toggle('show');
    });

    // Close dropdown when clicking outside
    document.addEventListener('click', function(e) {
        if (!showMeButton.contains(e.target) && !dropdownContent.contains(e.target)) {
            dropdownContent.classList.remove('show');
        }
    });

    // Handle dropdown item clicks
    dropdownContent.addEventListener('click', function(e) {
        if (e.target.classList.contains('dropdown-item')) {
            const effect = e.target.getAttribute('data-effect');
            const effectName = e.target.textContent.trim().split(' ')[1];
            
            dropdownContent.classList.remove('show');
            triggerShowMeEffect(effect, effectName);
        }
    });

    // Send message on Enter key
    chatInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });

    // Command history navigation with arrow keys
    chatInput.addEventListener('keydown', function(e) {
        if (e.key === 'ArrowUp') {
            e.preventDefault();
            navigateHistory('up');
        } else if (e.key === 'ArrowDown') {
            e.preventDefault();
            navigateHistory('down');
        } else if (e.key !== 'ArrowUp' && e.key !== 'ArrowDown' && historyIndex === -1) {
            currentInput = this.value;
        }
    });

    // Send message on button click
    sendButton.addEventListener('click', sendMessage);

    // Auto-resize input based on content
    chatInput.addEventListener('input', function() {
        if (this.value.length > 100) {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        } else {
            this.style.height = '';
        }
    });
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp);
