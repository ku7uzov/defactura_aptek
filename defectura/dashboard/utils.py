import requests
from bs4 import BeautifulSoup
import re





def parse_tablets(name, region):
    url = f"https://tabletka.by/search/?request={name}&region={region}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')


    warnings = [notice.text.strip() for notice in soup.select("div.notice.notice--warning")]
    dangers = [notice.text.strip() for notice in soup.select("div.notice.notice--danger")]

    # Фильтруем предупреждения, удаляя "По заданному фильтру не найдено"
    warnings = [w for w in warnings if w != "Данных по заданному фильтру не найдено."]

    # Проверяем, есть ли сообщение о ненайденных совпадениях
    no_results_message = None
    suggestions = []
    no_results = soup.select_one("h2.title-h2.page-title")
    if no_results and "По вашему запросу совпадений не найдено" in no_results.text:
        no_results_message = "По вашему запросу совпадений не найдено. Возможно, вы искали:"
        suggestions = [s.text.strip() for s in soup.select("div.link-block-wrap a .bttn.link-block")]

    # Извлекаем данные о таблетках
    tablets = []
    for row in soup.select("tbody.tbody-base-tbl tr.tr-border"):
        item_id_tag = row.select_one("td.btn .heart-icon")
        item_id = item_id_tag["itemid"] if item_id_tag else None  # Извлекаем itemID


        name_tag = row.select_one("td.name .tooltip-info-header a")
        form_tag = row.select_one("td.form .tooltip-info-header a")
        produce = row.select_one("td.produce .tooltip-info-header a")
        price_tag = row.select_one("td.price .price-value")
        mnn_tag = row.select_one("td.name .capture a")  # Парсим ссылку на МНН
        recipe_tag = row.select_one("td.form .capture")  # Добавим для получения информации о рецепте

        # Извлекаем данные о количестве аптек и ссылке
        pharmacy_info_tag = row.select_one("td.price .capture a")
        if pharmacy_info_tag:
            # Ищем первое число в тексте, например: "в 168 аптеках"
            match = re.search(r"\d+", pharmacy_info_tag.text)
            pharmacy_info = int(match.group()) if match else 0
        else:
            pharmacy_info = None

        # pharmacy_info = pharmacy_info_tag.text.strip() if pharmacy_info_tag else None
        pharmacy_link = pharmacy_info_tag['href'] if pharmacy_info_tag else None

        if name_tag and form_tag and price_tag and produce:
            item_id_tag = row.select_one("td.btn .heart-icon")
            item_id = item_id_tag["itemid"] if item_id_tag else None  # Извлекаем itemID

            name = name_tag.text.strip()
            form = form_tag.text.strip()
            produce = produce.text.strip()
            price_text = price_tag.text.strip()
            form_link = form_tag["href"].replace("®", "&reg")  # Берем ссылку на форму
            mnn_link = ""
            mnn_name = ""
            try:
                mnn_link = mnn_tag['href'].replace("®", "&reg")
                mnn_name = mnn_tag.text.strip() if mnn_tag else None
            except:
                pass

            recipe = recipe_tag.text.strip() if recipe_tag else "Не указано"

            # Извлекаем диапазон цен (например, 17.56 ... 18.42)
            price_match = re.search(r"([\d.]+)\s*\.\.\.\s*([\d.]+)\s*р\.", price_text)

            if price_match:
                price_from = float(price_match.group(1))
                price_to = float(price_match.group(2))
            else:
                # Если диапазона нет, пытаемся найти одну цену
                single_price_match = re.search(r"([\d.]+)\s*р\.", price_text)
                price_from = float(single_price_match.group(1)) if single_price_match else None
                price_to = None  # Указываем, что второй цены нет

            tablets.append({
                "item_id" :item_id,
                "name": name,
                "form": form,
                "produce": produce,
                "form_link": form_link,
                "price_from": price_from,
                "price_to": price_to,
                "mnn_link": mnn_link,
                "mnn_name": mnn_name,
                "recipe": recipe,
                "pharmacy_diff" : 4283 - int(pharmacy_info),
                "pharmacy_info": pharmacy_info,  # Добавляем количество аптек
                "pharmacy_link": pharmacy_link   # Добавляем ссылку на результаты
            })


    # Сортируем список по минимальной цене
    tablets.sort(key=lambda x: x["price_from"] if x["price_from"] is not None else float('inf'))


    return {
        "tablets": tablets,
        "warnings": warnings,
        "dangers": dangers,
        "no_results_message": no_results_message,
        "suggestions": suggestions
    }
