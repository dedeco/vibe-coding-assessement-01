// Condominium Analytics Agent - Frontend JavaScript

class CondominiumAnalytics {
    constructor() {
        this.apiBase = '';
        this.conversationId = 'default';
        this.recentQuestions = [];
        this.isLoading = false;
        
        this.initializeElements();
        this.bindEvents();
        this.checkSystemHealth();
    }
    
    initializeElements() {
        // Core elements
        this.questionInput = document.getElementById('questionInput');
        this.sendButton = document.getElementById('sendButton');
        this.messagesArea = document.getElementById('messagesArea');
        this.charCounter = document.getElementById('charCounter');
        
        // Status elements
        this.statusDot = document.getElementById('statusDot');
        this.statusText = document.getElementById('statusText');
        this.dbStatus = document.getElementById('dbStatus');
        this.aiStatus = document.getElementById('aiStatus');
        
        // UI elements
        this.loadingOverlay = document.getElementById('loadingOverlay');
        this.errorToast = document.getElementById('errorToast');
        this.errorMessage = document.getElementById('errorMessage');
        this.recentQuestionsEl = document.getElementById('recentQuestions');
        this.sidebarToggle = document.getElementById('sidebarToggle');
        this.sidebar = document.getElementById('sidebar');
        
        // Debug: Check if critical elements are found
        if (!this.questionInput) {
            console.error('Critical element not found: questionInput');
        }
        if (!this.recentQuestionsEl) {
            console.warn('Recent questions element not found');
        }
    }
    
    bindEvents() {
        // Input events
        if (this.questionInput) {
            this.questionInput.addEventListener('input', () => this.updateCharCounter());
            this.questionInput.addEventListener('keypress', (e) => this.handleKeyPress(e));
        }
        
        if (this.sendButton) {
            this.sendButton.addEventListener('click', () => this.sendQuestion());
        }
        
        // Sidebar events
        if (this.sidebarToggle) {
            this.sidebarToggle.addEventListener('click', () => this.toggleSidebar());
        }
        
        // Initialize input state
        this.updateCharCounter();
    }
    
    updateCharCounter() {
        if (!this.questionInput || !this.charCounter) {
            return;
        }
        
        const length = this.questionInput.value.length;
        this.charCounter.textContent = `${length}/500`;
        
        // Enable/disable send button
        if (this.sendButton) {
            const hasContent = length > 0 && !this.isLoading;
            this.sendButton.disabled = !hasContent;
        }
        
        // Update character counter color
        if (length > 450) {
            this.charCounter.style.color = 'var(--error-color)';
        } else if (length > 400) {
            this.charCounter.style.color = 'var(--warning-color)';
        } else {
            this.charCounter.style.color = 'var(--text-muted)';
        }
    }
    
