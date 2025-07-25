const sidebar = document.getElementById('sidebar');
const mainContent = document.getElementById('main-content');
const sidebarToggle = document.getElementById('sidebar-toggle');
const toggleIcon = document.getElementById('toggle-icon');

sidebarToggle.addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    mainContent.classList.toggle('expanded');
    
    // Change the toggle icon direction
    if (sidebar.classList.contains('collapsed')) {
        toggleIcon.classList.remove('bi-chevron-left');
        toggleIcon.classList.add('bi-chevron-right');
    } else {
        toggleIcon.classList.remove('bi-chevron-right');
        toggleIcon.classList.add('bi-chevron-left');
    }
});

// Mobile menu toggle
const mobileToggle = document.getElementById('mobile-toggle');
const mobileMenu = document.getElementById('mobile-menu');

mobileToggle.addEventListener('click', () => {
    mobileMenu.classList.toggle('show');
});

// Close mobile menu when clicking on a link
const mobileLinks = document.querySelectorAll('.mobile-menu .nav-link');
mobileLinks.forEach(link => {
    link.addEventListener('click', () => {
        mobileMenu.classList.remove('show');
    });
});

// Handle sidebar for mobile
const mobileShowSidebar = document.getElementById('mobile-toggle');
mobileShowSidebar.addEventListener('click', () => {
    sidebar.classList.toggle('mobile-show');
});

function showYoutubeInput() {
    document.getElementById('youtube-input').style.display = 'block';
}

function hideYoutubeInput() {
    document.getElementById('youtube-input').style.display = 'none';
    document.getElementById('youtube-link').value = '';
}

function triggerFileUpload(fileType) {
    document.getElementById('file_type').value = fileType;
    document.getElementById('file-input').accept = getAcceptAttribute(fileType);
    document.getElementById('file-input').click();
}

function getAcceptAttribute(fileType) {
    const acceptMap = {
        'pdf': '.pdf,.txt',
        'audio': '.mp3,.wav,.ogg,.m4a'
    };
    return acceptMap[fileType] || '';
}

// Updated submit function with loading bar
function submitForm() {
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length > 0) {
        showLoading();
        simulateProgress(); // For demo - replace with actual progress in real implementation
        document.getElementById('upload-form').submit();
    }
}

// Show loading overlay
function showLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'flex';
}

// Hide loading overlay
function hideLoading() {
    const overlay = document.getElementById('loading-overlay');
    overlay.style.display = 'none';
    resetProgress();
}

// Reset progress bar
function resetProgress() {
    document.getElementById('upload-progress').style.width = '0%';
    document.getElementById('progress-text').textContent = 'Processing your file...';
}

// Simulate progress (replace with real progress tracking in your implementation)
function simulateProgress() {
    const progressBar = document.getElementById('upload-progress');
    const progressText = document.getElementById('progress-text');
    let progress = 0;
    
    const interval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 90) progress = 90; // Don't go to 100% until actually done
        
        progressBar.style.width = progress + '%';
        
        if (progress < 30) {
            progressText.textContent = 'Uploading file...';
        } else if (progress < 60) {
            progressText.textContent = 'Processing content...';
        } else {
            progressText.textContent = 'Generating summary...';
        }
        
        if (progress >= 100) {
            clearInterval(interval);
        }
    }, 500);
    
    return interval;
}

// Updated YouTube form submission with loading
document.getElementById('youtube-form').addEventListener('submit', function(e) {
    const urlInput = document.getElementById('youtube-link');
    const youtubeRegex = /^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
    
    if (!youtubeRegex.test(urlInput.value)) {
        e.preventDefault();
        alert('Please enter a valid YouTube URL');
        urlInput.focus();
        return;
    }
    
    // Show loading for valid YouTube URL
    showLoading();
    const progressInterval = simulateProgress();
    // The progress will be interrupted when page changes
});

// Optional: Hide loading when navigating away
window.addEventListener('beforeunload', function() {
    hideLoading();
});