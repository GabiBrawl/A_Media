// Basic JavaScript functionality
document.addEventListener('DOMContentLoaded', function() {
    console.log('A_Media application loaded successfully!');

    // Basic functionality can be added here
    const header = document.querySelector('h1');
    if (header) {
        header.addEventListener('click', function() {
            alert('Welcome to A_Media!');
        });
    }
});