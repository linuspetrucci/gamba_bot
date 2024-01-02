import re


def convert_chance(chance: str) -> float | None:
    float_chance = 0
    try:
        float_chance = float(chance)
    except ValueError:
        if re.compile('[0-9]+/[0-9]+').fullmatch(chance):
            split_fraction = chance.split('/')
            float_chance = int(split_fraction[0])/int(split_fraction[1])
        elif re.compile('[1-9][0-9]%|[1-9]%').fullmatch(chance):
            print(int(chance.strip('%')))
            float_chance = int(chance.strip('%'))/100
    if float_chance >= 1 or float_chance <= 0:
        return None
    return float_chance
