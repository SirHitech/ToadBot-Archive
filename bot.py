# bot.py
import os
import pickle
import asyncio
import discord
import math
import random
from discord.ext import commands, tasks
from discord.utils import get
from dotenv import load_dotenv

#setup
print('Initializing Toad...')
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')
GUILD = os.getenv('DISCORD_GUILD')
bot = commands.Bot(command_prefix='!')
bettersFile = 'betters.pickle'
timeoutFile = 'timeout.pickle'
houseRateFile = 'house.pickle'
toadBetString = "Current bet: "

#globals
betters = {}
currentBet = ""
betMessageID = -1
isLocked = False
believersDict = {}
doubtersDict = {}
bettingTime = 120
activeBetters = []
presets = {
    "bbb" : (
    "Does he get bomb clip?",
    "Does he get Lakitu skip?"
    ),
    "wf" : (
    "Does he avoid the good luck pole on Wild Blue?",
    "Does he use less than 5 walljumps combined to get to the red coin island (Whomp + Fortress stars)?",
    "Does he collect the Whomp star without needing to adjust?"
    ),
    "ccm" : (
    "Does he hold onto the baby penguin in CCM the entire time before spawning the star? (any drop = failure)",
    "Does he get the faith jump in CCM first try?"
    ),
    "bowser1" : (
    "Does avoid getting the UBER CHARGE in Bowser 1??",
    "Does he kill Bowser 1 in 1 throw?",
    "Does he avoid taking any damage during Bowser 1 split?"
    ),
    "ssl" : (
    "Does he get BOING star first try in SSL?",
    "No deaths in SSL?",
    "Does he avoid sliding on the pyramid?"
    ),
    "lll" : (
    "Does he avoid getting burned during LLL split?"
    ),
    "hmc" : (
    "No deaths in HMC?",
    "Does he avoid taking damage from the scuttlebug in HMC?",
    "Does he avoid all boulders during the Boulder star in HMC?",
    "Does he talk to Toad without punching him?"
    ),
    "ddd" : (
    "Less than 3 dives to grab MIPS?",
    "Both MIPS clips without any failures? (dropping MIPS without clipping either door)",
    "Back of the sub sideflip first try? (walking away from sub + jump without sideflip = failure)"
    ),
    "bowser2" : (
    "Does he kill Bowser 2 in 1 throw?",
    "Does he end Bowser 2 with an even number of coins?"
    ),
    "bowser3" : (
    "Does he kill Bowser 3 in less than 5 throws?",
    "Does he avoid getting the UBER CHARGE in Bowser 3??",
    "Does he save time on the Bowser 3 split? (Not the entire run, just the split)"
    )
}

#constants
houseRate = 0.5

@bot.command(name='resetpoints')
async def resetpoints(context):
    if context.author.name == 'SirHitech':
        for better in betters:
            betters[better] = 50
        await context.send("All betters' points have been reset to 50.")

@bot.event
async def on_ready():
    global bettingTime
    print(f'{bot.user.name} has connected to Discord!')
    betters = loadBetters()
    bettingTime = loadTimeout()
    awardPoints.start()
    
@tasks.loop(minutes=15)
async def awardPoints():
    global activeBetters
    for better in activeBetters:
        betters[better] += 10
    activeBetters = []

@bot.command(name='register')
async def register(context):
    print(f'Attempting to register user.id {context.author.id}')
    if context.author.id in betters:
        await context.send(":warning: User is already registered.")
        return
    else:
        betters[context.author.id] = 50
        await saveBetters()
        await context.send(f"Successfully registered user: {context.author.name}. You have been given 50 points, good luck!")
        return

@bot.command(name='bet')
async def bet(context, *, arg):
    global currentBet
    if hasPermission(context.author):
        if currentBet:
            await context.send(f":warning: There is already an ongoing bet: '{currentBet}'")
        else:
            if arg in presets:
                currentBet = random.choice(presets[arg])
            else:
                currentBet = arg
            await context.send("New bet has been set! Vote with '!believe _amount_', or '!doubt _amount_'.")
            await context.send(f"{toadBetString} `{currentBet}`")
        
@bot.command(name='believe')
async def believe(context, argAmount):
    if currentBet:
        if context.author.id in believersDict or context.author.id in doubtersDict:
            await context.send(f":warning: {context.author.name} has already placed a bet.")
            return
        if argAmount.isdigit() and argAmount != '0':
            if context.author.id in betters:
                if betters[context.author.id] >= int(argAmount):
                    await predict(context.author, int(argAmount), True)
                    await context.send(f"Bet entered: {context.author.name} **believes** for {argAmount} points.")
                    return
                else:
                    await context.send(f":warning: {context.author.name} has insufficient points for that bet.")
                    return
            else:
                await context.send(f"User {context.author.name} is not yet registered. Please use !register before predicting.")
        else:
            await context.send(f":warning: Amount bet must be a positive whole number.")
            return
    else:
        await context.send(f":warning: A bet has not been started. Set one with !bet _betDesc_.")
        
