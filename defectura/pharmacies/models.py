from django.db import models

class Pharmacy(models.Model):
    name = models.CharField("Название аптеки", max_length=255)
    address = models.CharField("Адрес", max_length=500)
    network = models.CharField("Сеть", max_length=255, blank=True, null=True)
    phones = models.TextField("Телефоны", blank=True, null=True)



    def __str__(self):
        return f"{self.name} ({self.address})"
