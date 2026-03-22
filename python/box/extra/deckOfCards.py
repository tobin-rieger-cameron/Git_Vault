import collections
from random import choice
from random import shuffle

Card = collections.namedtuple('Card', ['rank','suit'])

class FrenchDeck:
    ranks = [str(n) for n in range(2, 11)] + list('JQKA')
    suits = 'spades diamonds clubs hearts'.split()

    def __init__(self):
        self._cards = [Card(rank, suit) for suit in self.suits
                       for rank in self.ranks]

    def __len__(self):
        return len(self._cards)

    def __str__(self):
        return '\n'.join(f'{card.rank} of {card.suit.capitalize()}' for card in self._cards)

    def __getitem__(self, position):
        return self._cards[position]

    def __setitem__(self, position, value):
        self._cards[position] = value


deck = FrenchDeck()

def set_card(deck, position, card):
    deck._[position] = card
#for card in deck:
#    print(f"{card.rank} of {card.suit}")
#print(deck)

#print("Deck length: ", len(deck))
#print("First card: ", deck[0])
#print("Second card: ", deck[1])
#print("Choose a random card: ", choice(deck))
#print("Top three cards: ", deck[:3])
#print("Just the Aces: ", deck[12::13]) # dumb way

#for card in reversed(deck): 
#    print(card)
#print(Card('Q', 'hearts') in deck)

suit_values = dict(spades=3, hearts=2, diamonds=1, clubs=0)

def suit_first(card):
    suit_value = suit_values[card.suit]
    rank_value = FrenchDeck.ranks.index(card.rank)
    return (suit_value, rank_value)

def spades_high(card):
    rank_value = FrenchDeck.ranks.index(card.rank)
    return rank_value * len(suit_values) + suit_values[card.suit]

for card in sorted(deck, key=suit_first):
#    print(card)
    print(f"{card.rank} of {card.suit}")

deck.__setitem__ = set_card
shuffle(deck)
print(deck)
