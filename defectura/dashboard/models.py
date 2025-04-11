from django.db import models

class Pharmacy(models.Model):
    name = models.CharField("Название аптеки", max_length=255)
    address = models.CharField("Адрес", max_length=500)
    network = models.CharField("Сеть", max_length=255, blank=True, null=True)
    phones = models.TextField("Телефоны", blank=True, null=True)


    def __str__(self):
        return f"{self.name} ({self.address})"


class DrugSearchHistory(models.Model):
    drug_id = models.CharField(max_length=255)
    drug_name = models.CharField(max_length=255)
    drug_form = models.CharField(max_length=255)
    pharmacies_with = models.PositiveIntegerField()
    pharmacies_without = models.PositiveIntegerField()
    searched_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.drug_name} ({self.searched_at.strftime('%Y-%m-%d %H:%M')})"