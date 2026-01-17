"""
Selenium-скрипт для парсинга расписания с сайта vvsu.ru.
Автоматизирует браузер для получения данных о занятиях.

"""
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.firefox.options import Options
import logging

logger = logging.getLogger(__name__)


def parse_vvsu_timetable(group_name):
    """
    Args:
        group_name (str): Название группы

    Returns:
        list: Список словарей с информацией о занятиях
    """
    logger.info(f"Парсинг расписания для группы: {group_name}")

    # Настройка Firefox драйвера
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--width=1280")
    options.add_argument("--height=720")
    options.set_preference("permissions.default.image", 2)  # Блокировка изображений

    # Инициализация драйвера
    try:
        driver = webdriver.Firefox(options=options)
    except Exception as e:
        logger.error(f"Ошибка инициалиазции драйвера: {e}")
        return None, None

    try:
        driver.get("https://www.vvsu.ru/timetable/")
        logger.info(f"Открыта страница расписания")

        # Ждем загрузки страницы
        wait = WebDriverWait(driver, 15)

        # Прокручиваем страницу и используем JavaScript для клика
        driver.execute_script("window.scrollTo(0, 300);")
        time.sleep(1)

        # Находим поле для ввода группы
        group_input = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "input#gr"))
        )
        driver.execute_script("arguments[0].click();", group_input)
        time.sleep(1)

        # Вводим название группы
        group_input.send_keys(group_name)
        logger.info(f"Введено название группы: {group_name}")
        time.sleep(1)

        # Ждем появления списка групп и кликаем на нужную
        time.sleep(1)
        try:
            group_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{group_name}')]"))
            )
            driver.execute_script("arguments[0].click();", group_button)
            logger.info(f"Выбрана группа из списка: {group_name}")
        except Exception as e:
            logger.error(f"Группа не найдена в списке: {group_name}. Ошибка: {e}")
            print("Группа не найдена в списке. Проверь название группы.")
            driver.quit()
            return None, None

        # Ждем загрузки расписания (2 секунды)
        time.sleep(2)
        logger.info(f"Расписание для группы {group_name} загружено успешно")

        # Возвращаем драйвер и wait для дальнейшего использования
        return driver, wait

    except Exception as e:
        logger.error(f"Произошла ошибка при загрузке: {e}", exc_info=True)
        print(f"Произошла ошибка при загрузке: {e}")
        try:
            driver.quit()
        except:
            pass
        return None, None

def parse_schedule_table(schedule_table):
    """Парсит данные из таблицы расписания"""
    lessons = []
    rows = schedule_table.find_elements(By.CSS_SELECTOR, "tbody tr")
    logger.info(f"Найдено строк в таблице: {len(rows)}")

    current_date = None

    for row in rows:
        lesson_data = {}

        # Проверяем, есть ли ячейка с датой (rowspan)
        try:
            date_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Дата']")
            if date_cell.get_attribute("rowspan"):
                current_date = date_cell.text
                lesson_data['Дата'] = current_date
        except NoSuchElementException:
            # Если даты нет в текущей строке, используем предыдущую
            if current_date:
                lesson_data['Дата'] = current_date

        # Парсим остальные данные
        try:
            time_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Время']")
            lesson_data['Время'] = time_cell.text
        except NoSuchElementException:
            continue  # Пропускаем строки без времени (это могут быть разделители)

        try:
            discipline_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Дисциплина']")
            lesson_data['Дисциплина'] = discipline_cell.text.split('\n')[0]  # Основное название

            # Проверяем наличие ссылки на вебинар
            try:
                webinar_link = discipline_cell.find_element(By.TAG_NAME, "a")
                lesson_data['Ссылка на вебинар'] = webinar_link.get_attribute("href")
            except NoSuchElementException:
                lesson_data['Ссылка на вебинар'] = None
        except NoSuchElementException:
            pass

        try:
            type_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Занятие']")
            lesson_data['Тип занятия'] = type_cell.text
        except NoSuchElementException:
            pass

        try:
            classroom_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Аудитория']")
            lesson_data['Аудитория'] = classroom_cell.text
        except NoSuchElementException:
            pass

        try:
            teacher_cell = row.find_element(By.CSS_SELECTOR, "td[data-th='Преподаватель']")
            lesson_data['Преподаватель'] = teacher_cell.text
        except NoSuchElementException:
            pass

        # Добавляем урок в список, если есть основные данные
        if lesson_data:
            lessons.append(lesson_data)

    logger.info(f"Спарсено {len(lessons)} занятий")
    return lessons

def get_current_week_schedule(driver, wait):
    """Получает расписание текущей недели"""
    try:
        # Находим активное расписание (текущая неделя)
        logger.info(f"Получение расписания текущей недели")
        schedule_table = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.carousel-item.active table.table-no-transform"))
        )
        schedule = parse_schedule_table(schedule_table)
        return schedule
    except Exception as e:
        logger.error(f"Ошибка при получении расписания: {e}")
        return []

def go_to_previous_week(driver, wait):
    """Переходит к расписанию на предыдущую неделю"""
    try:
        # Находим кнопку "Назад"
        logger.info(f"Переход к предыдущей неделе")
        prev_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.arrow-button.left[data-bs-slide='prev']"))
        )
        driver.execute_script("arguments[0].click();", prev_button)

        # Ждем загрузки нового расписания
        time.sleep(2)

        # Получаем расписание предыдущей недели
        return get_current_week_schedule(driver, wait)

    except Exception as e:
        logger.error(f"Ошибка при переходе на предыдущую неделю: {e}")
        return []


def go_to_next_week(driver, wait):
    """Переходит к расписанию на следующую неделю"""
    try:
        # Находим кнопку "Вперед"
        logger.info(f"Переход к следующей неделе")
        next_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.arrow-button.right[data-bs-slide='next']"))
        )
        driver.execute_script("arguments[0].click();", next_button)

        # Ждем загрузки нового расписания
        time.sleep(2)

        # Получаем расписание следующей недели
        return get_current_week_schedule(driver, wait)

    except Exception as e:
        logger.error(f"Ошибка при переходе на следующую неделю: {e}")
        return []
