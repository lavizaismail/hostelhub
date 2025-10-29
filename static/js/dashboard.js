// Dashboard interactivity and animations
document.addEventListener('DOMContentLoaded', function() {
  // Animate stats on load
  animateStats();
  
  // Add hover effects to cards
  const cards = document.querySelectorAll('.stat-card, .dashboard-card');
  cards.forEach(card => {
    card.addEventListener('mouseenter', function() {
      this.style.transform = 'translateY(-5px) scale(1.02)';
    });
    
    card.addEventListener('mouseleave', function() {
      this.style.transform = 'translateY(0) scale(1)';
    });
  });
});

function animateStats() {
  const statValues = document.querySelectorAll('.stat-value');
  
  statValues.forEach(stat => {
    const finalValue = parseInt(stat.textContent) || 0;
    let currentValue = 0;
    const increment = finalValue / 50;
    
    const timer = setInterval(() => {
      currentValue += increment;
      if (currentValue >= finalValue) {
        stat.textContent = finalValue;
        clearInterval(timer);
      } else {
        stat.textContent = Math.floor(currentValue);
      }
    }, 20);
  });
}
