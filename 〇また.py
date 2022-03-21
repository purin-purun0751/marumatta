import requests
import os.path
import re
import discord
import asyncio
import os, psycopg2
import json
from bs4 import BeautifulSoup

#DBに接続するためのやつ

DATABASE_URL = os.environ.get('DATABASE_URL')

connection = psycopg2.connect(DATABASE_URL)

cur = connection.cursor()
sql = "select token,channel_id from settings"
cur.execute(sql)
result = cur.fetchone()

# トークン取得
TOKEN = result[0]
# チャンネルID取得
CHANNEL_ID = result[1]

# targetテーブルから確認したいコミュニティを取得
def getTarget():
    targetCommunitys = []
    sql = "select community from target"
    cur.execute(sql)
    for row in cur:
        targetCommunitys.append(row[0])
    return targetCommunitys

# 放送URLから放送ID(lvXXXXXXX)抽出
def liveIdExtraction(liveURL):
    repatter = re.compile('lv[0-9]+')
    return repatter.search(liveURL).group()

# 放送URLから放送タイトル取得
def getLiveTitle(liveURL):
    r = requests.get(liveURL)
    soup = BeautifulSoup(r.content, "html.parser")
    for meta_tag in soup.find_all('meta', attrs={'property': 'og:title'}):
        return meta_tag.get('content')

# 放送URLから放送者名取得
def getLiveName(liveURL):
    r = requests.get(liveURL)
    soup = BeautifulSoup(r.content, "html.parser")
    return soup.find("span",{"class":"name"}).text

# logsテーブル内検索 あればTrue 無ければFalseを返す
def searchList(liveURL):
    liveLV = liveIdExtraction(liveURL)
    cur = connection.cursor()
    sql = "SELECT count(*)  FROM logs WHERE live = '" + liveLV + "'"
    cur.execute(sql)
    result = cur.fetchone()
    if int(result[0]) > 0:
        return True
    else:
        return False

# logsテーブルに放送ID追記
def addList(liveURL):
    liveLV = liveIdExtraction(liveURL)
    cur = connection.cursor()
    sql = "insert into logs(live) values('"+ liveLV + "');"
    cur.execute(sql)
    connection.commit()

# 接続に必要なオブジェクトを生成
client = discord.Client()

# 起動時に動作する処理
@client.event
async def on_ready():

    while(True):
        # ターゲットコミュニティの数だけ繰り返す
        targetCommunitys = getTarget()
        for targetCommunity in targetCommunitys:
            # URLを設定
            r = requests.get("https://live.nicovideo.jp/watch/" + targetCommunity)

            # コミュニティTOPページを確認
            soup = BeautifulSoup(r.content, "html.parser")
            result = soup.find('meta', attrs={'property': 'og:url', 'content': True})
            # 放送URL取得
            liveURL = result['content']

            # リスト内を検索してすでに処理済みの放送IDであれば処理しない
            if searchList(liveURL) is False:
                # 放送タイトル取得
                liveTitle = getLiveTitle(liveURL)
                # 放送者名取得
                liveName = getLiveName(liveURL)

                # Discordへ送信
                channel = client.get_channel(int(CHANNEL_ID))
                await channel.send('<@&822022490137559049> '  + liveName + 'さんが配信を開始しました。\n\n' + liveTitle + '\n' + liveURL)

                # 放送ID追記
                addList(liveURL)

       
# Discordに接続
client.run(TOKEN)
