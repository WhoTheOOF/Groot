import asyncio
import random

import discord
from discord.ext import commands
from utils.chat_formatting import hyperlink as link
from utils.useful import Embed, convert_to_int


class Blackjack(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.data = bot.data
        self.faces = ["A", "2", "3", "4", "5", "6", "7", "8", "9", "10", "J", "Q", "K"]
        self.values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]
        self.suits = ["spades", "hearts", "diamonds", "clubs"]

    @commands.command(name="play_blackjack")
    async def play_blackjack(self, ctx, amount):
        wallet = await self.data.get_data(ctx.author.id)
        if wallet >= 10000000:
            raise commands.BadArgument(
                f"{ctx.author.mention} You are too rich to gamble!"
            )
        boost = round(self.bot.cache["users"][ctx.author.id]["boost"], 2)
        if wallet == 0:
            raise commands.BadArgument(
                f"{ctx.author.mention} You have no coins to gamble with."
            )
        amount = await convert_to_int(amount, 500000)
        if amount > 500000:
            raise commands.BadArgument(
                f"{ctx.author.mention} You can't slots more than ⛻500,000 coins"
            )
        if amount > wallet:
            if amount != 500000:
                raise commands.BadArgument(
                    f"{ctx.author.mention} You don't have that much coins!"
                )
            else:
                amount = wallet
        ctx.amount = amount
        ctx.wallet = wallet
        stood = False
        won = None
        deck = [
            {"face": face, "suit": suit} for suit in self.suits for face in self.faces
        ]
        cards = {
            "user_cards": [self.deal(deck), self.deal(deck)],
            "bot_cards": [self.deal(deck), self.deal(deck)],
        }

        while (
            self.total_value(cards["user_cards"]) >= 21
            or self.total_value(cards["bot_cards"]) >= 21
        ):
            cards = {
                "user_cards": [self.deal(deck), self.deal(deck)],
                "bot_cards": [self.deal(deck), self.deal(deck)],
            }

        fail = 0

        while fail < 2:
            status = self.score(stood, cards["user_cards"], cards["bot_cards"])
            if not isinstance(status, int):
                result = status["result"]
                if result is True:
                    await self.data.update_data(ctx.author.id, round(amount * boost))
                elif result is False:
                    await self.data.update_data(ctx.author.id, -amount)
                em = await self.end(ctx, cards, status)
                return await ctx.send(embed=em)
            else:
                try:
                    await ctx.send(
                        content="What do you want to do?\nType `h` to hit, `s` to stand, `e` to end.",
                        embed=self.start(ctx, cards),
                    )
                    msg = await self.bot.wait_for(
                        "message",
                        timeout=15,
                        check=lambda m: m.author == ctx.author
                        and m.channel == ctx.channel,
                    )
                except asyncio.TimeoutError:
                    raise commands.BadArgument("Blackjack game ended due to timeout.")
                else:
                    msg = msg.content.lower()[0]
                    if msg == "h":
                        cards["user_cards"].append(self.deal(deck))
                    elif msg == "s":
                        while self.total_value(cards["bot_cards"]) < 17:
                            await self.dealersTurn(ctx, cards, deck)
                        stood = True

                    elif msg == "e":
                        await self.data.update_data(ctx.author.id, -round(0.5 * amount))
                        return await ctx.maybe_reply(
                            "You ended the game. Half of your bet was lost."
                        )
                    else:
                        fail += 1
        await self.data.update_data(ctx.author.id, -round(0.5 * amount))
        return await ctx.maybe_reply(
            "You lost the game due to multiple invalid choices. Half of your bet was lost."
        )

    def deal(self, deck: list):
        random.shuffle(deck)
        card = deck.pop()
        return card

    @staticmethod
    def get_icon(suit):
        suit_dict = {"spades": "♠", "hearts": "♥", "diamonds": "♦", "clubs": "♣"}
        return suit_dict[suit]

    def value(self, card):
        return self.values[self.faces.index(card)]

    def total_value(self, cards):
        values = [card["face"] for card in cards]
        aces = values.count("A")
        if aces > 0:
            values = [i for i in values if i != "A"]

        total = sum([self.value(card) for card in values])
        if aces == len(values) == 2:
            aces_value = random.choice([2, 12])
        else:
            aces_value = aces * 1 if total >= 11 else aces * 11

        return total + aces_value if total >= 11 else total + aces_value

    def score(self, stood, user_cards, bot_cards):
        if self.total_value(user_cards) > 21:
            return {"result": False, "message": "You lose! Busted!"}
        elif self.total_value(bot_cards) > 21:
            return {"result": True, "message": "You win! Your opponent busted!"}
        elif self.total_value(user_cards) == 21:
            return {"result": True, "message": "You win! You have 21!"}
        elif self.total_value(bot_cards) == 21:
            return {
                "result": False,
                "message": "You lose! Your opponent reached 21 before you!",
            }
        elif self.total_value(user_cards) == self.total_value(bot_cards) and stood:
            return {"result": None, "message": "You tied with your opponent!"}
        elif self.total_value(user_cards) < 21 and len(user_cards) == 5:
            return {
                "result": True,
                "message": "You won! You took 5 cards without going over 21.",
            }
        elif self.total_value(bot_cards) < 21 and len(bot_cards) == 5:
            return {
                "result": False,
                "message": "You lose! Your opponent took 5 cards without going above 21.",
            }
        elif (bot_deck := self.total_value(bot_cards)) > (
            user_deck := self.total_value(user_cards)
        ) and stood:
            return {
                "result": False,
                "message": f"You lose! You have {user_deck}, Dealer has {bot_deck}.",
            }
        elif (user_deck := self.total_value(user_cards)) > (
            bot_deck := self.total_value(bot_cards)
        ) and stood:
            return {
                "result": True,
                "message": f"You won! You have {user_deck}, Dealer has {bot_deck}.",
            }
        else:
            return self.total_value(user_cards)

    def start(self, ctx, cards):
        user_cards_visual = "".join(
            [
                link(
                    f"**`{self.get_icon(card['suit'])} {card['face']}`** ",
                    discord.utils.oauth_url(812395879146717214),
                )
                for card in cards["user_cards"]
            ]
        )
        bot_cards_visual = [
            link(
                f"**`{self.get_icon(card['suit'])} {card['face']}`** ",
                discord.utils.oauth_url(812395879146717214),
            )
            for card in cards["bot_cards"]
        ]
        em = Embed()
        em.add_field(
            name=ctx.author.display_name,
            value=f"Cards - {user_cards_visual}\nValue - `{self.total_value(cards['user_cards'])}`",
        )
        em.add_field(
            name=self.bot.user.display_name,
            value=f"Cards - {bot_cards_visual[0]} `?`\nValue - ` ? `",
        )
        em.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        em.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        return em

    async def end(self, ctx, cards, kwargs: dict):
        result = kwargs.pop("result")
        message = kwargs.pop("message")
        message = "**{}**".format(message)
        color = 0x3CA374 if result is True else 0xF04D4B
        color = 0xFFCC33 if result is None else color
        ctx.amount = round(0.5 * ctx.amount) if result is None else ctx.amount
        won_or_lost = (
            f"won  **⛻{ctx.amount:,}**! "
            if result is True
            else f"lost **⛻{ctx.amount:,}**. "
        )
        ctx.amount = -ctx.amount if result is True else ctx.amount
        message += f"\nYou {won_or_lost}You now have {await self.data.get_data(ctx.author.id):,}"
        user_cards_visual = "".join(
            [
                link(
                    f"**`{self.get_icon(card['suit'])} {card['face']}`** ",
                    discord.utils.oauth_url(812395879146717214),
                )
                for card in cards["user_cards"]
            ]
        )
        bot_cards_visual = "".join(
            [
                link(
                    f"**`{self.get_icon(card['suit'])} {card['face']}`** ",
                    discord.utils.oauth_url(812395879146717214),
                )
                for card in cards["bot_cards"]
            ]
        )
        em = Embed(description=message, color=color)
        em.add_field(
            name=ctx.author.display_name,
            value=f"Cards - {user_cards_visual}\nValue - `{self.total_value(cards['user_cards'])}`",
        )
        em.add_field(
            name=self.bot.user.display_name,
            value=f"Cards - {bot_cards_visual}\nValue - `{self.total_value(cards['bot_cards'])}`",
        )
        em.set_author(name=ctx.author.display_name, icon_url=ctx.author.avatar_url)
        em.set_footer(text="K, Q, J = 10  |  A = 1 or 11")
        return em

    async def dealersTurn(self, ctx, cards, deck):
        if self.total_value(cards["user_cards"]) > 21:
            return await self.end(
                ctx, cards, self.score(True, cards["user_cards"], cards["bot_cards"])
            )

        if len(cards["bot_cards"]) < 5:
            if self.total_value(cards["bot_cards"]) < 17:
                cards["bot_cards"].append(self.deal(deck))


def setup(bot):
    bot.add_cog(Blackjack(bot))
