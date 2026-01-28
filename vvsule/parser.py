"""
Selenium-скрипт для парсинга расписания с сайта vvsu.ru.

"""

import time
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService


def setup_driver():
    """Настройка Firefox для быстрого парсинга"""
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.set_preference("permissions.default.image", 2)
    options.set_preference("dom.webdriver.enabled", False)
    options.set_preference("useAutomationExtension", False)
    options.set_preference("media.volume_scale", "0.0")
    options.set_preference("dom.webnotifications.enabled", False)
    options.set_preference("network.http.use-cache", False)
    options.set_preference("browser.cache.disk.enable", False)
    options.set_preference("browser.cache.memory.enable", False)
    options.set_preference("browser.cache.offline.enable", False)
    options.set_preference("network.dns.disableIPv6", True)
    options.set_preference("network.prefetch-next", False)
    options.set_preference("network.http.pipelining", True)
    options.set_preference("network.http.proxy.pipelining", True)
    options.set_preference("network.http.pipelining.maxrequests", 8)
    options.set_preference("browser.dom.window.dump.enabled", True)
    options.set_preference("devtools.console.stdout.content", True)
    
    # Устанавливаем путь к geckodriver
    # gecko_path = "/usr/local/bin/geckodriver"
    
    try:
        # service = FirefoxService(executable_path=gecko_path, log_path="/tmp/geckodriver.log")
        
        # driver = webdriver.Firefox(service=service, options=options)
        driver = webdriver.Firefox(options=options)

        logging.info("✅ Firefox драйвер успешно инициализирован")
        
        # Устанавливаем таймауты
        driver.set_page_load_timeout(5)
        driver.implicitly_wait(3)
        
        return driver
        
    except Exception as e:
        logging.error(f"Не удалось запустить драйвер: {e}")
        return None


def parse_vvsu_timetable(group_name):
    """Парсинг ВСЕХ доступных недель расписания"""
    logging.info(f"=== НАЧАЛО парсинга ВСЕХ недель для {group_name} ===")
    
    driver = None
    try:
        driver = setup_driver()
        if not driver:
            return {"success": False, "error": "Не удалось инициализировать драйвер", "weeks": []}
        
        # Открываем страницу
        logging.info("Открываю страницу расписания...")
        try:
            driver.get("https://www.vvsu.ru/timetable/")
            logging.info("Страница открыта")
        except Exception as e:
            logging.error(f"Ошибка при открытии страницы: {e}")
            return {"success": False, "error": f"Не удалось открыть страницу: {e}", "weeks": []}
        
        # Находим и заполняем поле
        logging.info("Ищу поле для ввода группы...")
        try:
            # Ждем загрузки страницы
            time.sleep(1)
            group_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "input#gr"))
            )
            group_input.clear()
            group_input.send_keys(group_name)
            logging.info(f"Ввел группу: {group_name}")
            time.sleep(1)  # Ждем появления списка
        except TimeoutException:
            logging.error("Таймаут при поиске поля ввода")
            return {"success": False, "error": "Не удалось найти поле ввода", "weeks": []}
        
        # Ищем и кликаем по группе
        logging.info("Ищу группу в списке...")
        try:
            # Ищем кнопку с точным текстом
            group_button = None
            buttons = driver.find_elements(By.TAG_NAME, "button")
            for button in buttons:
                if group_name in button.text:
                    group_button = button
                    break
            
            if group_button:
                driver.execute_script("arguments[0].click();", group_button)
                logging.info(f"Кликнул по группе {group_name}")
                time.sleep(2)  # Ждем загрузки расписания
            else:
                logging.error(f"Кнопка группы {group_name} не найдена")
                return {"success": False, "error": f"Группа {group_name} не найдена", "weeks": []}
        except Exception as e:
            logging.error(f"Ошибка при выборе группы: {e}")
            return {"success": False, "error": f"Ошибка при выборе группы: {e}", "weeks": []}
        
        # Парсим ВСЕ доступные недели
        all_weeks_schedule = []
        max_weeks_to_parse = 3  # Максимальное количество недель для парсинга
        
        # Парсим текущую (активную) неделю
        try:
            current_schedule = parse_current_week(driver)
            if current_schedule:
                all_weeks_schedule.append(current_schedule)
                logging.info(f"Текущая неделя: {len(current_schedule)} занятий")
        except Exception as e:
            logging.error(f"Ошибка при парсинге текущей недели: {e}")
        
        # Парсим следующие недели
        weeks_parsed = 1
        while weeks_parsed < max_weeks_to_parse:
            try:
                if go_to_next_week(driver):
                    time.sleep(1)  # Ждем загрузки
                    week_schedule = parse_current_week(driver)
                    if week_schedule:
                        all_weeks_schedule.append(week_schedule)
                        logging.info(f"Неделя {weeks_parsed + 1}: {len(week_schedule)} занятий")
                        weeks_parsed += 1
                    else:
                        # Если неделя пустая, возможно, это конец расписания
                        logging.info(f"Неделя {weeks_parsed + 1} пустая, прекращаю парсинг")
                        break
                else:
                    # Не удалось перейти на следующую неделю
                    logging.info("Не удалось перейти на следующую неделю, прекращаю парсинг")
                    break
            except Exception as e:
                logging.error(f"Ошибка при парсинге недели {weeks_parsed + 1}: {e}")
                break
        
        # Возвращаем результат
        result = {
            'success': True,
            'group_name': group_name,
            'weeks': all_weeks_schedule,
            'parsed_at': datetime.now().isoformat(),
            'total_weeks': len(all_weeks_schedule)
        }
        
        logging.info(f"=== УСПЕШНО завершен парсинг: {len(all_weeks_schedule)} недель для {group_name} ===")
        return result

    except Exception as e:
        logging.error(f"=== КРИТИЧЕСКАЯ ошибка парсинга: {e} ===", exc_info=True)
        return {"success": False, "error": str(e), "weeks": []}
        
    finally:
        if driver:
            try:
                driver.quit()
                logging.info("Драйвер закрыт")
            except:
                logging.warning("Не удалось закрыть драйвер")
                pass


