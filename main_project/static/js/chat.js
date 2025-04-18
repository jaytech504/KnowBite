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
    
    // Function to get CSRF token from cookies
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
});

document.addEventListener('DOMContentLoaded', function() {
    const btn = document.getElementById('regenerateBtn');
    const confirmDialog = document.getElementById('regenerateConfirm');
    const loadingIndicator = document.querySelector('.loading-indicator');
    
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
        loadingIndicator.style.display = 'flex';
        
        fetch(`/summary/${fileId}/?regenerate=true`, {
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': '{{ csrf_token }}'
            },
            credentials: 'same-origin'
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                // Convert markdown to HTML if needed
                const processedHtml = marked.parse(data.summary);
                document.getElementById('summaryContent').innerHTML = processedHtml;

                if (typeof MathJax !== 'undefined') {
                    MathJax.typesetPromise([summaryContent]).catch(err => {
                        console.error('MathJax rendering error:', err);
                    });
                }
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