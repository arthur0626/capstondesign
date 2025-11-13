document.addEventListener('DOMContentLoaded', () => {
  
    const toggleBtn = document.getElementById('menu-toggle-btn');
    const sidebar = document.getElementById('sidebar');
    
    toggleBtn.addEventListener('click', () => {
        sidebar.classList.toggle('open'); 
    });

});