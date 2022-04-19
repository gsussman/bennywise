# core/tasks.py
from celery import shared_task
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
import plaid
from plaid.api import plaid_api
from plaid.model.item_public_token_exchange_request import ItemPublicTokenExchangeRequest
from plaid.model.transactions_get_request_options import TransactionsGetRequestOptions
from plaid.model.transactions_get_request import TransactionsGetRequest
import datetime
from datetime import datetime, timedelta, date
from .models import PlaidItem, Account, Transaction, Category, Spendable, Dailyresult
import json
import sendgrid
import os
from sendgrid.helpers.mail import *
from django.core.mail import send_mail, EmailMessage
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def spendeval(x):
    if x >= .99 and x <= 1.01:
        shortresult = "on target"
        longresult = "You're spending exactly on budget! You should try to spend under budget, for the days you eventually spend more, but this is still great!"
    elif x >= .9 and x < .99:
        shortresult = "great job"
        longresult = "You're spending less than can! This is great, you are preparing for days where you overspend and are building your wealth!"
    elif x < .9:
        shortresult = "amazing"
        longresult = "You're doing an incredible job and spent over 10% less than your budget! This is how you save for a major rainy day and build serious wealth. Ka-Ching!"
    elif x >1.01 and x <= 1.1:
        shortresult = "a bit too high"
        longresult = "You're spending a bit higher than you should! You should try to spend under budget, and youre over. Focus on having fewer of these in the future."
    elif x > 1.1:
        shortresult = "way too high"
        longresult = "You're spending much higher than your budget! You should monitor your spending to make sure this number comes down in the future."
    return (shortresult, longresult)

configuration = plaid.Configuration(
    host=plaid.Environment.Development,
    api_key={
        'clientId': os.environ.get("PLAIDCLIENTID"),
        'secret': os.environ.get("PLAIDSECRET"),
    }
)

api_client = plaid.ApiClient(configuration)
client = plaid_api.PlaidApi(api_client)

@shared_task
def add():
    x=2
    y=10
    print ("success")
    return x + y

@shared_task
def update_transactions():
    User = get_user_model()
    users = User.objects.all()
    for us in users:
        accounttopull = Account.objects.filter(user=us)
        for a in accounttopull:
            accountlist = []
            accountitem = a.plaid_account_id
            accountlist.append(accountitem)
            plaiditem = PlaidItem.objects.get(account__plaid_account_id=accountitem)
            access_token = plaiditem.access_token
            timespan_weeks = 4 * 24  # Plaid only goes back 24 months
            start_date = '{:%Y-%m-%d}'.format(datetime.now() + timedelta(weeks=(-timespan_weeks)))
            end_date = '{:%Y-%m-%d}'.format(datetime.now())

            request = TransactionsGetRequest(
                access_token=access_token,
                start_date=date.fromisoformat(start_date),
                end_date=date.fromisoformat(end_date),
                options=TransactionsGetRequestOptions(
                    account_ids=accountlist
                )
            )
            response = client.transactions_get(request)
            transactions = response['transactions']
            while len(transactions) < response['total_transactions']:
                request = TransactionsGetRequest(
                    access_token=access_token,
                    start_date=date.fromisoformat(start_date),
                    end_date=date.fromisoformat(end_date),
                    options=TransactionsGetRequestOptions(
                        offset=len(transactions),
                        account_ids=accountlist
                    )
                )
                response = client.transactions_get(request)
                transactions.extend(response['transactions'])

            for transaction in transactions:
                try:
                    existing_trans = us.transaction_set.get(transaction_id=transaction['transaction_id'])
                    #                builtin_cat = Category.objects.get(pk=transaction['builtin_cat_id'])
                    #                existing_trans.builtin_category = builtin_cat
                    existing_trans.save()
                    continue
                except Transaction.DoesNotExist:
                    new_trans = Transaction()
                    new_trans.account = us.account_set.get(plaid_account_id=transaction['account_id'])
                    new_trans.account_owner = transaction['account_owner']
                    new_trans.amount = transaction['amount']
                    new_trans.authorized_date = transaction['authorized_date']

                    #                builtin_cat = Category.objects.get(pk=transaction['builtin_cat_id'])
                    #                new_trans.builtin_category = builtin_cat

                    new_trans.category = transaction['category']
                    new_trans.category_id = transaction['category_id']
                    new_trans.date = transaction['date'].strftime('%Y-%m-%d')
                    new_trans.iso_currency_code = transaction['iso_currency_code']
                    #                new_trans.location = transaction['location']
                    new_trans.merchant_name = transaction['merchant_name']
                    new_trans.name = transaction['name']
                    #                new_trans.payment_meta = transaction['payment_meta']
                    new_trans.payment_channel = transaction['payment_channel']
                    new_trans.pending = transaction['pending']
                    new_trans.pending_transaction_id = transaction['pending_transaction_id']
                    new_trans.transaction_code = transaction['transaction_code']
                    new_trans.transaction_id = transaction['transaction_id']
                    new_trans.transaction_type = transaction['transaction_type']
                    new_trans.unofficial_currency_code = transaction['unofficial_currency_code']
                    new_trans.user = us
                    new_trans.save()
                    try:
                        print('trying to update transaction')
                        print(new_trans.date)
                        transdate = str(new_trans.date)
                        dailyresult = Dailyresult.objects.get(user = us, date = transdate)
                        drsp = str(dailyresult.spent)
                        drsp = float(drsp)
                        ntamt = str(new_trans.amount)
                        ntamt = float(ntamt)
                        spentupdate = drsp + ntamt
                        print(spentupdate)
                        dailyresult.spent = spentupdate
                        dailyresult.save()
                        print('updated transaction')
                    except:
                        pass

        print('all done')

