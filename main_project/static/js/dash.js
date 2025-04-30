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

// Hide YouTube input field
function hideYoutubeInput() {
    document.getElementById('youtube-input').style.display = 'none';
    document.getElementById('youtube-link').value = '';
}

// Trigger file input based on type
function triggerFileUpload(fileType) {
    document.getElementById('file_type').value = fileType;
    document.getElementById('file-input').accept = getAcceptAttribute(fileType);
    document.getElementById('file-input').click();
}

// Get accept attribute based on file type
function getAcceptAttribute(fileType) {
    const acceptMap = {
        'pdf': '.pdf,.txt',
        'audio': '.mp3,.wav,.ogg,.m4a'
    };
    return acceptMap[fileType] || '';
}

// Submit form when file is selected
function submitForm() {
    const fileInput = document.getElementById('file-input');
    if (fileInput.files.length > 0) {
        document.getElementById('upload-form').submit();
    }
}

// Validate YouTube URL before submission
document.getElementById('youtube-form').addEventListener('submit', function(e) {
    const urlInput = document.getElementById('youtube-link');
    const youtubeRegex = /^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
    
    if (!youtubeRegex.test(urlInput.value)) {
        e.preventDefault();
        alert('Please enter a valid YouTube URL');
        urlInput.focus();
    }
});function showYoutubeInput() {
        document.getElementById('youtube-input').style.display = 'block';
    }

    // Hide YouTube input field
    function hideYoutubeInput() {
        document.getElementById('youtube-input').style.display = 'none';
        document.getElementById('youtube-link').value = '';
    }

    // Trigger file input based on type
    function triggerFileUpload(fileType) {
        document.getElementById('file_type').value = fileType;
        document.getElementById('file-input').accept = getAcceptAttribute(fileType);
        document.getElementById('file-input').click();
    }

    // Get accept attribute based on file type
    function getAcceptAttribute(fileType) {
        const acceptMap = {
            'pdf': '.pdf,.txt',
            'audio': '.mp3,.wav,.ogg,.m4a'
        };
        return acceptMap[fileType] || '';
    }

    // Submit form when file is selected
    function submitForm() {
        const fileInput = document.getElementById('file-input');
        if (fileInput.files.length > 0) {
            document.getElementById('upload-form').submit();
        }
    }

    // Validate YouTube URL before submission
    document.getElementById('youtube-form').addEventListener('submit', function(e) {
        const urlInput = document.getElementById('youtube-link');
        const youtubeRegex = /^(https?\:\/\/)?(www\.)?(youtube\.com|youtu\.?be)\/.+$/;
        
        if (!youtubeRegex.test(urlInput.value)) {
            e.preventDefault();
            alert('Please enter a valid YouTube URL');
            urlInput.focus();
        }
    });

