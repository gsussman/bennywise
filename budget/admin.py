from django.contrib import admin

# Register your models here.
from .models import Transaction, Account, PlaidItem, Spendable, Dailyresult

admin.site.register(Transaction)
admin.site.register(Account)
admin.site.register(PlaidItem)
admin.site.register(Spendable)
admin.site.register(Dailyresult)