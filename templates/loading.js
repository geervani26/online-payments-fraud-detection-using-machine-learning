// Add this to your pages
function showLoading(message = 'Processing...') {
    const loader = document.createElement('div');
    loader.className = 'custom-loader';
    loader.innerHTML = `
        <div class="loader-content">
            <div class="spinner"></div>
            <p>${message}</p>
            <div class="progress-bar">
                <div class="progress-fill"></div>
            </div>
        </div>
    `;
    document.body.appendChild(loader);
}

// Particle effect on button click
document.querySelector('button[type="submit"]')?.addEventListener('click', function(e) {
    createParticleEffect(e);
});

function createParticleEffect(event) {
    const button = event.target;
    const rect = button.getBoundingClientRect();
    
    for (let i = 0; i < 20; i++) {
        const particle = document.createElement('span');
        particle.className = 'particle';
        particle.style.left = (Math.random() * rect.width) + 'px';
        particle.style.top = (Math.random() * rect.height) + 'px';
        particle.style.background = `hsl(${Math.random() * 360}, 100%, 50%)`;
        button.appendChild(particle);
        
        setTimeout(() => particle.remove(), 1000);
    }
}