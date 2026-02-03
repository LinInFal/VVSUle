function initMainApp() {
    // Переменные для хранения данных
    let currentWeekIndex = 0;
    let allWeeksSchedule = [];
    let currentGroup = '';
    let currentMode = 'schedule'; // 'schedule' или 'weather'
    let swipeEnabled = true;
    
    // Элементы DOM
    const searchInput = document.querySelector('.search input');
    const clearBtn = document.querySelector('.btn');
    const searchBtn = document.querySelector('.btn2');
    const scheduleContainer = document.querySelector('.schedule');
    const prevWeekBtn = document.querySelector('.nav-btn:first-child');
    const nextWeekBtn = document.querySelector('.nav-btn:last-child');
    const searchContainer = document.querySelector('.search');
    const titleElement = document.querySelector('.title');
    const cloudIcon = document.querySelector('#weather-icon i');
    const weatherTitle = document.querySelector('.weather-title');
    const footer = document.querySelector('.footer');

    // Сохраняем оригинальный заголовок
    const originalTitle = titleElement ? titleElement.textContent : '';
    
    // Обработчик очистки поля ввода
    clearBtn.addEventListener('click', function() {
        searchInput.value = '';
        searchInput.focus();
    });
    
    // Обработчик поиска расписания
    searchBtn.addEventListener('click', async function() {
        const groupName = searchInput.value.trim();
        
        // Приводим к верхнему регистру
        const normalizedGroup = groupName.toUpperCase();
        currentGroup = normalizedGroup;

        // Включаем свайпы при переходе в режим расписания
        swipeEnabled = true;
        
        // Показать индикатор загрузки
        showLoading();
        
        try {
            // Запрос к API для парсинга расписания
            const response = await fetch(`/api/schedule?group=${encodeURIComponent(groupName)}`);
            
            if (!response.ok) {
                throw new Error(`HTTP ошибка: ${response.status}`);
            }
            
            const data = await response.json();
            
            if (data.success && data.schedule) {
                allWeeksSchedule = data.schedule.weeks || [];
                currentWeekIndex = 0;
                
                if (allWeeksSchedule.length > 0) {
                    displaySchedule(allWeeksSchedule[currentWeekIndex]);
                    updateWeekButtons();
                } else {
                    showNoSchedule();
                }
            } else {
                showError(data.message || 'Не удалось загрузить расписание');
            }
        } catch (error) {
            console.error('Ошибка:', error);
            showError(`Ошибка подключения к серверу: ${error.message}`);
        }
    });

    // Обработчик погоды (иконка облака)
    cloudIcon.parentElement.addEventListener('click', async function() {
        if (currentMode === 'weather') {
            // Если уже в режиме погоды, возвращаемся к расписанию
            returnToSchedule();
        } else {
            // Переключаемся на погоду
            currentMode = 'weather';

            // Блокируем свайпы в режиме погоды
            swipeEnabled = false;
            
            // Меняем иконку
            cloudIcon.classList.remove('bi-cloud-rain');
            cloudIcon.classList.add('bi-cloud-rain-fill');

            // Показываем заголовок погоды
            weatherTitle.style.display = 'block';
            
            // Скрываем поиск
            searchContainer.style.display = 'none';
            
            // Скрываем кнопки навигации
            if (footer) footer.style.display = 'none';
            
            // Показываем загрузку
            showWeatherLoading();
            
            try {
                // Запрос погоды
                const response = await fetch('/api/weather');
                
                if (!response.ok) {
                    throw new Error(`HTTP ошибка: ${response.status}`);
                }
                
                const data = await response.json();
                
                if (data.success && data.forecast) {
                    displayWeather(data.forecast);
                } else {
                    showError(data.message || 'Не удалось загрузить погоду');
                }
            } catch (error) {
                console.error('Ошибка:', error);
                showError(`Ошибка загрузки погоды: ${error.message}`);
            }
        }
    });

    // Функция возврата к расписанию
    function returnToSchedule() {
        currentMode = 'schedule';
        
        // Возвращаем иконку
        cloudIcon.classList.remove('bi-cloud-rain-fill');
        cloudIcon.classList.add('bi-cloud-rain');

        // Скрываем заголовок погоды
        weatherTitle.style.display = 'none';
        
        // Показываем поиск и возвращаем заголовок
        searchContainer.style.display = 'flex';
        
        // Очищаем контейнер
        scheduleContainer.innerHTML = '';
        scheduleContainer.style.display = 'none';
        
        // Скрываем футер
        if (footer) footer.style.display = 'none';
    }

    // Обработчик предыдущей недели
    if (prevWeekBtn) {
        prevWeekBtn.addEventListener('click', function() {
            if (currentWeekIndex > 0 && allWeeksSchedule.length > 0) {
                currentWeekIndex--;
                displaySchedule(allWeeksSchedule[currentWeekIndex]);
                updateWeekButtons();
            }
        });
    }
    
    // Обработчик следующей недели
    if (nextWeekBtn) {
        nextWeekBtn.addEventListener('click', function() {
            if (currentWeekIndex < allWeeksSchedule.length - 1 && allWeeksSchedule.length > 0) {
                currentWeekIndex++;
                displaySchedule(allWeeksSchedule[currentWeekIndex]);
                updateWeekButtons();
            }
        });
    }
    
    // Обработка Enter в поле ввода
    searchInput.addEventListener('keypress', function(e) {
        if (e.key === 'Enter') {
            searchBtn.click();
        }
    });
    
    // Инициализация свайпов
    initSwipeGestures();
    
    // Вспомогательные функции
    function showLoading() {
        scheduleContainer.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p>Загружаем расписание для группы ${currentGroup}...</p>
            </div>
        `;
        
        // Показать контейнер расписания, если он был скрыт
        scheduleContainer.style.display = 'block';
        if (footer) footer.style.display = 'flex';
    }

    function showWeatherLoading() {
        scheduleContainer.innerHTML = `
            <div class="loading">
                <div class="spinner"></div>
                <p class="loading-message">Загружаем погоду во Владивостоке...</p>
            </div>
        `;
        
        // Показать контейнер
        scheduleContainer.style.display = 'block';
    }
    
    function displaySchedule(scheduleData) {
        if (!scheduleData || scheduleData.length === 0) {
            showNoSchedule();
            return;
        }

        // Группируем занятия по дням
        const groupedByDate = {};
        scheduleData.forEach(lesson => {
            const date = lesson['Дата'] || 'Без даты';
            if (!groupedByDate[date]) {
                groupedByDate[date] = [];
            }
            groupedByDate[date].push(lesson);
        });
        
        // Создаем HTML для расписания
        let scheduleHTML = '';
        let isFirstDay = true;
        
        Object.keys(groupedByDate).forEach(date => {
            scheduleHTML += `
                <div class="day ${isFirstDay ? 'first' : ''}">
                    <div class="day-title ${isFirstDay ? 'first' : ''}">● ${formatDate(date)}</div>
            `;
            
            groupedByDate[date].forEach((lesson, index) => {
                scheduleHTML += `
                    <div class="lesson">
                        <div class="time">${lesson['Время'] || '??:?? – ??:??'}</div>
                        <div class="name">${lesson['Дисциплина'] || 'Не указано'}</div>
                        <div class="place">${lesson['Аудитория'] || 'Аудитория не указана'}</div>
                        <div class="teacher">${lesson['Преподаватель'] || 'Преподаватель не указан'}</div>
                        <div class="type">${lesson['Тип занятия'] || 'Тип не указан'}</div>
                    </div>
                `;
            });
            
            scheduleHTML += `</div>`;
            isFirstDay = false;
        });
        
        scheduleContainer.innerHTML = scheduleHTML;
        scheduleContainer.style.display = 'block';
    }

    function displayWeather(forecastData) {
        if (!forecastData || forecastData.length === 0) {
            showNoWeather();
            return;
        }
        
        let weatherHTML = '';
        
        forecastData.forEach((day, index) => {
            weatherHTML += `
                <div class="weather-day">
                    <div class="weather-header  ${index === 0 ? 'first' : ''}">
                        <span class="weather-icon">${day.condition_icon}</span>
                        <span class="weather-date">${day.date_display}</span>
                    </div>
                    <div class="weather-content">
                        <div class="weather-temp-container">
                            <div class="weather-temp">
                                <span class="temp-value">${day.temperature}</span>
                                <span class="temp-unit">°C</span>
                            </div>
                        </div>
                        <div class="weather-details">
                            <div class="weather-detail">
                                <span class="detail-label">Скорость ветра:</span>
                                <span class="detail-value">${day.wind_speed} м/с (${day.wind_direction})</span>
                            </div>
                            <div class="weather-detail">
                                <span class="detail-label">Влажность:</span>
                                <span class="detail-value">${day.humidity}%</span>
                            </div>
                            <div class="weather-detail">
                                <span class="detail-label">Осадки:</span>
                                <span class="detail-value">${day.precipitation} мм</span>
                            </div>
                        </div>
                    </div>
                </div>
            `;
        });
        
        scheduleContainer.innerHTML = weatherHTML;
        scheduleContainer.style.display = 'block';
    }
    
    function formatDate(dateStr) {
        // Преобразуем дату из формата "Понедельник 01.01.2001"
        // или возвращаем как есть, если не удалось распарсить
        return dateStr;
    }
    
    function showNoSchedule() {
        scheduleContainer.innerHTML = `
            <div class="no-schedule">
                <p>📭 Расписание для группы "${currentGroup}" не найдено</p>
                <p>Проверьте правильность написания группы</p>
            </div>
        `;
        
        // Скрыть кнопки навигации
        if (footer) footer.style.display = 'none';
    }

    function showNoWeather() {
        scheduleContainer.innerHTML = `
            <div class="no-schedule">
                <p class="no-schedule-message">📭 Не удалось загрузить прогноз погоды</p>
                <p class="no-schedule-message">Попробуйте позже</p>
            </div>
        `;
    }
    
    function showError(message) {
        scheduleContainer.innerHTML = `
            <div class="error">
                <p>❌ Ошибка</p>
                <p>${message}</p>
                <button class="retry-btn">Повторить попытку</button>
            </div>
        `;

        // Показать контейнер расписания
        scheduleContainer.style.display = 'block';
        if (footer) footer.style.display = 'none';
        
        // Добавляем обработчик для кнопки повтора
        const retryBtn = scheduleContainer.querySelector('.retry-btn');
        if (retryBtn) {
            retryBtn.addEventListener('click', function() {
                searchBtn.click();
            });
        }
    }
    
    function updateWeekButtons() {
        if (!prevWeekBtn || !nextWeekBtn) return;
        
        // Обновляем состояние кнопок навигации
        prevWeekBtn.disabled = currentWeekIndex === 0;
        nextWeekBtn.disabled = currentWeekIndex === allWeeksSchedule.length - 1;
        
        // Визуальная обратная связь
        prevWeekBtn.style.opacity = prevWeekBtn.disabled ? '0.5' : '1';
        prevWeekBtn.style.cursor = prevWeekBtn.disabled ? 'not-allowed' : 'pointer';

        nextWeekBtn.style.opacity = nextWeekBtn.disabled ? '0.5' : '1';
        nextWeekBtn.style.cursor = nextWeekBtn.disabled ? 'not-allowed' : 'pointer';
    }
    
    function initSwipeGestures() {
        let startX = 0;
        let endX = 0;
        
        scheduleContainer.addEventListener('touchstart', function(e) {
            if (!swipeEnabled) return; // Проверяем, разрешены ли свайпы
            startX = e.changedTouches[0].screenX;
        }, { passive: true });
        
        scheduleContainer.addEventListener('touchend', function(e) {
            if (!swipeEnabled) return;
            endX = e.changedTouches[0].screenX;
            handleSwipe();
        }, { passive: true });
        
        function handleSwipe() {
            const minSwipeDistance = 50;
            const distance = endX - startX;
            
            if (Math.abs(distance) < minSwipeDistance) return;
            
            if (distance > 0) {
                // Свайп вправо = предыдущая неделя
                if (prevWeekBtn && !prevWeekBtn.disabled) {
                    prevWeekBtn.click();
                }
            } else {
                // Свайп влево = следующая неделя
                if (nextWeekBtn && !nextWeekBtn.disabled) {
                    nextWeekBtn.click();
                }
            }
        }
    }
}

// Инициализируем когда DOM готов
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initMainApp);
} else {
    initMainApp();
}