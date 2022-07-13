from lib2to3.pgen2 import token
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from operator import itemgetter
import datetime

creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json')
gc = gspread.authorize(creds)

sh = gc.open('Bhlist')


worksheet_list = sh.worksheets()
print(worksheet_list)

worksheet = sh.get_worksheet(0)

list_of_lists = worksheet.get_all_values()
print(list_of_lists)




print("-----------------------------")
s=sorted(list_of_lists, key=lambda x: datetime.datetime.strptime(x[2],'%Y-%m-%d'))
print(s)

txt=''
for ss in s:
    txt=txt+ss[0]+"  "+ss[1]+'\n'
    print(ss)




import requests



def telegram_bot_sendtext(bot_message):
    bot_token = '5581022067:AAEioxFbXMInJ2cUBfHpwbSaflsxVgOH2CQ'
    bot_chatID = '109495759'
    send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message

    response = requests.get(send_text)

    return response.json()

print(telegram_bot_sendtext(str(txt)))














