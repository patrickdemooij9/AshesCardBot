import praw
import time
import re
import requests
import json
import os
import random
import datetime
from datetime import date
from tinydb import TinyDB, Query


class RedditBot(object):
    def __init__(self, config, database):
        self.database = database
        self.started = False
        self.db = TinyDB('db.json')
        self.login(config)

    def login(self, config):
        self.reddit = praw.Reddit(username=config.username,
                                  password=config.password,
                                  client_id=config.client_id,
                                  client_secret=config.client_secret,
                                  user_agent=config.user_agent)

    def run_bot(self):
        if (self.started is False):
            self.started = True
            while(self.started is True):
                if (self.__check_for_post_time()):
                    print("Should create new post")
                    cardToVisit = self.__get_latest_card_id()
                    if cardToVisit:
                        print("Visiting card: " + cardToVisit)
                        loadedCardData = self.__load_card_data(cardToVisit)

                        post = self.reddit.subreddit("bottesting").submit(self.__format_post_title(
                            loadedCardData), selftext=self.__format_post_description(loadedCardData))

                        self.__visit_card_id(cardToVisit)
                    else:
                        print("No card found to visit!")

                print("Done with everything. Sleeping")
                time.sleep(3600)

    def __check_for_post_time(self):
        table = self.database.table('posts')
        if len(table) > 0:
            sortedTable = sorted(table, key=lambda k: k["postDate"])
            latestPost = sortedTable[-1]
            latestPostDate = datetime.datetime.strptime(
                latestPost["postDate"], "%a %b %d %H:%M:%S %Y")
            if (latestPostDate + datetime.timedelta(minutes=1440) <= datetime.datetime.now()):
                return True
            return False
        else:
            print("No entries found in database")
            return True

    def __get_latest_card_id(self):
        table = self.database.table('cards')
        if len(table) > 0:
            cardQuery = Query()
            nonVisitedCards = table.search(cardQuery.visited == False)
            if (len(nonVisitedCards) > 0):
                random.shuffle(nonVisitedCards)
                return nonVisitedCards[0]["stub"]
            else:
                print("No new cards to visit!")
        else:
            print("Cards table is empty")

    def __visit_card_id(self, id):
        cardTable = self.database.table('cards')
        cardQuery = Query()
        cardTable.update({'stub': id, 'visited': True}, cardQuery.stub == id)

        postsTable = self.database.table('posts')
        postsTable.insert(
            {'postDate': datetime.datetime.now().ctime(), 'cardCode': id})

    def __load_card_data(self, id):
        response = requests.get("https://api.ashes.live/v2/cards/" + id)
        if response.status_code == 200:
            data = json.loads(response.text)
            return data
        else:
            print("Response returned invalid status code")

    def make_pretty_cost(self, text):
        splitted = text.split("[[")
        amountCost = ""
        diceCost = ""

        if len(splitted) > 1:
            amountCost = splitted[0].strip()
            if amountCost:
                amountCost += "x "
            diceCost = splitted[1].replace("]]", "")
        else:
            diceCost = splitted[0].replace("]]", "")

        text = amountCost
        for cost in diceCost.split(":"):
            text += " " + cost.capitalize()
        return text

    def __format_post_title(self, cardData):
        msg = "[COTW] "
        msg += cardData["name"]
        msg += " (" + date.today().strftime("%Y/%m/%d") + ")"
        return msg

    def __format_post_description(self, cardData):
        msg = "[" + cardData["name"] + \
            "](https://ashes.live/cards/" + cardData["stub"] + "/)"
        msg += " ([Image](https://cdn.ashes.live/images/cards/" + \
                    cardData["stub"] + ".jpg))\n\n"
        if (cardData.get("type")):
                msg += "* **" + cardData["type"] + "**\n\n"

        if (cardData.get("placement")):
            msg += "* **Placement:** " + cardData["placement"] + "\n\n"

        if (cardData.get("phoenixborn")):
            msg += "* **Phoenixborn: " + cardData["phoenixborn"] + "**\n\n"
        if (cardData.get("battlefield")):
            msg += "* **Battlefield: " + str(cardData["battlefield"]) + "**\n\n"
        if (cardData.get("attack")):
            msg += "* **Attack: " + str(cardData["attack"]) + "**\n\n"
        if (cardData.get("life")):
            msg += "* **Life: " + str(cardData["life"]) + "**\n\n"
        if (cardData.get("recover")):
            msg += "* **Recover: " + str(cardData["recover"]) + "**\n\n"
        if (cardData.get("copies")):
            msg += "* **Copies: " + str(cardData["copies"]) + "**\n\n"
        if (cardData.get("spellboard")):
            msg += "* **Spellboard: " + str(cardData["spellboard"]) + "**\n\n"

        if (cardData.get("cost")):
            first = True
            msg += "* **Cost:** [ "
            for cost in cardData["cost"]:
                if not first:
                    msg += ", "
                if isinstance(cost, list):
                    msg += "("
                    for costItem in cost:
                        msg += self.make_pretty_cost(costItem) + " or "
                    msg += ")" 
                else:
                    msg += self.make_pretty_cost(cost)
                first = False
            msg += "]\n\n"

        if (cardData.get("text")):
            for text in cardData["text"].split("\n\n"):
                realText = text
                if (text.startswith("~")):
                    realText = realText.replace("~", "(Reaction Ability)")
                if (text.startswith("*")):
                    realText = realText.replace("*", "(Inexhaustible)")
                if (cardData.get("conjurations")):
                    for conjuration in cardData["conjurations"]:
                        realText = realText.replace("[[" + conjuration["name"] + "]]", "[" + conjuration["name"] +
                                                "](https://ashes.live/cards/" + conjuration["stub"] + "/)")
                otherMatches = re.findall('\[\[(.*?)\]\]', realText)
                for match in otherMatches:
                    realText = realText.replace("[[" + match + "]]", self.make_pretty_cost(match))
                msg += realText + "\n\n"
        if (cardData.get("release")):
            msg += "***" + cardData["release"]["name"] + "***\n\n"

        msg += "\n\n^(This bot is maintained by [Patrick](https://www.reddit.com/user/Patrickdemooij9).)"
        return msg