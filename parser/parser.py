
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


def parse_vvsu_timetable(group_name):
    """
    Args:
        group_name (str): Название группы

    Returns:
        list: Список словарей с информацией о занятиях
    """

    # Настройка Firefox драйвера
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--width=1280")
    options.add_argument("--height=720")
    options.set_preference("permissions.default.image", 2)  # Блокировка изображений

    # Инициализация драйвера
    driver = webdriver.Firefox(options=options)

    try:
        driver.get("https://www.vvsu.ru/timetable/")

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
        time.sleep(1)

        # Ждем появления списка групп и кликаем на нужную
        time.sleep(1)
        try:
            group_button = wait.until(
                EC.element_to_be_clickable((By.XPATH, f"//button[contains(., '{group_name}')]"))
            )
            driver.execute_script("arguments[0].click();", group_button)
        except:
            print("Группа не найдена в списке. Проверь название группы.")
            return None, None

        # Ждем загрузки расписания (2 секунды)
        time.sleep(2)

        # Возвращаем драйвер и wait для дальнейшего использования
        return driver, wait

    except Exception as e:
        print(f"Произошла ошибка при загрузке: {e}")
        return None, None


def get_current_week_schedule(driver, wait):
    """Получает расписание текущей недели"""
    try:
        # Находим активное расписание (текущая неделя)
        schedule_table = wait.until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div.carousel-item.active table.table-no-transform"))
        )

        return parse_schedule_table(schedule_table)
    except Exception as e:
        print(f"Ошибка при получении расписания: {e}")
        return []


def parse_schedule_table(schedule_table):
    """Парсит данные из таблицы расписания"""
    lessons = []
    rows = schedule_table.find_elements(By.CSS_SELECTOR, "tbody tr")

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

    return lessons


def go_to_previous_week(driver, wait):
    """Переходит к расписанию на предыдущую неделю"""
    try:
        # Находим кнопку "Назад"
        prev_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.arrow-button.left[data-bs-slide='prev']"))
        )
        driver.execute_script("arguments[0].click();", prev_button)

        # Ждем загрузки нового расписания
        time.sleep(2)

        # Получаем расписание предыдущей недели
        return get_current_week_schedule(driver, wait)

    except Exception as e:
        print(f"Ошибка при переходе на предыдущую неделю: {e}")
        return []


def go_to_next_week(driver, wait):
    """Переходит к расписанию на следующую неделю"""
    try:
        # Находим кнопку "Вперед"
        next_button = wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.arrow-button.right[data-bs-slide='next']"))
        )
        driver.execute_script("arguments[0].click();", next_button)

        # Ждем загрузки нового расписания
        time.sleep(2)

        # Получаем расписание следующей недели
        return get_current_week_schedule(driver, wait)

    except Exception as e:
        print(f"Ошибка при переходе на следующую неделю: {e}")
        return []


def print_schedule(lessons, week_description="Текущая неделя"):
    """Выводит расписание в консоль в новом формате"""
    if not lessons:
        print(f"{week_description}: расписание не найдено")
        return

    current_date = None
    for lesson in lessons:
        # Обрабатываем дату - убираем переносы строки
        lesson_date = lesson.get('Дата', '').replace('\n', ' ') if lesson.get('Дата') else None

        # Выводим заголовок даты
        if lesson_date != current_date:
            current_date = lesson_date
            if current_date:
                print(f"{current_date}")
                print("-" * 55)

        # Выводим данные пары
        if lesson.get('Время'):
            print(f"{lesson.get('Время', '')}")
            print(lesson.get('Дисциплина', ''))

            # Если есть вебинар, выводим ссылку
            webinar_link = lesson.get('Ссылка на вебинар')
            if webinar_link:
                print(webinar_link)
                print(lesson.get('Аудитория', ''))
            else:
                print(lesson.get('Аудитория', ''))

            print(lesson.get('Преподаватель', ''))
            print(lesson.get('Тип занятия', ''))
            print("-" * 55)

# Пример использования
if __name__ == "__main__":
    # Укажите нужную группу
    # group = input("Введите название группы: ")
    group = "БПИ-24-2"

    print(f"Загружаем расписание для группы {group}...")
    driver, wait = parse_vvsu_timetable(group)

    if driver and wait:
        try:
            # Текущая неделя
            current_schedule = get_current_week_schedule(driver, wait)
            print_schedule(current_schedule, "Текущая неделя")

            # Предыдущая неделя
            prev_schedule = go_to_previous_week(driver, wait)
            print_schedule(prev_schedule, "Предыдущая неделя")

            # Следующая неделя
            next_schedule = go_to_next_week(driver, wait)
            print_schedule(next_schedule, "Следующая неделя")

        finally:
            # Закрываем браузер
            driver.quit()
    else:
        print("Не удалось загрузить страницу с расписанием")
