from turtle import left
import requests
from lib2to3.pgen2 import token
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from operator import itemgetter
import datetime
from datetime import date
import schedule
import time
import math

print("imruunging")

def main(telid):
    errorInDataBase = False

    creds = ServiceAccountCredentials.from_json_keyfile_name(
        'credentials.json')
    gc = gspread.authorize(creds)

    sh = gc.open('Bhlist')

    worksheet_list = sh.worksheets()
    # print(worksheet_list)

    worksheet = sh.get_worksheet(0)

    list_of_lists = worksheet.get_all_values()
    # print(list_of_lists)

    """

    print("-----------------------------")
    s = sorted(list_of_lists,
            key=lambda x: datetime.datetime.strptime(x[2], '%Y-%m-%d'))
    print(s)

    """

    nowdate = datetime.date.today().strftime('%Y-%m-%d')
    bhlist = []
    # print(nowdate)
    # print(type(nowdate))
    for ss in list_of_lists:
        try:
            bhdate = ss[2]
            date_now_obj = datetime.datetime.strptime(nowdate, '%Y-%m-%d')
            date_bhdate_obj = datetime.datetime.strptime(bhdate, '%Y-%m-%d')
            delta = date_now_obj - date_bhdate_obj

            ecp = delta.days % 365.2425
            left_day_s = 365.2425-ecp
            left_day_s = math.floor(left_day_s)

            ss.append(left_day_s)
            bhlist.append(ss)

        except:
            errorInDataBase = True

            pass

    bhlist_s = sorted(bhlist, key=itemgetter(3))

    def geticon(x):
        if x < 0:
            return""
        if x == 0:
            return "🎊🎊🎊"
        if x < 10:
            return "🟧"

        if x < 30:
            return "🟨"

        if x < 90:
            return "🟩"
        else:
            return "⬛️"

    txt = ''
    linec = 1
    for ss in bhlist_s:
        txt = txt+str(linec)+")"+ss[0]+"  \["+ss[1]+"]  " + \
            str(ss[3])+"روز مانده"+geticon(ss[3])+'\n'
        linec += 1

    txt = txt+'\n'+"<—ئایان لیست->"+'\n'
    if errorInDataBase == True:
        txt = txt+'\n'+"خطا در دیتابیس"+'\n'

    def telegram_bot_sendtext(bot_message, telid):
        bot_token = '5581022067:AAEioxFbXMInJ2cUBfHpwbSaflsxVgOH2CQ'
        bot_chatID = telid
        send_text = 'https://api.telegram.org/bot' + bot_token + \
            '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

        response = requests.get(send_text)

        return response.json()
    try:
        log = str(telegram_bot_sendtext(str(txt), telid)[
                  'ok'])+str(datetime.datetime.now())+'\n'
    except Exception as e:
        log = str(datetime.datetime.now()) + str(e)+'\n'
    print(log)

    with open("wdfurbh_log_.txt", "a") as file:
        file.write(log)
        file.close


def send():
    reciver_list = ['77931666', '109495759', '134097516','337513902']
    for reciver in reciver_list:
        main(reciver)


send()

try:
    schedule.every(43200).seconds.do(send)

except Exception as e:
    print(e)
    with open("wdfurbh_log_.txt", "a") as file:
        file.write(str(e))
        file.close

while True:

    # Checks whether a scheduled task
    # is pending to run or not
    schedule.run_pending()
    time.sleep(1)
