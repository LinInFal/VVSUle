function initDarkTheme() {
    const moonIcon = document.querySelector('#theme-toggle i');
    const themeToggle = document.querySelector('#theme-toggle');
    
    // Проверяем сохраненную тему в localStorage
    const savedTheme = localStorage.getItem('theme');
    const isDarkTheme = savedTheme === 'dark';
    
    // Применяем начальную тему
    if (isDarkTheme) {
        document.body.classList.add('dark-theme');
        moonIcon.classList.remove('bi-moon');
        moonIcon.classList.add('bi-moon-fill');
    }
    
    // Обработчик переключения темы
    themeToggle.addEventListener('click', function() {
        const isCurrentlyDark = document.body.classList.contains('dark-theme');
        
        if (isCurrentlyDark) {
            // Переключаем на светлую тему
            document.body.classList.remove('dark-theme');
            moonIcon.classList.remove('bi-moon-fill');
            moonIcon.classList.add('bi-moon');
            localStorage.setItem('theme', 'light');
        } else {
            // Переключаем на темную тему
            document.body.classList.add('dark-theme');
            moonIcon.classList.remove('bi-moon');
            moonIcon.classList.add('bi-moon-fill');
            localStorage.setItem('theme', 'dark');
        }
    });
}

// Инициализируем когда DOM готов
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initDarkTheme);
} else {
    initDarkTheme();
}