    handleKeyPress(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            this.sendQuestion();
        }
    }
    
    async checkSystemHealth() {
        try {
            const response = await fetch('/health');
            const health = await response.json();
            
            this.updateSystemStatus(health);
        } catch (error) {
            console.error('Health check failed:', error);
            this.updateSystemStatus({ 
                status: 'unhealthy', 
                components: { chromadb: 'error', claude_api: 'error' },
                message: 'Connection failed'
            });
        }
    }
    
    updateSystemStatus(health) {
        // Update main status indicator
        this.statusDot.className = 'status-dot ' + 
            (health.status === 'healthy' ? 'connected' : 
             health.status === 'unhealthy' ? 'error' : '');
        this.statusText.textContent = health.message || health.status;
        
        // Update sidebar status
        if (this.dbStatus) {
            this.dbStatus.textContent = this.formatComponentStatus(health.components?.chromadb);
        }
        if (this.aiStatus) {
            this.aiStatus.textContent = this.formatComponentStatus(health.components?.claude_api);
        }
    }
    
    formatComponentStatus(status) {
        if (!status) return 'Unknown';
        if (status.includes('healthy')) return '✅ Ready';
        if (status.includes('configured')) return '✅ Ready';
        if (status.includes('not configured')) return '⚠️ Limited';
        if (status.includes('error')) return '❌ Error';
        return status;
    }
    
    async sendQuestion() {
        const question = this.questionInput.value.trim();
        if (!question || this.isLoading) return;
        
        // Add to recent questions
        this.addToRecentQuestions(question);
        
        // Clear input and show loading
        this.questionInput.value = '';
        this.updateCharCounter();
        this.showLoading();
        
        // Add user message to chat
        this.addMessage(question, 'user');
        
        try {
            const response = await fetch('/query', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    question: question,
                    conversation_id: this.conversationId
                })
            });
            
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }
            
            const result = await response.json();
            
            if (result.success) {
                this.addMessage(result.answer, 'assistant', result.suggestions);
            } else {
                throw new Error(result.error_message || 'Unknown error occurred');
            }
            
        } catch (error) {
            console.error('Query failed:', error);
            this.showError(`Failed to get response: ${error.message}`);
            this.addMessage(
                'Sorry, I encountered an error processing your question. Please try again.',
                'assistant'
            );
        } finally {
            this.hideLoading();
        }
    }
    
    addMessage(content, sender, suggestions = []) {
        // Remove welcome message if this is the first real message
        const welcomeMessage = this.messagesArea.querySelector('.welcome-message');
        if (welcomeMessage) {
            welcomeMessage.remove();
        }
        
        // Create message element
        const messageEl = document.createElement('div');
        messageEl.className = `message message-${sender}`;
        
        const contentEl = document.createElement('div');
        contentEl.className = 'message-content';
        
        const textEl = document.createElement('div');
        textEl.className = 'message-text';
        textEl.textContent = content;
        
        contentEl.appendChild(textEl);
        
        // Add suggestions for assistant messages
        if (sender === 'assistant' && suggestions.length > 0) {
            const suggestionsEl = document.createElement('div');
            suggestionsEl.className = 'suggestions';
            
            const titleEl = document.createElement('h4');
            titleEl.textContent = 'Suggested follow-up questions:';
            suggestionsEl.appendChild(titleEl);
            
            const buttonsEl = document.createElement('div');
            buttonsEl.className = 'suggestion-buttons';
            
            suggestions.forEach(suggestion => {
                const btnEl = document.createElement('button');
                btnEl.className = 'suggestion-btn';
                btnEl.textContent = suggestion;
                btnEl.addEventListener('click', () => this.askSuggestion(suggestion));
                buttonsEl.appendChild(btnEl);
            });
            
            suggestionsEl.appendChild(buttonsEl);
            contentEl.appendChild(suggestionsEl);
        }
        
        messageEl.appendChild(contentEl);
        this.messagesArea.appendChild(messageEl);
        
        // Scroll to bottom
        this.scrollToBottom();
    }
    
    askSuggestion(suggestion) {
        this.questionInput.value = suggestion;
        this.updateCharCounter();
        this.questionInput.focus();
    }
    
    scrollToBottom() {
        this.messagesArea.scrollTop = this.messagesArea.scrollHeight;
    }
    
    showLoading() {
        this.isLoading = true;
        this.loadingOverlay.classList.add('visible');
        this.sendButton.disabled = true;
        this.updateCharCounter();
    }
    
    hideLoading() {
        this.isLoading = false;
        this.loadingOverlay.classList.remove('visible');
        this.updateCharCounter();
    }
    
    showError(message) {
        this.errorMessage.textContent = message;
        this.errorToast.classList.add('visible');
        
        // Auto-hide after 5 seconds
        setTimeout(() => {
            this.hideError();
        }, 5000);
    }
    
    hideError() {
        this.errorToast.classList.remove('visible');
    }
    
    addToRecentQuestions(question) {
        // Add to beginning of array
        this.recentQuestions.unshift(question);
        
        // Keep only last 10
        this.recentQuestions = this.recentQuestions.slice(0, 10);
        
        // Update UI
        this.updateRecentQuestionsUI();
        
        // Store in localStorage
        localStorage.setItem('recentQuestions', JSON.stringify(this.recentQuestions));
    }
    
    updateRecentQuestionsUI() {
        if (!this.recentQuestionsEl) return;
        
        try {
            this.recentQuestionsEl.innerHTML = '';
            
            if (this.recentQuestions.length === 0) {
                const emptyEl = document.createElement('div');
                emptyEl.className = 'recent-question';
                emptyEl.textContent = 'No recent questions';
                emptyEl.style.opacity = '0.5';
                this.recentQuestionsEl.appendChild(emptyEl);
                return;
            }
            
            this.recentQuestions.forEach(question => {
            const questionEl = document.createElement('div');
            questionEl.className = 'recent-question';
            questionEl.textContent = question.length > 60 ? 
                question.substring(0, 60) + '...' : question;
            questionEl.title = question;
            questionEl.addEventListener('click', () => {
                try {
                    if (!this.questionInput) {
                        console.error('Question input element not found');
                        return;
                    }
                    this.questionInput.value = question;
                    this.updateCharCounter();
                    this.questionInput.focus();
                } catch (error) {
                    console.error('Error handling recent question click:', error);
                    this.showError('Failed to load recent question');
                }
            });
            this.recentQuestionsEl.appendChild(questionEl);
        });
        } catch (error) {
            console.error('Error updating recent questions UI:', error);
        }
    }
    
    loadRecentQuestions() {
        try {
            const stored = localStorage.getItem('recentQuestions');
            if (stored) {
                this.recentQuestions = JSON.parse(stored);
                this.updateRecentQuestionsUI();
            }
        } catch (error) {
            console.error('Failed to load recent questions:', error);
        }
    }
    
    toggleSidebar() {
        this.sidebar.classList.toggle('hidden');
    }
}

// Global functions for HTML onclick events
function askExample(question) {
    if (window.analytics) {
        window.analytics.questionInput.value = question;
        window.analytics.updateCharCounter();
        window.analytics.sendQuestion();
    }
}

function hideError() {
    if (window.analytics) {
        window.analytics.hideError();
    }
}

// Initialize the application when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    console.log('Initializing Condominium Analytics Agent...');
    
    window.analytics = new CondominiumAnalytics();
    window.analytics.loadRecentQuestions();
    
    console.log('✅ Application initialized successfully');
});

// Handle page visibility changes to reconnect if needed
document.addEventListener('visibilitychange', function() {
    if (!document.hidden && window.analytics) {
        // Re-check system health when page becomes visible
        setTimeout(() => {
            window.analytics.checkSystemHealth();
        }, 1000);
    }
});