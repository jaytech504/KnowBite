window.MathJax = {
    tex: {
      inlineMath: [['$', '$'], ['\\(', '\\)']],
      displayMath: [['$$', '$$'], ['\\[', '\\]']],
      processEscapes: true
    },
    svg: {
      fontCache: 'global'
    }
  };

  

// Function to get CSRF cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

document.addEventListener('DOMContentLoaded', function() {
    const userMessageInput = document.getElementById('user-message');
    const sendButton = document.getElementById('send-button');
    const chatMessages = document.getElementById('chat-messages');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Hide loading indicator initially
    loadingIndicator.style.display = 'none';
    
    sendButton.addEventListener('click', sendMessage);
    userMessageInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendMessage();
        }

    MathJax.typesetPromise(document.querySelectorAll('.message.bot'));
    });
    function addBotMessage(content) {
        const botMessageElement = document.createElement('div');
        botMessageElement.className = 'message bot';
        
        // Use Marked.js to render markdown
        botMessageElement.innerHTML = marked.parse(content);
        chatMessages.appendChild(botMessageElement);
        
        MathJax.typesetPromise([botMessageElement]).then(() => {
            // Scroll to bottom of chat after rendering is complete
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
    function sendMessage() {
        const message = userMessageInput.value.trim();
        if (!message) return;
        
        // Add user message to chat
        const userMessageElement = document.createElement('div');
        userMessageElement.className = 'message user';
        userMessageElement.textContent = message;
        chatMessages.appendChild(userMessageElement);
        
        // Clear input
        userMessageInput.value = '';
        
        // Show loading indicator
        loadingIndicator.style.display = 'block';
        
        // Get CSRF token
        const csrftoken = getCookie('csrftoken');
        
        // Prepare form data
        const formData = new FormData();
        formData.append('message', message);
        
        // Send request to backend
        fetch(`/summary/${fileId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            loadingIndicator.style.display = 'none';
            
            if (data.error) {
                console.error('Error:', data.error);
                // Show error message
                const errorElement = document.createElement('div');
                errorElement.className = 'message error';
                errorElement.textContent = 'Sorry, there was an error processing your request.';
                chatMessages.appendChild(errorElement);
            } else {
                // Add bot response to chat
                addBotMessage(data.response);
            }
            
            // Scroll to bottom of chat
            chatMessages.scrollTop = chatMessages.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicator.style.display = 'none';
            
            // Show error message
            const errorElement = document.createElement('div');
            errorElement.className = 'message error';
            errorElement.textContent = 'Sorry, there was an error connecting to the server.';
            chatMessages.appendChild(errorElement);
            
            // Scroll to bottom of chat
            chatMessages.scrollTop = chatMessages.scrollHeight;
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const userMessageChat = document.getElementById('user-message-chat');
    const sendChat = document.getElementById('send-button-chat');
    const chatMessage = document.getElementById('chat-messages-chat');
    const loadingIndicators = document.getElementById('loading-indicator-chat');
    
    // Hide loading indicator initially
    loadingIndicators.style.display = 'none';
    
    sendChat.addEventListener('click', sendChatMessage);
    userMessageChat.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            sendChatMessage();
        }

    MathJax.typesetPromise(document.querySelectorAll('.message-chat.bot'));
    });
    function addChatMessage(content) {
        const botMessageChat = document.createElement('div');
        botMessageChat.className = 'message-chat bot';
        
        // Use Marked.js to render markdown
        botMessageChat.innerHTML = marked.parse(content);
        chatMessage.appendChild(botMessageChat);
        
        MathJax.typesetPromise([botMessageChat]).then(() => {
            // Scroll to bottom of chat after rendering is complete
            chatMessage.scrollTop = chatMessage.scrollHeight;
        });
    }
    function sendChatMessage() {
        const messages = userMessageChat.value.trim();
        if (!messages) return;
        
        // Add user message to chat
        const userMessageEle = document.createElement('div');
        userMessageEle.className = 'message-chat user';
        userMessageEle.textContent = messages;
        chatMessage.appendChild(userMessageEle);
        
        // Clear input
        userMessageChat.value = '';
        
        // Show loading indicator
        loadingIndicators.style.display = 'block';
        
        // Get CSRF token
        const csrftoken = getCookie('csrftoken');
        
        // Prepare form data
        const formData = new FormData();
        formData.append('message-chat', messages);
        
        // Send request to backend
        fetch(`/chatbot/${fileId}/`, {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrftoken
            },
            body: formData
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            // Hide loading indicator
            loadingIndicators.style.display = 'none';
            
            if (data.error) {
                console.error('Error:', data.error);
                // Show error message
                const errorElement = document.createElement('div');
                errorElement.className = 'message-chat error';
                errorElement.textContent = 'Sorry, there was an error processing your request.';
                chatMessage.appendChild(errorElement);
            } else {
                // Add bot response to chat
                addChatMessage(data.response);
            }
            
            // Scroll to bottom of chat
            chatMessage.scrollTop = chatMessage.scrollHeight;
        })
        .catch(error => {
            console.error('Error:', error);
            loadingIndicators.style.display = 'none';
            
            // Show error message
            const errorElement = document.createElement('div');
            errorElement.className = 'message-chat error';
            errorElement.textContent = 'Sorry, there was an error connecting to the server.';
            chatMessage.appendChild(errorElement);
            
            // Scroll to bottom of chat
            chatMessage.scrollTop = chatMessage.scrollHeight;
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('regenerateBtn');
    const confirmDialog = document.getElementById('regenerateConfirm');
    const loadingIndicator = document.getElementById('loading-indicator');
    
    // Confirmation Dialog Handlers
    btn.addEventListener('click', function() {
        confirmDialog.style.display = 'block';
    });

    document.getElementById('confirmRegenerate').addEventListener('click', function() {
        confirmDialog.style.display = 'none';
        startRegeneration();
    });

    document.getElementById('cancelRegenerate').addEventListener('click', function() {
        confirmDialog.style.display = 'none';
    });

    // AJAX Regeneration
    function startRegeneration() {
        btn.classList.add('loading');
        loadingIndicator.style.display = 'block';
        
        const csrftoken = getCookie('csrftoken');
        
        fetch(`/summary/${fileId}/?regenerate=true`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrftoken
            },
            credentials: 'same-origin'
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Network response was not ok');
            }
            return response.json();
        })
        .then(data => {
            if (data.summary) {
                // Convert markdown to HTML if needed
                const processedHtml = marked.parse(data.summary);
                document.getElementById('summaryContent').innerHTML = processedHtml;

                if (typeof MathJax !== 'undefined') {
                    MathJax.typesetPromise([document.getElementById('summaryContent')]).catch(err => {
                        console.error('MathJax rendering error:', err);
                    });
                }
            } else if (data.error) {
                alert(data.error);
            }
        })
        .catch(error => {
            alert('Request failed: ' + error.message);
        })
        .finally(() => {
            btn.classList.remove('loading');
            loadingIndicator.style.display = 'none';
        });
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Resizable split panel functionality
    const resizeHandle = document.querySelector('.resize-handle');
    const summarySection = document.getElementById('summary-section');
    const chatbotSection = document.getElementById('chatbot-section');
    
    let isResizing = false;
    let lastX = 0;
    
    resizeHandle.addEventListener('mousedown', (e) => {
      isResizing = true;
      lastX = e.clientX;
      document.body.style.cursor = 'col-resize';
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', stopResize);
      e.preventDefault(); // Prevent text selection during drag
    });
    
    function handleMouseMove(e) {
      if (!isResizing) return;
      
      const dx = e.clientX - lastX;
      const summaryWidth = summarySection.getBoundingClientRect().width;
      const newSummaryWidth = summaryWidth + dx;
      
      // Set minimum and maximum widths
      if (newSummaryWidth > 200 && newSummaryWidth < window.innerWidth - 300) {
        summarySection.style.flex = '0 0 ' + newSummaryWidth + 'px';
        lastX = e.clientX;
      }
    }
    
    function stopResize() {
      isResizing = false;
      document.body.style.cursor = '';
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', stopResize);
    }
    
  });

document.addEventListener('DOMContentLoaded', function() {
    const darkMode = document.cookie.split('; ').find(row => row.startsWith('dark_mode='));
    if (darkMode && darkMode.split('=')[1] === 'true') {
        document.body.classList.add('dark-mode');
        document.getElementById('dark-mode-toggle').checked = true;
    }
})

document.getElementById('dark-mode-toggle').addEventListener('change', function() {
    fetch("{% url 'toggle_dark_mode' %}", {
        method: 'POST',
        headers: {
            'X-CSRFToken': '{{ csrf_token }}',
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({})
    }).then(response => response.json())
      .then(data => {
        if (data.success) {
            document.body.classList.toggle('dark-mode');
            location.reload();
        }
      });
});


function updateDifficultyLabel(value) {
    const labels = document.querySelectorAll('.slider-label');
    let difficultyText = document.getElementById('difficulty').value;
    labels.forEach(label => label.classList.remove('active'));
    
    if(value == 1) {
        document.querySelector('.slider-label[data-value="1"]').classList.add('active');
    } else if(value == 2) {
        document.querySelector('.slider-label[data-value="2"]').classList.add('active');
    } else if(value == 3) { 
        document.querySelector('.slider-label[data-value="3"]').classList.add('active');
    }
}

document.addEventListener('DOMContentLoaded', function() {
    // Update progress as questions are answered
    const questionCards = document.querySelectorAll('.question-card');
    const progressBar = document.querySelector('.progress-bar');
    const progressText = document.querySelector('.progress-text');
    
    // Initialize progress
    updateProgress();
    
    // Add event listeners to all radio buttons
    document.querySelectorAll('.option input').forEach(radio => {
        radio.addEventListener('change', function() {
            const questionCard = this.closest('.question-card');
            questionCard.querySelector('.question-status').classList.add('answered');
            updateProgress();
        });
    });
    
    function updateProgress() {
        const answered = document.querySelectorAll('.question-status.answered').length;
        const total = questionCards.length;
        const percentage = (answered / total) * 100;
        
        progressBar.style.width = percentage + '%';
        progressText.textContent = answered + '/' + total + ' answered';
        
        // Enable submit button if all answered (optional)
        if (answered === total) {
            document.querySelector('.submit-btn').style.opacity = '1';
        }
    }
});

document.addEventListener('DOMContentLoaded', function() {
    // Animate score circle
    const scoreCircles = document.querySelectorAll('.score-circle');
    scoreCircles.forEach(circle => {
        const score = parseInt(circle.getAttribute('data-score'));
        const fill = circle.querySelector('.score-fill');
        const circumference = 2 * Math.PI * 45;
        const offset = circumference - (score / 100) * circumference;
        
        fill.style.strokeDashoffset = offset;
    });
});