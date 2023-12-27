import json

import click
from click.shell_completion import CompletionItem
from termcolor import colored
from functools import cmp_to_key

SAVE_FILE_NAME = "save.json"
STATE_FILE_NAME = "state.json"


class Decks:
    def __init__(
        self,
        infection: list[list[str]],
        discard: list[str],
        card_to_color: dict[str, str],
    ) -> None:
        self.infection_deck: list[list[str]] = infection
        self.discard_pile: list[str] = discard
        self.card_to_color: dict[str, str] = card_to_color

    @staticmethod
    def load(file_name: str) -> "Decks":
        try:
            with open(file_name, "rb") as file:
                obj = json.load(file)
        except FileNotFoundError:
            obj = {}

        return Decks(
            obj.get("infection", [[]]),
            obj.get("discard", []),
            obj.get("card_to_color", {}),
        )

    def save(self, file_name: str) -> None:
        with open(file_name, "w") as file:
            json.dump(
                {
                    "infection": self.infection_deck,
                    "discard": self.discard_pile,
                    "card_to_color": self.card_to_color,
                },
                file,
                indent=4,
            )

    def _print_formatting(self, lis: [str]) -> [str]:
        card_counts = {}
        reprs = []
        for card in lis:
            card_counts[card] = card_counts.get(card, 0) + 1
            # Sort by count, then name.
            card_tuples = [(v, k) for k, v in card_counts.items()]
            card_tuples.sort(key=cmp_to_key(self.compare))
            reprs = []
            for count, card in card_tuples:
                name = f"x{count} " + self._format_name(card)
                reprs.append(name)
        return reprs

    def print(self) -> None:
        print("Infection decks (topmost first):")
        for i, deck in enumerate(self.infection_deck):
            if len(deck) == 0:
                continue

            deck_names = self._print_formatting(deck)
            print(f"deck {i+1}: {len(deck)}")
            for name in deck_names:
                print(f"\t{name}")

        discards = self._print_formatting(self.discard_pile)
        print(f"\nDiscard: {len(self.discard_pile)}")
        for name in discards:
            print(f"\t{name}")

    def compare(self, item1, item2):
        count1 = item1[0]
        count2 = item2[0]

        if count1 > count2:
            return -1

        elif count2 > count1:
            return 1
        else:
            name1 = item1[1]
            name2 = item2[1]
            if name1 > name2:
                return 1
            elif name2 > name1:
                return -1
            else:
                return 0

    def _format_name(self, card: str) -> str:
        if card in self.card_to_color:
            return colored(card, on_color=f"on_{self.card_to_color[card]}")
        return card

    def draw(self, card: str) -> None:
        if card in self.infection_deck[0]:
            self.infection_deck[0].remove(card)
            if not self.infection_deck[0]:
                self.infection_deck.pop(0)
        self.discard_pile.append(card)
        self.discard_pile.sort()

    def reshuffle_discard(self) -> None:
        if len(self.discard_pile) > 0:
            self.infection_deck.insert(0, list(self.discard_pile))
            self.discard_pile = []

    def remove_discard(self, card: str) -> None:
        if card in self.discard_pile:
            self.discard_pile.remove(card)

    def mark_card(self, card: str, color: str) -> None:
        self.card_to_color[card] = color

    def unmark_card(self, card: str) -> None:
        del self.card_to_color[card]


class AliasedGroup(click.Group):
    def get_command(self, ctx, cmd_name):
        shorthands = {
            "p": "print",
            "dc": "draw_card",
            "rd": "remove_discard",
        }
        if cmd_name in shorthands:
            cmd_name = shorthands[cmd_name]
        return click.Group.get_command(self, ctx, cmd_name)


@click.command(cls=AliasedGroup)
def cli():
    # This is the root command.
    pass


class CardNameType(click.ParamType):
    name = "cards"

    def shell_complete(self, ctx, param, incomplete):
        # Implements shell completion for cities.
        # Requires a recent version of bash and adding the following to your .bashrc:
        # $ eval "$(_PANDEMIC_HELPER_COMPLETE=bash_source pandemic_helper)"
        try:
            with open("cards.txt") as f:
                cities = [c.strip() for c in f.readlines() if len(c) > 0]
        except FileNotFoundError:
            cities = []
        return [
            CompletionItem(name.lower().replace(" ", "_"))
            for name in cities
            if name.lower().replace(" ", "_").startswith(incomplete)
        ]


@cli.command("print")
def _print() -> None:
    decks = Decks.load(STATE_FILE_NAME)
    decks.print()


@cli.command("draw_card")
@click.argument("cards", type=CardNameType(), nargs=-1)
def draw_card(cards: [str]) -> None:
    decks = Decks.load(STATE_FILE_NAME)
    for card in cards:
        card = card.replace("_", " ").strip().lower()
        decks.draw(card)
    decks.save(STATE_FILE_NAME)
    decks.print()


@cli.command("remove_discard")
@click.argument("cards", type=CardNameType(), nargs=-1)
def remove_discard(cards: list[str]) -> None:
    decks = Decks.load(STATE_FILE_NAME)
    for card in cards:
        card = card.replace("_", " ").strip().lower()
        decks.remove_discard(card)
    decks.save(STATE_FILE_NAME)
    decks.print()


@cli.command()
def shuffle() -> None:
    decks = Decks.load(STATE_FILE_NAME)
    decks.reshuffle_discard()
    decks.save(STATE_FILE_NAME)
    decks.print()


@cli.command()
@click.option("--color", "-c", required=True, help="red|yellow|none")
@click.argument("cards", type=CardNameType(), nargs=-1)
def mark(color: str, cards: list[str]) -> None:
    decks = Decks.load(STATE_FILE_NAME)
    for card in cards:
        card = card.replace("_", " ").strip().lower()
        if color.lower() == "none":
            decks.unmark_card(card)
        else:
            decks.mark_card(card, color)
    decks.save(STATE_FILE_NAME)
    decks.print()


@cli.command()
def save() -> None:
    decks = Decks.load(STATE_FILE_NAME)
    decks.save(SAVE_FILE_NAME)
    decks.print()


@cli.command()
def load() -> None:
    decks = Decks.load(SAVE_FILE_NAME)
    decks.save(STATE_FILE_NAME)
    decks.print()


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
