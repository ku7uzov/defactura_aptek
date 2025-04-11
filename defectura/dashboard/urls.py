from django.urls import path, re_path
from .views import dashboard, search_tablets, run_parser_and_download, process_phone_file

urlpatterns = [
    path('', dashboard, name='dashboard'),  # Главная страница Mini App
    path("search/tablets/", search_tablets, name="search_tablets"),
    path('download/<int:item_id>/', run_parser_and_download, name='run_parser_and_download'),
    path('sort-file/', process_phone_file, name='sort_file'),

]


