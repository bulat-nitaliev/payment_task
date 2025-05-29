from django.db import models

class Organization(models.Model):
    inn = models.CharField(max_length=12, unique=True, verbose_name="ИНН организации")
    balance = models.DecimalField(max_digits=15, decimal_places=2, default=0, verbose_name="Баланс")

    def __str__(self):
        return self.inn

class Payment(models.Model):
    operation_id = models.UUIDField(unique=True, verbose_name="ID операции")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма платежа")
    payer_inn = models.CharField(max_length=12, verbose_name="ИНН плательщика")
    document_number = models.CharField(max_length=255, verbose_name="Номер документа")
    document_date = models.DateTimeField(verbose_name="Дата документа")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания записи")

    def __str__(self):
        return str(self.operation_id)

class BalanceLog(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, verbose_name="Организация")
    payment = models.ForeignKey(Payment, on_delete=models.CASCADE, verbose_name="Платеж")
    amount = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Сумма изменения")
    balance_after = models.DecimalField(max_digits=15, decimal_places=2, verbose_name="Баланс после операции")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата операции")

    def __str__(self):
        return f"{self.organization.inn} | {self.amount}"