@bot.command(name='doubt')
async def doubt(context, argAmount):
    if currentBet:
        if context.author.id in doubtersDict or context.author.id in believersDict:
            await context.send(f":warning: {context.author.name} has already placed a bet.")
            return
        if argAmount.isdigit() and argAmount != '0':
            if context.author.id in betters:
                if betters[context.author.id] >= int(argAmount):
                    await predict(context.author, int(argAmount), False)
                    await context.send(f"Bet entered: {context.author.name} **doubts** for {argAmount} points.")
                    return
                else:
                    await context.send(f":warning: {context.author.name} has insufficient points for that bet.")
                    return
            else:
                await context.send(f"User {context.author.name} is not yet registered. Please use !register before predicting.")
        else:
            await context.send(f":warning: Amount bet must be a positive whole number.")
            return
    else:
        await context.send(f":warning: A bet has not been started. Set one with !bet _betDesc_.")
        
@bot.command(name='currentbet')
async def currentbet(context):
    if currentBet:
        await context.send(f"`{currentBet}`")
    else:
        await context.send("A bet has not been started. Set one with !bet _betDesc_.")
        
@bot.command(name='timeout')
async def timeout(context, argTimeout):
    global bettingTime
    if hasPermission(context.author):
        if argTimeout.isdigit() and argTimeout != '0':
            bettingTime = int(argTimeout)
            await saveTimeout()
            await context.send(f"Betting timeout has been updated to {argTimeout}s")
        else:
            await context.send("Timeout value must be a positive whole number.")
    else:
        await context.send("You do not have permission to do that.")

@bot.command(name='points')
async def points(context):
    if context.author.id in betters:
        if context.author.id in believersDict:
            adjustedPoints = betters[context.author.id] - believersDict[context.author.id]
            print(f"Adjusted believe point check: {context.author.name} has {betters[context.author.id]} - {believersDict[context.author.id]} points")
            await context.send(f"{context.author.name} has {adjustedPoints} points.")
        elif context.author.id in doubtersDict:
            adjustedPoints = betters[context.author.id] - doubtersDict[context.author.id]
            print(f"Adjusted doubt point check: {context.author.name} has {betters[context.author.id]} - {doubtersDict[context.author.id]} points")
            await context.send(f"{context.author.name} has {adjustedPoints} points.")
        else:
            print(f"Non-adjusted points check made. {context.author.name} has {betters[context.author.id]} points.")
            await context.send(f"{context.author.name} has {betters[context.author.id]} points.")
    else:
        await context.send(f"User {context.author.name} is not yet registered. Please use !register before predicting.")
    
@bot.event
async def on_message(message):
    if message.author == bot.user and toadBetString in message.content:
        await message.add_reaction('🔒')
        await message.add_reaction('🙏')
        await message.add_reaction('😈')
        await message.add_reaction('❌')
        
        global betMessageID
        betMessageID = message.id
        
        try:
            reaction, user = await bot.wait_for('reaction_add', timeout=bettingTime, check=checkForLock)
        except asyncio.TimeoutError:
            if currentBet:
                if betMessageID == message.id:
                    await lockBet(message.channel, f"Betting time has elapsed ({bettingTime}s), bets have been locked in.")
        else:
            if currentBet:
                await lockBet(message.channel, f"Bet has been locked, no more predictions submissions can be placed.")
    await bot.process_commands(message)

@bot.event
async def on_raw_reaction_add(payload):
    if payload.message_id == betMessageID:
        if hasPermission(payload.member):
            channel = bot.get_channel(payload.channel_id)
            if payload.emoji.name == '🙏':
                await payout(channel, True)
            elif payload.emoji.name == '😈':
                await payout(channel, False)
            elif payload.emoji.name == '❌':
                await refundBet(channel, f"Bet cancelled, all predictions have been refunded.")

