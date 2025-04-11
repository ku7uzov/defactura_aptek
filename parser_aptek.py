import csv
import requests
from bs4 import BeautifulSoup

BASE_URL = "https://tabletka.by/pharmacies/"
HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

def parse_pharmacy_row(row):
    try:
        name = row.select_one('.pharm-name a').text.strip()
    except:
        name = ""

    try:
        address = row.select_one('.address .tooltip-info-header .text-wrap span').text.strip()
    except:
        address = ""

    try:
        work_times = [li.text.strip() for li in row.select('.address .tooltip-info-body .tooltip-info-list li')]
        work_times = "; ".join(work_times)
    except:
        work_times = ""

    try:
        phone = row.select_one('.phone a').text.strip()
    except:
        phone = ""

    try:
        lat = row.select_one('.tooltip-info-link a')['data-lat']
        lon = row.select_one('.tooltip-info-link a')['data-lon']
    except:
        lat = lon = ""

    return {
        'Название': name,
        'Адрес': address,
        'Время работы': work_times,
        'Телефон': phone,
        'Широта': lat,
        'Долгота': lon
    }

def scrape_pharmacies():
    pharmacies = []
    for page in range(1, 212):  # 43 страницы
        print(f"Парсим страницу {page}...")
        response = requests.get(f"{BASE_URL}?&page={page}&sort=name&sorttype=asc", headers=HEADERS)
        soup = BeautifulSoup(response.text, 'html.parser')
        rows = soup.select('tr.tr-border')
        for row in rows:
            pharmacy = parse_pharmacy_row(row)
            pharmacies.append(pharmacy)
    return pharmacies

def save_to_csv(pharmacies, filename="all_pharmacies.csv"):
    keys = pharmacies[0].keys()
    with open(filename, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(pharmacies)

if __name__ == "__main__":
    data = scrape_pharmacies()
    save_to_csv(data)
    print("✅ Данные сохранены в dashboard.csv")