@shared_task
def create_day():
    today = date.today()
    User = get_user_model()
    users = User.objects.all()
    for us in users:
        try:
            dayentry = Dailyresult.objects.get(user=us, date=today)
        except:
            dayentry = Dailyresult(user=us, date=today)
            dayentry.save()
        trans = Transaction.objects.filter(user=us, date=today)
        total = 0
        for a in trans:
            amount = a.amount
            total = total + amount
        budget = Spendable.objects.get(user=us, current=True)
        dispincome = budget.dispincome
        leftover = int(dispincome) - total
        dayentry.budget = dispincome
        dayentry.spent = total
        dayentry.leftover = leftover
        dayentry.save()

@shared_task
def daily_email():
    User = get_user_model()
    users = User.objects.all()
    for us in users:
        allresults = Dailyresult.objects.filter(user=us)
        today = date.today()
        dayresult = Dailyresult.objects.get(user=us, date=today)
        daybudget = dayresult.budget
        dayspent = dayresult.spent
        dayleftover = dayresult.leftover
        daypercentraw = dayspent/daybudget
        dayshortmsg = spendeval(daypercentraw)[0]
        daylongmsg = spendeval(daypercentraw)[1]
        daypercentreadable = round((daypercentraw*100), 1)
        todayprint = today.strftime("%m/%d/%Y")
        today = today.strftime("%Y-%m-%d")
        today = date.fromisoformat(today)
        sevendayend = today - timedelta(days=7)
        sevenbudget = 0
        sevenspent = 0
        sevenleftover = 0
        for i in range(1, 8):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            sevenbudget = sevenbudget + dresults.budget
            sevenspent = sevenspent + dresults.spent
            sevenleftover = sevenleftover + dresults.leftover
        sevenpercent = sevenspent/sevenbudget
        sevenshortmsg = spendeval(sevenpercent)[0]
        sevenlongmsg = spendeval(sevenpercent)[1]
        sevenpercentreadable = round((sevenpercent*100), 1)
        print (sevenbudget, sevenspent, sevenleftover)
        thirtybudget = 0
        thirtyspent = 0
        thirtyleftover = 0
        for i in range(1, 31):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            thirtybudget = thirtybudget + dresults.budget
            thirtyspent = thirtyspent + dresults.spent
            thirtyleftover = thirtyleftover + dresults.leftover
        thirtypercent = thirtyspent/thirtybudget
        thirtyshortmsg = spendeval(thirtypercent)[0]
        thirtylongmsg = spendeval(thirtypercent)[1]
        thirtypercentreadable = round((thirtypercent*100), 1)
        print (thirtybudget, thirtyspent, thirtyleftover)

        sixtybudget = 0
        sixtyspent = 0
        sixtyleftover = 0
        for i in range(1, 61):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            sixtybudget = sixtybudget + dresults.budget
            sixtyspent = sixtyspent + dresults.spent
            sixtyleftover = sixtyleftover + dresults.leftover
        sixtypercent = sixtyspent/sixtybudget
        sixtyshortmsg = spendeval(sixtypercent)[0]
        sixtylongmsg = spendeval(sixtypercent)[1]
        sixtypercentreadable = round((sixtypercent*100), 1)
        print (sixtybudget, sixtyspent, sixtyleftover)

        ninetybudget = 0
        ninetyspent = 0
        ninetyleftover = 0
        for i in range(1, 91):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            ninetybudget = ninetybudget + dresults.budget
            ninetyspent = ninetyspent + dresults.spent
            ninetyleftover = ninetyleftover + dresults.leftover
        ninetypercent = ninetyspent/ninetybudget
        ninetyshortmsg = spendeval(ninetypercent)[0]
        ninetylongmsg = spendeval(ninetypercent)[1]
        ninetypercentreadable = round((ninetypercent*100), 1)
        print (ninetybudget, ninetyspent, ninetyleftover)

        oneeightbudget = 0
        oneeightspent = 0
        oneeightleftover = 0
        for i in range(1, 181):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            oneeightbudget = oneeightbudget + dresults.budget
            oneeightspent = oneeightspent + dresults.spent
            oneeightleftover = oneeightleftover + dresults.leftover
        oneeightpercent = oneeightspent/oneeightbudget
        oneeightshortmsg = spendeval(oneeightpercent)[0]
        oneeightlongmsg = spendeval(oneeightpercent)[1]
        oneeightpercentreadable = round((oneeightpercent*100), 1)
        print (oneeightbudget, oneeightspent, oneeightleftover)

        threesixbudget = 0
        threesixspent = 0
        threesixleftover = 0
        for i in range(1, 366):
            day = today - timedelta(days=i)
            dresults = Dailyresult.objects.get(user=us, date=day)
            threesixbudget = threesixbudget + dresults.budget
            threesixspent = threesixspent + dresults.spent
            threesixleftover = threesixleftover + dresults.leftover
        threesixpercent = threesixspent/threesixbudget
        threesixshortmsg = spendeval(threesixpercent)[0]
        threesixlongmsg = spendeval(threesixpercent)[1]
        threesixpercentreadable = round((threesixpercent*100), 1)
        print (threesixbudget, threesixspent, threesixleftover)
        transactions = Transaction.objects.filter(user=us)
        msg = EmailMessage(
            from_email='gene.sussman@gmail.com',
            to=['gene.sussman@gmail.com'],
        )
        msg.template_id = "d-4a98398932b342228c07ed7982d765f2"
        msg.dynamic_template_data = {
            "todaydate": str(todayprint),
            "sevenbudget": str(sevenbudget),
            "sevenspent": str(sevenspent),
            "sevenleftover": str(sevenleftover),
            "thirtybudget": str(thirtybudget),
            "thirtyspent": str(thirtyspent),
            "thirtyleftover": str(thirtyleftover),
            "sixtybudget": str(sixtybudget),
            "sixtyspent": str(sixtyspent),
            "sixtyleftover": str(sixtyleftover),
            "ninetybudget": str(ninetybudget),
            "ninetyspent": str(ninetyspent),
            "ninetyleftover": str(ninetyleftover),
            "oneeightbudget": str(oneeightbudget),
            "oneeightspent": str(oneeightspent),
            "oneeightleftover": str(oneeightleftover),
            "threesixbudget": str(threesixbudget),
            "threesixspent": str(threesixspent),
            "threesixleftover": str(threesixleftover),
            "daybudget" : str(daybudget),
            "dayspent" : str(dayspent),
            "dayleftover" : str(dayleftover),
            "dayshortmsg" : dayshortmsg,
            "daylongmsg" : daylongmsg,
            "daypercentreadable" : str(daypercentreadable),
            "sevenshortmsg" : sevenshortmsg,
            "sevenlongmsg" : sevenlongmsg,
            "sevenpercentreadable" : str(sevenpercentreadable),
            "thirtyshortmsg" : thirtyshortmsg,
            "thirtylongmsg" : thirtylongmsg,
            "thirtypercentreadable" : str(thirtypercentreadable),
            "sixtyshortmsg" : sixtyshortmsg,
            "sixtylongmsg" : sixtylongmsg,
            "sixtypercentreadable" : str(sixtypercentreadable),
            "ninetyshortmsg" : ninetyshortmsg,
            "ninetylongmsg" : ninetylongmsg,
            "ninetypercentreadable" : str(ninetypercentreadable),
            "oneeightshortmsg" : oneeightshortmsg,
            "oneeightlongmsg" : oneeightlongmsg,
            "oneeightpercentreadable" : str(oneeightpercentreadable),
            "threesixshortmsg" : threesixshortmsg,
            "threesixlongmsg" : threesixlongmsg,
            "threesixpercentreadable" : str(threesixpercentreadable),
        }
        msg.send(fail_silently=False)


