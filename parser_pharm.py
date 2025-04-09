import time
import csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException


BASE_URL = "https://tabletka.by/result/?ls=9002"


def create_driver() -> webdriver.Chrome:
    options = Options()
    # options.add_argument("--headless")  # включи при необходимости
    options.add_argument("--disable-gpu")
    return webdriver.Chrome(options=options)


# Установить отображение 100 аптек на странице
def set_items_per_page(driver: webdriver.Chrome) -> None:
    try:
        try:
            bottom_notice = driver.find_element(By.CLASS_NAME, "bottom-notice-close")
            driver.execute_script("arguments[0].click();", bottom_notice)
            print("🔕 Баннер закрыт")
            time.sleep(1)
        except NoSuchElementException:
            pass

        select_buttons = driver.find_elements(By.ID, "paging")
        if not select_buttons:
            print("⚠️ Элемент #paging не найден — возможно, показ всех аптек по умолчанию.")
            return

        select_button = select_buttons[0]
        driver.execute_script("arguments[0].scrollIntoView(true);", select_button)
        driver.execute_script("arguments[0].click();", select_button)

        option_100 = driver.find_element(By.ID, "tw3")
        driver.execute_script("arguments[0].click();", option_100)
        time.sleep(1)
    except Exception as e:
        print("❌ Ошибка при выборе количества аптек:", e)


# Сбор информации об аптеках на странице
from selenium.common.exceptions import StaleElementReferenceException


def get_pharmacy_info(driver: webdriver.Chrome) -> list[list[str]]:
    pharmacies = []
    rows = driver.find_elements(By.CSS_SELECTOR, "tr.tr-border")

    for index in range(len(rows)):
        try:
            # Получаем строку снова, чтобы избежать stale reference
            row = driver.find_elements(By.CSS_SELECTOR, "tr.tr-border")[index]

            name = row.find_element(By.CSS_SELECTOR, ".pharm-name a").text.strip()
            address = row.find_element(By.CSS_SELECTOR, ".address .text-wrap span").text.strip()
            phone = row.find_element(By.CSS_SELECTOR, ".phone .text-wrap a").text.strip()
            price = row.find_element(By.CSS_SELECTOR, ".price .price-value").text.strip()
            pharmacies.append([name, address, phone, price])
        except (NoSuchElementException, StaleElementReferenceException):
            continue

    return pharmacies


# Переход на следующую страницу
def click_next(driver: webdriver.Chrome) -> bool:
    try:
        next_btn = driver.find_element(By.CSS_SELECTOR, ".table-pagination-next a")
        if not next_btn.is_displayed():
            print("⚠️ Кнопка 'Вперёд' не видна. Страницы закончились.")
            return False

        driver.execute_script("arguments[0].scrollIntoView(true);", next_btn)
        driver.execute_script("window.scrollBy(0, 100);")
        driver.execute_script("arguments[0].click();", next_btn)
        return True
    except Exception as e:
        print("❌ Ошибка при переходе на следующую страницу:", e)
        return False


# Чтение всех аптек
def read_pharmacies(file_name: str) -> set[tuple[str, str]]:
    with open(file_name, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)
        return {(row[0].strip(), row[1].strip()) for row in reader if row}


# Чтение аптек, у которых есть препарат
# Чтение второго файла (аптеки с препаратом)
def read_pharmacies_with_drug(file_name):
    with open(file_name, newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # ⬅️ пропустить заголовок
        pharmacies = {(row[0].strip(), row[1].strip()) for row in reader if row}
    return pharmacies


# Основной алгоритм
def compare_pharmacies():
    # Чтение всех аптек
    all_pharmacies = read_pharmacies('all_pharmacies.csv')

    # Чтение аптек с препаратом
    pharmacies_with_drug = read_pharmacies_with_drug('pharmacies_with_drug.csv')

    # 🔍 Отладочная информация
    print(f"📄 Всего строк в all_pharmacies.csv (включая заголовок): {sum(1 for _ in open('all_pharmacies.csv', encoding='utf-8'))}")
    print(f"🏥 Уникальных аптек (по названию и адресу): {len(all_pharmacies)}")
    print(f"💊 Аптек, в которых есть препарат: {len(pharmacies_with_drug)}")

    # Находим аптеки, в которых нет препарата
    pharmacies_without_drug = all_pharmacies - pharmacies_with_drug

    print(f"❌ Всего аптек без препарата: {len(pharmacies_without_drug)}")

    # Чтение дополнительной информации о всех аптеках (из первого файла)
    pharmacies_info = {}
    with open('all_pharmacies.csv', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        next(reader, None)  # Пропустить заголовок
        for row in reader:
            name = row[0].strip()
            address = row[1].strip()
            work_time = row[2].strip()
            phone = row[3].strip()
            pharmacies_info[(name, address)] = {
                "work_time": work_time,
                "phone": phone,
            }

    # Записываем результат в новый файл
    with open('pharmacies_without_drug.csv', "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Название аптеки", "Адрес", "Телефон", "Время работы", "Цена"])

        for pharmacy in pharmacies_without_drug:
            if pharmacy in pharmacies_info:
                info = pharmacies_info[pharmacy]
                writer.writerow([pharmacy[0], pharmacy[1], info["phone"], info["work_time"], ""])

    print("💾 Аптеки, в которых нет препарата, сохранены в pharmacies_without_drug.csv")

# Главная функция
def main():
    driver = create_driver()

    print("🚀 Открываем страницу...")
    driver.get(BASE_URL)
    time.sleep(2)

    print("⚙️ Устанавливаем показ по 100...")
    set_items_per_page(driver)

    result = []
    page = 1

    while True:
        print(f"📄 Парсим страницу {page}...")
        result.extend(get_pharmacy_info(driver))
        if not click_next(driver):
            break
        time.sleep(1)
        page += 1

    print(f"✅ Собрано аптек: {len(result)}")

    with open("pharmacies_with_drug.csv", "w", newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow(["Название аптеки", "Адрес", "Телефон", "Цена"])
        writer.writerows(result)

    print("💾 Данные сохранены в pharmacies_with_drug.csv")
    driver.quit()

    compare_pharmacies()


if __name__ == "__main__":
    main()