async def payout(channel, doBelieversWin):
    global betters
    
    believersTotal = 0
    for believer in believersDict:
        believersTotal += believersDict[believer]
    doubtersTotal = 0
    for doubter in doubtersDict:
        doubtersTotal += doubtersDict[doubter]
    if believersTotal == 0 and doubtersTotal == 0:
        if doBelieversWin:
            await channel.send("Believers win, but no bets were made so no payouts will be made.")
        else:
            await channel.send("Doubters win, but no bets were made so no payouts will be made.")
    elif doubtersTotal == 0:
        if doBelieversWin:
            await channel.send(f"Believers win! Calculating house odds ({houseRate}x) for betters.")
            for believer in believersDict:
                print(f"believerID: {believer}")
                user = await bot.fetch_user(believer)
                winnings = math.floor(believersDict[believer] * 0.5)
                betters[believer] += winnings
                await channel.send(f"{user.name} has won {winnings} points!")
        else:
            for believer in believersDict:
                betters[believer] -= believersDict[believer]
            await channel.send("Doubters win! Better luck next time!")
    elif believersTotal == 0:
        if not doBelieversWin:
            await channel.send(f"Doubters win! Calculating house odds ({houseRate}x) for betters.")
            for doubter in doubtersDict:
                print(f"doubterID: {doubter}")
                user = await bot.fetch_user(doubter)
                winnings = math.floor(doubtersDict[doubter] * 0.5)
                betters[doubter] += winnings
                await channel.send(f"{user.name} has won {winnings} points!")
        else:
            for doubter in doubtersDict:
                betters[doubter] -= doubtersDict[doubter]
            await channel.send("Believers win! Better luck next time!")
    else:
        if doBelieversWin:
            await channel.send(f"Believers win!")
            totalBelieveAmount = 0
            for believer in believersDict:
                totalBelieveAmount += believersDict[believer]
            totalDoubtAmount = 0
            for doubter in doubtersDict:
                totalDoubtAmount += doubtersDict[doubter]
            for believer in believersDict:
                print(f"believerID: {believer}")
                user = await bot.fetch_user(believer)
                payoutRate = totalDoubtAmount / totalBelieveAmount
                winnings = math.floor(believersDict[believer] * payoutRate)
                betters[believer] += winnings
                await channel.send(f"{user.name} has won {winnings} points!")
            for doubter in doubtersDict:
                betters[doubter] -= doubtersDict[doubter]
        else:
            await channel.send(f"Doubters win!")
            totalBelieveAmount = 0
            for believer in believersDict:
                totalBelieveAmount += believersDict[believer]
            totalDoubtAmount = 0
            for doubter in doubtersDict:
                totalDoubtAmount += doubtersDict[doubter]
            for doubter in doubtersDict:
                print(f"doubterID: {doubter}")
                user = await bot.fetch_user(doubter)
                payoutRate = totalBelieveAmount / totalDoubtAmount
                winnings = math.floor(doubtersDict[doubter] * payoutRate)
                betters[doubter] += winnings
                await channel.send(f"{user.name} has won {winnings} points!")
            for believer in believersDict:
                betters[believer] -= believersDict[believer]
    resetBetVariables()
    await saveBetters()
    
async def predict(user, amount, isBelieve):
    global believersDict
    global doubtersDict
    if isBelieve:
        believersDict[user.id] = amount
    else:
        doubtersDict[user.id] = amount
    if user.id not in activeBetters:
        activeBetters.append(user.id)

async def saveBetters():
    with open(bettersFile, 'wb') as handle:
        pickle.dump(betters, handle, protocol=pickle.HIGHEST_PROTOCOL)

def loadBetters():
    global betters
    with open(bettersFile, 'rb') as handle:
        betters = pickle.load(handle)
        print(f'Successfully loaded betters from {bettersFile}')
        
async def saveTimeout():
    with open(timeoutFile, 'wb') as handle:
        pickle.dump(bettingTime, handle, protocol=pickle.HIGHEST_PROTOCOL)
        
def loadTimeout():
    global bettingTime
    with open(timeoutFile, 'rb') as handle:
        bettingTime = pickle.load(handle)
        print(f'Successfully loaded bettingTime from {timeoutFile}: {bettingTime}')
        
def hasPermission(user):
    for role in user.roles:
        if role.name == 'Gambling Manager':
            return True
    return False

async def lockBet(channel, message):
    global isLocked
    isLocked = True
    await channel.send(message)

def resetBetVariables():
    global currentBet
    global betMessageID
    global isLocked
    global believersDict
    global doubtersDict
    believersDict = {}
    doubtersDict = {}
    currentBet = ""
    betMessageID = -1
    isLocked = False

async def refundBet(channel, message):
    resetBetVariables()
    await channel.send(message)
   
def checkForLock(reaction, user):
    return hasPermission(user) and str(reaction.emoji) == '🔒'

bot.run(TOKEN)
