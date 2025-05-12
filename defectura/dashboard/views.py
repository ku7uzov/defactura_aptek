


import requests
from bs4 import BeautifulSoup

from .utils import parse_tablets,parser


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


from .models import DrugSearchHistory


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
from collections import defaultdict

def drug_chart(request, drug_id):
    history = DrugSearchHistory.objects.filter(drug_id=drug_id).order_by('searched_at')

    if not history:
        return HttpResponse("Нет данных для выбранного препарата.")

    drug_name = history[0].drug_name

    # --- Подготовка графика изменений по времени ---
    labels = []
    data = []
    for i in range(1, len(history)):
        prev = history[i - 1]
        curr = history[i]
        diff = curr.pharmacies_without - prev.pharmacies_without
        labels.append(curr.searched_at.strftime('%d.%m %H:%M'))
        data.append(diff)

    # --- Группировка по дате (берем последнюю запись на день) ---
    daily_stats = {}
    for entry in history:
        date = entry.searched_at.date()
        daily_stats[date] = entry  # перезапись = берём последнюю запись на день

    # --- Подготовка таблицы ---
    table_data = []
    sorted_dates = sorted(daily_stats.keys())
    for i, date in enumerate(sorted_dates):
        entry = daily_stats[date]
        row = {
            'date': date.strftime('%d.%m.%Y'),
            'with': entry.pharmacies_with,
            'without': entry.pharmacies_without,
            'diff_with': None,
            'diff_without': None,
        }

        if i > 0:
            prev_entry = daily_stats[sorted_dates[i - 1]]
            row['diff_with'] = entry.pharmacies_with - prev_entry.pharmacies_with
            row['diff_without'] = entry.pharmacies_without - prev_entry.pharmacies_without

        table_data.append(row)
    history = DrugSearchHistory.objects.filter(drug_id=drug_id).order_by('searched_at')

    if not history:
        return HttpResponse("Нет данных для выбранного препарата.")

    drug_name = history[0].drug_name

    # --- Группируем по дате (последняя запись на день) ---
    daily_stats = {}
    for entry in history:
        date = entry.searched_at.date()
        daily_stats[date] = entry  # последняя запись на день

    # Сортируем даты
    sorted_dates = sorted(daily_stats.keys())

    # Формируем данные по датам
    dates = [d.strftime('%d.%m.%Y') for d in sorted_dates]
    with_data = []
    without_data = []
    dynamics = []

    for i, date in enumerate(sorted_dates):
        entry = daily_stats[date]
        with_data.append(entry.pharmacies_with)
        without_data.append(entry.pharmacies_without)

        if i == 0:
            dynamics.append(None)
        else:
            diff = entry.pharmacies_with - daily_stats[sorted_dates[i - 1]].pharmacies_with
            dynamics.append(diff)

    return render(request, 'dashboard/drug_chart.html', {
        'drug_name': drug_name,
        'labels': labels,
        'data': data,
        'table_data': table_data,
        # 'drug_name': drug_name,
        'dates': dates,
        'with_data': with_data,
        'without_data': without_data,
        'dynamics': dynamics,
    })

import subprocess
from django.http import FileResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

