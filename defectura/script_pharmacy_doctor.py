import csv
import pandas as pd

# Загружаем список аптек из Excel
pharmacies_df = pd.read_excel('defectura_3.xlsx')
pharmacies = []

for _, row in pharmacies_df.iterrows():
    pharmacies.append({
        'name': row['Название аптеки'],
        'address': row['Адрес'],
        'phone': row['Телефон']
    })

# Загружаем список фармацевтов из CSV
pharmacists = []
with open('pharmacevty.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f, delimiter=';')
    next(reader)
    for row in reader:
        pharmacists.append({
            'name': row[0],
            'phone': row[1],
            'workplace': row[2],
            'location': row[3],
            'pharmacy_name': row[4]
        })

# Сопоставление аптек и фармацевтов
result = []
matched_pharmacies = set()

for pharmacist in pharmacists:
    for pharmacy in pharmacies:
        if pharmacy['name'] == pharmacist['pharmacy_name']:
            result.append({
                'Аптека': pharmacy['name'],
                'Местоположение аптеки': pharmacy['address'],
                'Номер телефона аптеки': pharmacy['phone'],
                'ФИО': pharmacist['name'],
                'Телефон фармацевта': pharmacist['phone'],
            })
            matched_pharmacies.add(pharmacy['name'])

# Добавляем аптеки без фармацевтов
for pharmacy in pharmacies:
    if pharmacy['name'] not in matched_pharmacies:
        result.append({
            'Аптека': pharmacy['name'],
            'Местоположение аптеки': pharmacy['address'],
            'Номер телефона аптеки': pharmacy['phone'],
            'ФИО': '',
            'Телефон фармацевта': '',
        })

# Сохраняем результат в Excel
output_df = pd.DataFrame(result)
output_df.to_excel('pharmacies_with_pharmacists.xlsx', index=False)

print("Excel-файл с результатами создан: pharmacies_with_pharmacists.xlsx")
