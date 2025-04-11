from django.contrib import admin
from .models import Pharmacy, DrugSearchHistory
# Register your models here.\


@admin.register(Pharmacy)
class PharmacyAdmin(admin.ModelAdmin):
    list_display = ('name', 'address', 'network')
    search_fields = ('name', 'address', 'network')



@admin.register(DrugSearchHistory)
class DrugSearchHistoryAdmin(admin.ModelAdmin):
    list_display = ("drug_name", "searched_at", "pharmacies_with", "pharmacies_without")
    list_filter = ("drug_name",)
    ordering = ("-searched_at",)