@csrf_exempt
@require_POST
def run_parser_and_download(request, item_id):
    # Запуск парсера с item_id
    try:
        name = request.POST.get('name')
        form = request.POST.get('form')

        region_url = f"https://tabletka.by/result/?ls={item_id}&region=0"
        response = requests.get(region_url, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(response.content, "html.parser")
        price_cnt_tag = soup.find("span", class_="price-cnt")
        pharmacy_info = int(price_cnt_tag.text.strip()) if price_cnt_tag else 0

        # Шаг 3: Сохранение в историю
        save_search_to_db(
            drug_id=item_id,
            drug_name=name,
            drug_form=form,
            with_count=pharmacy_info,
            without_count= 4283 - pharmacy_info  # Или сколько всего аптек у тебя
        )

        print('subprocess start')
        # Генерация уникального имени файла для каждого пользователя
        # Генерация уникального имени файла для каждого пользователя
        filename = f"pharmacies_without_drug.xlsx"  # Изменено на CSV


        parser(item_id)



        print('process end')

        # Загружаем аптеки
        pharmacies_df = pd.read_excel(filename)
        pharmacies = [
            {
                'name': row['Название аптеки'],
                'address': row['Адрес'],
                'phone': row['Телефон']
            }
            for _, row in pharmacies_df.iterrows()
        ]

        # Загружаем фармацевтов
        pharmacists = []
        with open('pharmacevty_csv.csv', 'r', encoding='utf-8') as f:
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

        # Сопоставляем
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

        # Создаём CSV

        # Путь к файлу после генерации
        if os.path.exists(filename):
            # Отправляем файл для скачивания
            output_df = pd.DataFrame(result)
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename=sorted_file.csv'
            output_df.to_csv(response, index=False, encoding='utf-8', sep=';')

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
        "no_results_msessage": None,
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



def sorted_file(request):
    return render(request, "dashboard/sorted_file.html", )



def history(request):
    # Получаем все записи, отсортированные по времени
    history = DrugSearchHistory.objects.order_by('-searched_at')  # Последние запросы первыми

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

    return render(request, "dashboard/history.html", {
        "history": history,
        "drug_changes": last_change_by_drug,  # Для графика и последнего отображения
        "chart_labels": labels,
        "chart_data": data,
        "all_changes": all_changes  # Вся динамика изменений по всем препаратам
    })


from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
import csv
import pandas as pd
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.files.storage import default_storage
from django.http import HttpResponse

@csrf_exempt
@require_POST
def sort_file(request):
    uploaded_file = request.FILES['file']
    file_path = default_storage.save('temp_pharmacy.xlsx', uploaded_file)

    # Загружаем аптеки
    pharmacies_df = pd.read_excel(file_path)
    pharmacies = [
        {
            'name': row['Название аптеки'],
            'address': row['Адрес'],
            'phone': row['Телефон']
        }
        for _, row in pharmacies_df.iterrows()
    ]

    # Загружаем фармацевтов
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

    # Сопоставляем
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

    # Создаём CSV
    output_df = pd.DataFrame(result)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename=sorted_file.csv'
    output_df.to_csv(response, index=False, encoding='utf-8', sep=';')

    return response



import os
import re
from django.core.files.storage import FileSystemStorage
from io import BytesIO


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




def search_table(request):
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

    return render(request, "dashboard/search.html", {
        "history": history,
        "drug_changes": last_change_by_drug,   # Для графика и последнего отображения
        "chart_labels": labels,
        "chart_data": data,
        "all_changes": all_changes             # Вся динамика изменений по всем препаратам
    })



def dynamic(request):
    # Получаем все записи, отсортированные по времени
    history = DrugSearchHistory.objects.order_by("drug_id", 'drug_name', 'searched_at')

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

    return render(request, "dashboard/dynamic.html", {
        "history": history,
        "drug_changes": last_change_by_drug,  # Для графика и последнего отображения
        "chart_labels": labels,
        "chart_data": data,
        "all_changes": all_changes  # Вся динамика изменений по всем препаратам
    })


import pandas as pd
import csv
import io
from django.http import HttpResponse
from django.shortcuts import render
from .forms import FileUploadForm

def upload_files(request):
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            pharmacies_file = request.FILES['pharmacies_file']
            pharmacists_file = request.FILES['pharmacists_file']

            pharmacies_df = pd.read_excel(pharmacies_file)
            pharmacies = []
            for _, row in pharmacies_df.iterrows():
                pharmacies.append({
                    'name': row['Название аптеки'],
                    'address': row['Адрес'],
                    'phone': row['Телефон']
                })

            pharmacists = []
            stream = io.StringIO(pharmacists_file.read().decode('utf-8'))
            reader = csv.reader(stream, delimiter=';')
            next(reader)
            for row in reader:
                pharmacists.append({
                    'name': row[0],
                    'phone': row[1],
                    'workplace': row[2],
                    'location': row[3],
                    'pharmacy_name': row[4]
                })

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

            for pharmacy in pharmacies:
                if pharmacy['name'] not in matched_pharmacies:
                    result.append({
                        'Аптека': pharmacy['name'],
                        'Местоположение аптеки': pharmacy['address'],
                        'Номер телефона аптеки': pharmacy['phone'],
                        'ФИО': '',
                        'Телефон фармацевта': '',
                    })

            output = io.BytesIO()
            output_df = pd.DataFrame(result)
            output_df.to_excel(output, index=False)
            output.seek(0)

            response = HttpResponse(
                output,
                content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            )
            response['Content-Disposition'] = 'attachment; filename=pharmacies_with_pharmacists.xlsx'
            return response
    else:
        form = FileUploadForm()
    return render(request, 'upload_form.html', {'form': form})
