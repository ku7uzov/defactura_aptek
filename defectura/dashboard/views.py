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
from collections import defaultdict

def dashboard(request):
    # Получаем все записи, отсортированные по времени
    history = DrugSearchHistory.objects.order_by("drug_id",'drug_name', 'searched_at')

    # Группируем записи по названию препарата
    drug_history = defaultdict(list)
    for record in history:
        drug_history[(record.drug_id, record.drug_name)].append(record)

    # Храним динамику изменений по каждому препарату
    all_changes = []
    last_change_by_drug = []

    for (drug_id, drug_name), records in drug_history.items():
        for i in range(1, len(records)):
            prev = records[i - 1]
            curr = records[i]

            diff = curr.pharmacies_without - prev.pharmacies_without
            if diff != 0:
                change = {
                    'drug_name': drug_name,
                    'pharmacies_without_diff': diff,
                    'searched_at': curr.searched_at,
                    'previous_searched_at': prev.searched_at
                }
                all_changes.append(change)

        # Добавим последнюю разницу отдельно, если нужно отобразить на графике
        if len(records) > 1:
            last = records[-1]
            prev = records[-2]
            diff = last.pharmacies_without - prev.pharmacies_without
            last_change_by_drug.append({
                'drug_id': drug_id,
                'drug_name': drug_name,
                'pharmacies_without_diff': diff,
                'searched_at': last.searched_at,
                'previous_searched_at': prev.searched_at
            })

    # Подготовка данных для графика (только последние изменения)
    labels = [change['drug_name'] for change in last_change_by_drug]
    data = [change['pharmacies_without_diff'] for change in last_change_by_drug]

    return render(request, "dashboard/dashboard.html", {
        "history": history,
        "drug_changes": last_change_by_drug,   # Для графика и последнего отображения
        "chart_labels": labels,
        "chart_data": data,
        "all_changes": all_changes             # Вся динамика изменений по всем препаратам
    })

def drug_chart(request, drug_id):
    # Фильтруем изменения только для нужного препарата
    history = DrugSearchHistory.objects.filter(drug_id=drug_id).order_by('searched_at')

    drug_name = history[0].drug_name  # Берём название препарата из первой записи

    # Готовим список изменений
    labels = []
    data = []

    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        diff = curr.pharmacies_without - prev.pharmacies_without
        labels.append(curr.searched_at.strftime('%d.%m %H:%M'))
        data.append(diff)

    return render(request, 'dashboard/drug_chart.html', {
        'drug_name': drug_name,
        'labels': labels,
        'data': data,
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
            without_count= 4283 - pharmacy_info  # Или сколько всего аптек у тебя
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

