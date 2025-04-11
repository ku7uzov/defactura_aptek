import requests
from bs4 import BeautifulSoup
from django.http import HttpResponse
from django.shortcuts import render

from .models import DrugSearchHistory
from .utils import parse_tablets
from django.http import FileResponse
import time
import subprocess
import os


def save_search_to_db(drug_id,drug_name,drug_form, with_count, without_count):
    # from django.conf import settings
    # import os
    # import django
    #
    # # Установка переменных окружения Django
    # os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'your_project_name.settings')  # замените на имя вашего проекта
    # django.setup()


    DrugSearchHistory.objects.create(
        drug_id=drug_id,
        drug_name=drug_name,
        drug_form=drug_form,
        pharmacies_with=with_count,
        pharmacies_without=without_count
    )
from django.shortcuts import render
from .models import DrugSearchHistory

def dashboard(request):
    # Получаем все записи, отсортированные по времени
    history = DrugSearchHistory.objects.order_by('-searched_at')

    # Для каждого препарата находим последние две записи
    drug_changes = []
    seen_drugs = set()

    for record in history:
        if record.drug_name not in seen_drugs:
            seen_drugs.add(record.drug_name)
            # Находим последнюю запись для этого препарата
            latest_record = record
            # Находим предпоследнюю запись для этого препарата
            previous_record = DrugSearchHistory.objects.filter(drug_name=record.drug_name).order_by('-searched_at')[1] if DrugSearchHistory.objects.filter(drug_name=record.drug_name).count() > 1 else None

            if previous_record:
                # Вычисляем разницу по отсутствию препарата
                pharmacies_without_diff = latest_record.pharmacies_without - previous_record.pharmacies_without

                # Если разница по отсутствию препарата есть, добавляем в список изменений
                if pharmacies_without_diff != 0:
                    diff = {
                        'drug_name': latest_record.drug_name,
                        'pharmacies_without_diff': pharmacies_without_diff,
                        'searched_at': latest_record.searched_at,
                        'previous_searched_at': previous_record.searched_at
                    }
                    drug_changes.append(diff)

    # Готовим данные для графика
    labels = [change['drug_name'] for change in drug_changes]
    data = [change['pharmacies_without_diff'] for change in drug_changes]

    return render(request, "dashboard/dashboard.html", {
        "history": history,
        "drug_changes": drug_changes,
        "chart_labels": labels,
        "chart_data": data
    })

import os
import subprocess
from django.http import FileResponse
from django.shortcuts import render

