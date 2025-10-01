from dataclasses import dataclass #hämtar dekoratorn

@dataclass
class Character:
    name: str #dataklass med ett fält, för att hålla modellen enkel och tydlig

@dataclass
class Place:
    name: str #dataklass med ett fält, för att hålla modellen enkel och tydlig

@dataclass
class Event: #dataklass med tre fält
    title: str #rubriken på händelsen
    description: str #fri text
    date: str = "" #datum som sträng, valfritt default tom sträng

