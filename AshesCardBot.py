import RedditBotClass
import config
import os
import json
import requests
from tinydb import TinyDB, Query

def load_cards(api_link):
	response = requests.get(api_link)
	result = json.loads(response.text)
	for card in result["results"]:
		cardStub = card["stub"]
		entry = cardTable.search(cardQuery.stub == cardStub)
		if not entry:
			cardTable.insert({'stub':cardStub,'visited':False})
			print(cardStub + " doesn't exists yet, so creating")
				
	if result["next"] is not None:
		load_cards(result["next"])

if not os.path.exists('db.json'):
    open("db.json", "w+")

database = TinyDB("db.json")
cardQuery = Query()
cardTable = database.table('cards')

load_cards("https://api.ashes.live/v2/cards?limit=" + str(config.card_import_limit) + "&sort=name&order=asc")

bot = RedditBotClass.RedditBot(config, database)
bot.run_bot()