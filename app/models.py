from dataclasses import dataclass, field
from typing import List

@dataclass
class Character:
    name: str
    description: str = ""
    color: str = ""
    texts: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

@dataclass
class Place:
    name: str
    description: str = ""
    texts: List[str] = field(default_factory=list)
    images: List[str] = field(default_factory=list)

@dataclass
class Event:
    title: str
    description: str = ""
    start_date: str = ""
    end_date: str = ""
    images: List[str] = field(default_factory=list)
    characters: List[str] = field(default_factory=list)
    places: List[str] = field(default_factory=list)
