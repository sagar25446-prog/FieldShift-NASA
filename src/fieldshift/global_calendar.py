"""Historical planting and harvest calendars, with purely calendar-based sequences."""
from dataclasses import dataclass
from datetime import date, timedelta
from functools import lru_cache
from itertools import permutations
import math
from pathlib import Path

import numpy as np

SOURCE = "https://sage.nelson.wisc.edu/data-and-models/datasets/crop-calendar-dataset/"


@dataclass(frozen=True)
class Calendar:
    name: str
    crop: str
    plant: int
    harvest: int


@lru_cache(maxsize=1)
def _grid():
    with np.load(Path(__file__).resolve().parents[2] / "data/global_calendar.npz", allow_pickle=False) as grid:
        return grid["crops"].tolist(), grid["half_days"]


def at_point(latitude: float, longitude: float) -> tuple[Calendar, ...]:
    if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
        raise ValueError("Coordinates are outside the world map.")
    row = min(359, math.floor((90 - latitude) * 2))
    col = math.floor((longitude + 180) * 2) % 720
    names, grid = _grid()
    results = []
    for name, (plant, harvest) in zip(names, grid[:, :, row, col]):
        if plant and harvest:
            crop = name.partition(".Winter")[0].partition(".2")[0].replace(".", " ")
            label = name.replace(".Winter", " (winter)").replace(".2", " (second season)").replace(".", " ")
            if name in {"Wheat", "Oats", "Barley"}:
                label += " (spring)"
            results.append(Calendar(label, crop, (int(plant)+1)//2, (int(harvest)+1)//2))
    return tuple(results)


def month_name(day: int) -> str:
    return (date(2001, 1, 1) + timedelta(days=(day-1) % 365)).strftime("%b")


def sequences(calendars: tuple[Calendar, ...], start_month: int, count: int):
    """Earliest non-overlapping typical dates on a repeating 365-day calendar."""
    if count not in (2, 3):
        raise ValueError("Choose two or three crops.")
    first_day = date(2001, start_month, 1).timetuple().tm_yday
    options = []
    for sequence in permutations(calendars, count):
        if len({item.crop for item in sequence}) != count:
            continue
        ready = first_day
        slots = []
        for item in sequence:
            plant = item.plant + 365 * max(0, math.ceil((ready - item.plant) / 365))
            harvest = plant + (item.harvest - item.plant) % 365
            slots.append((item.name, plant, harvest))
            ready = harvest + 1
        options.append(tuple(slots))
    return sorted(options, key=lambda slots: (slots[-1][2], slots))
