import requests
import datetime
import os
import json

CACHE_DIR = "./cache"
DUST_TABLE = "./cardust.csv"
CRAFT_TABLE = "./cardcraft.csv"

SALE_TAX = 0.11

#Class that represents a card lifted from the market
class Card:

    def __init__(self, name, cost):
        self.name = name
        self.cost = cost
        self.dust = 0
        self.zPerDust = 0

    def setDust(self,dust):
        self.dust = dust
        self.zPerDust = self.cost/dust

    def __str__(self):
        return "{}: {},{}".format(self.name,self.cost,self.zPerDust)

    def __hash__(self):
        return hash(self.name)

#Class that represents a crafting recipe
class Recipe:

    def __init__(self, string):
        split = string.strip().split(",")
        self.name = split.pop(0)
        self.cards = []
        self.dustNeeded = 0
        self.zenyNeeded = 0
        for elem in split:
            if elem[0] == '@':
                self.dustNeeded = int(elem[1:])
            elif elem[0] == '$':
                self.zenyNeeded = int(elem[1:])
            else:
                self.cards.append(elem)

    #Calculates the cost and profit of the crafting
    def calcCostAndProfit(self, priceOneDust, cards):
        self.cost = 0
        self.profit = 0
        if self.name not in cards: #No date
            return
        for cardName in self.cards:
            if cardName not in cards: #No data
                return
            self.cost += cards[cardName].cost
        self.cost += priceOneDust*self.dustNeeded
        self.cost += self.zenyNeeded
        self.profit = int(cards[self.name].cost*(1-SALE_TAX)-self.cost)
        return

    def __str__(self):
        return "{}: Cost:{}, Profit:{} - Needs: {}{}dust{}zeny".format(self.name,self.cost,self.profit,self.cards,self.dustNeeded,self.zenyNeeded)
            
#Reads the jsons from the cache directory for the given date. Existance isn't checked.
def loadFromCache(date):
    dateDir = os.path.join(CACHE_DIR,date)
    files = []
    data = []
    for r, d, f in os.walk(dateDir):
        for file in f:
            files.append(os.path.join(r, file))
            print(os.path.join(r, file))
    for file in files:
        with open(file,"r") as f:
            data.append(json.load(f))            
    return data

#Reads the jsons from the website
def loadFromSite(date):
    dateDir = os.path.join(CACHE_DIR,date)
    try:
        os.mkdir(dateDir)
    except:
        pass
    jsons = []
    code = 200
    index = 0
    while True:
        r = requests.get('https://us-central1-rom-exchange.cloudfunctions.net/api?item=card&exact=false&slim=true&page='+str(index))
        code = r.status_code
        if code != 200:
            print(str(code)+":"+str(r.content))
            exit(1)
        receivedJson = r.json()
        if len(receivedJson) == 0:
            break
        else:
            jsons.append(receivedJson)
            with open(os.path.join(dateDir,str(index))+".json", "w") as f:
                #f.write(str(json).replace("'","\'").replace("None","null"))
                json.dump(receivedJson, f)
            print("Fetched page: "+str(index))
            index += 1     
    return jsons

#Checks the fetching options and returns an array of jsons
def fetchData(ignoreCache=False):
    today = str(datetime.date.today())
    dirPath = os.path.join(CACHE_DIR,today)
    if (os.path.isdir(dirPath)) and len(os.listdir(dirPath)) != 0:
        return loadFromCache(today)
    else:
        return loadFromSite(today)

#Given an array of jsons, turns them into a card price dictionary
def parseData(jsonArray):
    cards = {}
    for json in jsonArray:
        for elem in json:
            cost = int(elem['global']['latest'])
            name = elem['name'].strip("Card").strip()
            if cost > 0 and not "[" in name:                
                card = Card(name,cost)
                cards[name] = card
    return cards

#Gets the price data
def fetchPriceData():
    jsons = fetchData()
    return parseData(jsons)

#Returns a list with the cheapest num cards for dusting, given a dictionary of cards with dust values
def findCheapestDust(num, cards):
    return list(filter(lambda x:x.zPerDust > 0,sorted(list(cards.values()),key=lambda x: x.zPerDust)))

#Loads the dusting numnbers from the file
def loadDust(cards):
    with open(DUST_TABLE, "r") as file:
        lines = file.readlines()
        for line in lines:
            if len(line) > 0 and line[0] != "/":
                split = line.strip().split(",")
                cardName = split[0]
                if cardName in cards:
                    if len(split[1]) > 0:
                        dust = int(split[1])
                        cards[cardName].setDust(dust)

#Loads the recipes from the file
def loadRecipes():
    recipes = {}
    with open(CRAFT_TABLE, "r") as file:
        lines = file.readlines()
        for line in lines:
            if len(line) > 0 and line[0] != "/":
                recipe = Recipe(line)
                recipes[recipe.name] = recipe
    return recipes

def calcRecipeProfit(recipes, cards, priceOneDust):
    for recipe in recipes.values():
        recipe.calcCostAndProfit(priceOneDust,cards)
    return recipes

def loadData():
    cardPrices = fetchPriceData()
    loadDust(cardPrices)
    cheapestDust = findCheapestDust(10,cardPrices)
    profit = calcRecipeProfit(loadRecipes(),cardPrices,cheapestDust[0].zPerDust)
    return cardPrices,cheapestDust,profit

#Prints all the relevant stuff
def printAll(num):
    cardPrices,cheapestDust,profit = loadData()
    print("--------------------- Cheapest cards")
    cards = sorted(list(cardPrices.values()),key=lambda x: x.cost)
    for x in range(num):
        print(cards[x])
    print("------------------------ Cheapest powder")
    for x in range(num):
        print(cheapestDust[x])
    print("------------------------ Profit opportunities")
    recipes = sorted(list(profit.values()),key=lambda x: x.profit,reverse=True)
    for x in range(len(recipes)):
        if recipes[x].cost > 0 and recipes[x].profit > 0:
            print(recipes[x])

#Prints the cheapest num cards for dusting
def printCheapestDust(num):
    data = fetchPriceData()
    loadDust(data)


printAll(10)
