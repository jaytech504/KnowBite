// Initialize Firebase
const firebaseConfig = {
    apiKey: "AIzaSyDkwTdni0d0nDzMOPsQnsjGhFdavovrRVw",
    authDomain: "knowbite-dc17e.firebaseapp.com",
    projectId: "knowbite-dc17e",
    storageBucket: "knowbite-dc17e.firebasestorage.app",
    messagingSenderId: "613045162976",
    appId: "1:613045162976:web:294d0b77fbb1710382d185",
    measurementId: "G-F3N8PS644J"
};

// Initialize Firebase
firebase.initializeApp(firebaseConfig);

// Google Sign-in function
function signInWithGoogle() {
    const provider = new firebase.auth.GoogleAuthProvider();
    firebase.auth().signInWithPopup(provider)
        .then((result) => {
            // Get the Google access token
            const credential = result.credential;
            const token = credential.accessToken;
            const user = result.user;

            // Send the token to your Django backend
            fetch('/accounts/firebase-auth/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': getCookie('csrftoken')
                },
                body: JSON.stringify({
                    'token': token,
                    'uid': user.uid,
                    'email': user.email,
                    'display_name': user.displayName
                })
            })
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    window.location.href = data.redirect_url;
                }
            })
            .catch(error => {
                console.error('Error:', error);
            });
        })
        .catch((error) => {
            console.error('Error:', error);
        });
}

// Helper function to get CSRF token
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