def parse_current_week(driver):
    """Парсит текущую активную неделю"""
    try:
        # Ищем активную таблицу
        schedule_table = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.carousel-item.active table.table-no-transform"))
        )
        return parse_schedule_table(schedule_table)
    except TimeoutException:
        logging.warning("Таблица текущей недели не найдена")
        return []
    except Exception as e:
        logging.error(f"Ошибка при поиске таблицы текущей недели: {e}")
        return []


def go_to_next_week(driver):
    """Переходит к следующей неделе, возвращает True если успешно"""
    try:
        # Ищем кнопку "вперед" (стрелка вправо)
        next_button = driver.find_element(By.CSS_SELECTOR, "button.arrow-button.right[data-bs-slide='next']")
        
        # Проверяем, активна ли кнопка
        if next_button.is_enabled():
            driver.execute_script("arguments[0].click();", next_button)
            return True
        else:
            logging.info("Кнопка следующей недели неактивна")
            return False
    except NoSuchElementException:
        logging.info("Кнопка следующей недели не найдена")
        return False
    except Exception as e:
        logging.error(f"Ошибка при переходе на следующую неделю: {e}")
        return False


def parse_schedule_table(schedule_table):
    """Парсит данные из таблицы расписания"""
    lessons = []
    try:
        rows = schedule_table.find_elements(By.CSS_SELECTOR, "tbody tr")
        current_date = None
        
        for row in rows:
            lesson_data = {}
            
            # Пытаемся найти дату
            try:
                date_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Дата']")
                date_text = date_cell.text.strip()
                if date_text:
                    # Если у ячейки есть rowspan или текущая дата None, это новая дата
                    if date_cell.get_attribute("rowspan") or not current_date:
                        current_date = date_text
                    lesson_data['Дата'] = current_date
            except NoSuchElementException:
                if current_date:
                    lesson_data['Дата'] = current_date
            
            # Пытаемся найти время
            try:
                time_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Время']")
                time_text = time_cell.text.strip()
                if time_text:
                    lesson_data['Время'] = time_text
                else:
                    continue  # Пропускаем строки без времени
            except NoSuchElementException:
                continue  # Пропускаем строки без времени
            
            # Получаем дисциплину
            try:
                discipline_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Дисциплина']")
                discipline_text = discipline_cell.text.strip()
                if discipline_text:
                    # Берем первую строку (основное название)
                    lesson_data['Дисциплина'] = discipline_text.split('\n')[0]
                    
                    # Проверяем наличие ссылки на вебинар
                    try:
                        webinar_link = discipline_cell.find_element(By.TAG_NAME, "a")
                        lesson_data['Ссылка на вебинар'] = webinar_link.get_attribute("href")
                    except NoSuchElementException:
                        pass
            except NoSuchElementException:
                pass
            
            # Получаем аудиторию
            try:
                classroom_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Аудитория']")
                classroom_text = classroom_cell.text.strip()
                if classroom_text:
                    lesson_data['Аудитория'] = classroom_text
            except NoSuchElementException:
                pass
            
            # Получаем преподавателя
            try:
                teacher_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Преподаватель']")
                teacher_text = teacher_cell.text.strip()
                if teacher_text:
                    lesson_data['Преподаватель'] = teacher_text
            except NoSuchElementException:
                pass
            
            # Получаем тип занятия
            try:
                type_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Занятие']")
                type_text = type_cell.text.strip()
                if type_text:
                    lesson_data['Тип занятия'] = type_text
            except NoSuchElementException:
                pass
            
            if lesson_data:
                lessons.append(lesson_data)
    
    except Exception as e:
        logging.error(f"Ошибка парсинга таблицы: {e}")
    
    return lessons