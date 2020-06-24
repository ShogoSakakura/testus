# インポートするライブラリ
from flask import Flask, request, abort

from linebot import (
    LineBotApi, WebhookHandler
)
from linebot.exceptions import (
    InvalidSignatureError
)
from linebot.models import (
    FollowEvent, MessageEvent, TextMessage, TextSendMessage, ImageMessage, ImageSendMessage, TemplateSendMessage, ButtonsTemplate, PostbackTemplateAction, MessageTemplateAction, URITemplateAction
)
import os

# バーコード画像を文字列に変換
from pyzbar.pyzbar import decode
from PIL import Image
import io

# バーコード文字列から商品を検索(Yahoo! ショッピングのみ)
import urllib
import time
from bs4 import BeautifulSoup

# 軽量なウェブアプリケーションフレームワーク:Flask
app = Flask(__name__)


#環境変数からLINE Access Tokenを設定
LINE_CHANNEL_ACCESS_TOKEN = os.environ["LINE_CHANNEL_ACCESS_TOKEN"]
#環境変数からLINE Channel Secretを設定
LINE_CHANNEL_SECRET = os.environ["LINE_CHANNEL_SECRET"]

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# MessageEvent
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    message = event.message.text
    print(message)

    reply_text = 'バーコード(JAN)の画像を送ってください'

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
     )

# ImageEvent
@handler.add(MessageEvent, message=ImageMessage)
def handle_image(event):
    # print("handle_image:", event)

    message_id = event.message.id
    message_content = line_bot_api.get_message_content(message_id)

    image = io.BytesIO(message_content.content)

    code, flag_a = convert_barcode_to_character(image)

    print('バーコードリードの結果：{},{}'.format(code, flag_a))

    # バーコードリード成功
    if (flag_a == False):
        jc_name, flag_c = jancode_search(code)

        # 指定JANコードの商品を発見
        if (flag_c == False):
            dtc_name, price, flag_b = kakaku_dotcom_search(code)

            # 商品発見
            if (flag_b == False):
                reply_text = '価格ドットコムの検索結果\n商品名：{}\n価格：{}\n'.format(jc_name,price)

            # 商品発見できず
            else:
                reply_text = '価格ドットコムでは商品が見つかりません'

        else:
            reply_text = '指定JANコードの商品が見つかりません'

    # バーコードリード失敗
    else:
        reply_text = 'JANコード読み取り失敗。\n'

    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=reply_text)
     )   


from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

# 天気を教えてくれる(削除予定)
# def tenki():
#     options = Options()
#     # 追加
#     options.binary_location = '/app/.apt/usr/bin/google-chrome'
#     options.add_argument('--headless')
#     # コメントアウト
#     # browser = webdriver.Chrome(executable_path=r'D:\Program\chromedriver.exe', chrome_options=options)
#     driver = webdriver.Chrome(chrome_options=options)

#     # Yahooの天気サイトにアクセス
#     driver.get('https://weather.yahoo.co.jp/weather/')

#     # ソースコードを取得
#     html = driver.page_source

#     # ブラウザを終了する
#     driver.quit()

#     # HTMLをパースする
#     soup = BeautifulSoup(html, 'html.parser') # または、'html.parser'

#     # スクレイピングした《今日の日本の天気予報の要約》を変数に格納
#     message = soup.select_one('#condition > p.text').get_text()

#     return message

# 商品検索(価格ドットコム)
def kakaku_dotcom_search(code):
    options = Options()

    # 追加
    options.binary_location = '/app/.apt/usr/bin/google-chrome'
    options.add_argument('--headless')

    driver = webdriver.Chrome(chrome_options=options)

    URL = 'https://kakaku.com/search_results/{}/'.format(code)
    print(URL)

    driver.get(URL)

    num_of_hits = driver.find_elements_by_xpath('//*[@id="default"]/div[2]/div[2]/div/div[3]/div[1]/span/span')[0].text
    print('Hit件数：{}件'.format(num_of_hits))
    
    if(int(num_of_hits)==0):
        print('Hitなし')        

        # ブラウザを終了する
        driver.quit()

        return None, None, True

    else:
        product_name = driver.find_elements_by_xpath('//*[@id="default"]/div[2]/div[2]/div/div[4]/div/div[1]/div/div[1]/div[1]/div/p[1]')[0].text
        product_price = driver.find_elements_by_xpath('//*[@id="default"]/div[2]/div[2]/div/div[4]/div/div[1]/div/div[2]/div/p/span')[0].text

        print('商品名：{}'.format(product_name))
        print('価格：{}'.format(product_price))

        # ブラウザを終了する
        driver.quit()

        return product_name, product_price, False

# 商品検索(jancode)
def jancode_search(code):
    options = Options()

    # 追加
    options.binary_location = '/app/.apt/usr/bin/google-chrome'
    options.add_argument('--headless')

    driver = webdriver.Chrome(chrome_options=options)

    URL = 'https://www.janken.jp/gadgets/jan/JanSyohinKensaku.php'
    print(URL)

    driver.get(URL)

    driver.find_elements_by_xpath('/html/body/div/form/input[2]')[0].send_keys(code)
    driver.find_elements_by_xpath('/html/body/div/form/input[3]')[0].click()

    try:
        product_name = driver.find_elements_by_xpath('/html/body/div/table/tbody/tr[1]/td[2]/a')[0].text

    except:
        return None, True
    
    driver.quit()
    print('商品名：{}'.format(product_name))  
    return product_name, False

# バーコード画像を文字列に変換
def convert_barcode_to_character(image):
    not_found_flag = False

    pil_img = Image.open(image) 

    # バーコードの読取り
    data = decode(pil_img)

    if (data == []):
        not_found_flag = True
        return '', not_found_flag

    else:
        # 文字列コード
        code = data[0][0].decode('utf-8', 'ignore')
        return code, not_found_flag

# バーコード文字列から商品を検索(Yahoo! ショッピングのみ)(削除予定)
# def code_to_product_info(code):
#     not_found_flag = False

#     start_time = time.time()

#     product_info = None
#     client_id = 'dj00aiZpPWFJNndwRjFUNUdWViZzPWNvbnN1bWVyc2VjcmV0Jng9OTg-'

#     url = 'http://shopping.yahooapis.jp/ShoppingWebService/V1/itemSearch?appid={0}&jan={1}'.format(client_id, code)
#     response = urllib.request.urlopen(url)#.read()
#     soup = BeautifulSoup(response)
#     res = soup.find_all('name') # nameタグを取得
#     #ここから超雑
#     if (res==[]):
#         not_found_flag = True

#     elif len(res) > 0:
#         product_info = res[0]
    
#     return product_info, not_found_flag

if __name__ == "__main__":
    port = int(os.getenv("PORT"))
    app.run(host="0.0.0.0", port=port)