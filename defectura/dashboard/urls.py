from django.urls import path, re_path
from .views import dashboard, search_tablets, run_parser_and_download, process_phone_file, drug_chart, sorted_file, search_table, history, dynamic, upload_files, sort_file

urlpatterns = [
    path('', search_table, name='dashboard'),  # Главная страница Mini App
    path('search/', search_table, name='search_table'),  # Главная страница Mini App
    path('history/', history, name='history'),  # Главная страница Mini App
    path('dynamic/', dynamic, name='dynamic'),  # Главная страница Mini App
    path("search/tablets/", search_tablets, name="search_tablets"),
    path('download/<int:item_id>/', run_parser_and_download, name='run_parser_and_download'),
    path('sort-file/', sort_file, name='sort_file'),
    path('sorted-file/', sorted_file, name='sorted_file'),
    path('drug-chart/<str:drug_id>/', drug_chart, name='drug_chart'),
    path('upload/', upload_files, name='upload_files'),

]