def run_parser_and_download(request, item_id):
    # Запуск парсера с item_id
    try:

        name = request.GET.get('name')
        form = request.GET.get('form')

        region_url = f"https://tabletka.by/result/?ls={item_id}&region=0"
        response = requests.get(region_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        price_cnt_tag = soup.find("span", class_="price-cnt")
        pharmacy_info = int(price_cnt_tag.text.strip()) if price_cnt_tag else 0

        # name = f"Препарат {item_id}"
        # form = "таблетки"  # Пример, замени при необходимости

        # Шаг 3: Сохранение в историю
        save_search_to_db(
            drug_id=item_id,
            drug_name=name,
            drug_form=form,
            with_count=pharmacy_info,
            without_count=4283 - pharmacy_info  # Или сколько всего аптек у тебя
        )


        # Вызываем парсер с передачей item_id
        result = subprocess.run(
            ["python", "parser_pharm.py", str(item_id)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,  # Возвращает stdout и stderr как строки
            encoding = 'utf-8',  # Указываем кодировку


        )

        # Печать вывода для отладки
        # print("STDOUT:", result.stdout)
        # print("STDERR:", result.stderr)

        # Проверка на ошибки
        if result.returncode != 0:
            return render(request, "dashboard/error.html", {"message": f"Ошибка при выполнении парсера: {result.stderr}"})

        # Путь к файлу после генерации
        file_path = "pharmacies_without_drug.xlsx"

        if os.path.exists(file_path):
            # Отправляем файл для скачивания
            response = FileResponse(open(file_path, 'rb'), as_attachment=True, filename="pharmacies_without_drug.xlsx")
            return response
        else:
            return render(request, "dashboard/error.html", {"message": "Файл не найден."})

    except subprocess.CalledProcessError as e:
        return render(request, "dashboard/error.html", {"message": f"Ошибка при выполнении парсера: {e}"})
    except Exception as e:
        # Ловим любые другие ошибки
        return render(request, "dashboard/error.html", {"message": f"Непредвиденная ошибка: {str(e)}"})


def search_tablets(request):
    query = request.GET.get("query", "")  # Название лекарства
    region = request.GET.get("selected-region", "0")  # Регион по умолчанию (например, "125")

    result = parse_tablets(query, region) if query else {
        "tablets": [],
        "warnings": [],
        "dangers": [],
        "no_results_message": None,
        "suggestions": []
    }

    # Рендерим HTML и отправляем его как ответ
    html_content = render(request, "dashboard/tablets_results.html", {
        "tablets": result["tablets"],
        "warnings": result["warnings"],
        "dangers": result["dangers"],
        "no_results_message": result["no_results_message"],
        "suggestions": result["suggestions"],
    }).content

    return HttpResponse(html_content)


import os
import re
import pandas as pd
from django.core.files.storage import FileSystemStorage
from django.http import HttpResponse
from django.shortcuts import render
from io import BytesIO
from openpyxl import Workbook

def process_phone_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        fs = FileSystemStorage()
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)

        try:
            df = pd.read_excel(file_path, engine='openpyxl')

            processed_rows = []  # Для мобильных номеров
            city_phones = []  # Для городских номеров
            unprocessed_rows = []  # Для строк, которые не были изменены

            for _, row in df.iterrows():
                row_modified = False
                new_row = []
                new_city_phones = []  # Для сохранения городских номеров в текущей строке

                for cell in row:
                    if pd.isna(cell):
                        new_row.append(cell)
                        continue

                    text = str(cell)

                    original_text = text  # на случай если надо откат

                    # Если номер начинается с +375, пропускаем его
                    if text.startswith('+375'):
                        new_row.append(text)
                        continue

                    # Убираем + перед 375, только если перед ним нет уже 375
                    text, count_plus = re.subn(r'\+375', '375', text)

                    # Заменяем (033), (33) → 37533
                    text, count_33 = re.subn(r'\(?0?33\)?\D*(\d{6,7})', r'37533\1', text)

                    # Заменяем (029), (29) → 37529
                    text, count_29 = re.subn(r'\(?0?29\)?\D*(\d{6,7})', r'37529\1', text)

                    # Заменяем (044), (44) → 37544
                    text, count_44 = re.subn(r'\(?0?44\)?\D*(\d{6,7})', r'37544\1', text)

                    # Проверяем на городские номера (например, с префиксом 8 или другими условными признаками)
                    if re.match(r'^8\d{7}$', text):  # Пример для городских номеров
                        new_city_phones.append(text)

                    # Проверяем, были ли какие-то изменения
                    if count_plus > 0 or count_33 > 0 or count_29 > 0 or count_44 > 0:
                        row_modified = True

                    new_row.append(text)

                # Если был изменён хотя бы один номер, добавляем строку в processed_rows
                if row_modified:
                    processed_rows.append(new_row)

                # Если в строке есть городской номер, добавляем его в список city_phones
                if new_city_phones:
                    city_phones.append(new_city_phones)

                # Если строка не была изменена, добавляем её в unprocessed_rows
                if not row_modified:
                    unprocessed_rows.append(new_row)

            if not processed_rows and not unprocessed_rows:
                return render(request, "dashboard/error.html", {"message": "Нет подходящих строк для обработки."})

            # Создаём новый Excel файл с двумя листами
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                # Записываем данные на первый лист (мобильные номера)
                cleaned_df = pd.DataFrame(processed_rows, columns=df.columns)
                cleaned_df.to_excel(writer, sheet_name='Mobile Phones', index=False)

                # Если городские номера найдены, записываем их на второй лист
                if city_phones:
                    city_phones_df = pd.DataFrame(city_phones, columns=['City Phones'])
                    city_phones_df.to_excel(writer, sheet_name='City Phones', index=False)

                # Записываем строки без изменений на третий лист (Unprocessed)
                if unprocessed_rows:
                    unprocessed_df = pd.DataFrame(unprocessed_rows, columns=df.columns)
                    unprocessed_df.to_excel(writer, sheet_name='Unprocessed Phones', index=False)

            # Перемещаем указатель в начало файла
            output.seek(0)

            # Отправляем файл на скачивание
            response = HttpResponse(output.read(),
                                    content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            response['Content-Disposition'] = f'attachment; filename="processed_{uploaded_file.name}"'

            # Удаляем временные файлы
            os.remove(file_path)

            return response

        except Exception as e:
            return render(request, "dashboard/error.html", {"message": f"Ошибка при обработке файла: {str(e)}"})

    return render(request, "dashboard/error.html", {"message": "Неверный запрос."})

