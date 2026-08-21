"""
text_humanizer.py
Converts raw written script text (numbers, currency, years, percentages,
abbreviations, symbols) into 100% natural, human-spoken English for TTS engines.
"""

import re

# ── Base Number Words ────────────────────────────────────────────────────────
_ONES = ["", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine",
         "ten", "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen",
         "seventeen", "eighteen", "nineteen"]
_TENS = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]
_ORDINALS = {
    1: "first", 2: "second", 3: "third", 4: "fourth", 5: "fifth",
    6: "sixth", 7: "seventh", 8: "eighth", 9: "ninth", 10: "tenth",
    11: "eleventh", 12: "twelfth", 13: "thirteenth", 14: "fourteenth",
    15: "fifteenth", 16: "sixteenth", 17: "seventeenth", 18: "eighteenth",
    19: "nineteenth", 20: "twentieth", 30: "thirtieth", 40: "fortieth",
    50: "fiftieth", 60: "sixtieth", 70: "seventieth", 80: "eightieth",
    90: "ninetieth", 100: "hundredth", 1000: "thousandth", 1000000: "millionth"
}


def int_to_words(n: int) -> str:
    """Converts integer (0 to 999,999,999,999) into spoken words."""
    if n == 0:
        return "zero"
    if n < 0:
        return "negative " + int_to_words(-n)

    parts = []
    
    if n >= 1_000_000_000_000:
        trillions = n // 1_000_000_000_000
        n %= 1_000_000_000_000
        parts.append(f"{int_to_words(trillions)} trillion")
        
    if n >= 1_000_000_000:
        billions = n // 1_000_000_000
        n %= 1_000_000_000
        parts.append(f"{int_to_words(billions)} billion")

    if n >= 1_000_000:
        millions = n // 1_000_000
        n %= 1_000_000
        parts.append(f"{int_to_words(millions)} million")

    if n >= 1_000:
        thousands = n // 1_000
        n %= 1_000
        parts.append(f"{int_to_words(thousands)} thousand")

    if n >= 100:
        hundreds = n // 100
        n %= 100
        parts.append(f"{_ONES[hundreds]} hundred")

    if n >= 20:
        tens = n // 10
        units = n % 10
        if units:
            parts.append(f"{_TENS[tens]}-{_ONES[units]}")
        else:
            parts.append(_TENS[tens])
    elif n > 0:
        parts.append(_ONES[n])

    return " ".join(parts)


def decimal_to_words(num_str: str) -> str:
    """Converts decimal numbers like '3.14' to 'three point one four'."""
    if "." not in num_str:
        try:
            return int_to_words(int(num_str))
        except ValueError:
            return num_str
            
    int_part, dec_part = num_str.split(".", 1)
    int_word = int_to_words(int(int_part)) if int_part else "zero"
    
    dec_words = []
    for digit in dec_part:
        if digit.isdigit():
            dec_words.append(_ONES[int(digit)] if int(digit) != 0 else "zero")
        else:
            dec_words.append(digit)
            
    return f"{int_word} point {' '.join(dec_words)}"


def year_to_words(year: int) -> str:
    """Converts 4-digit years like 1999 -> 'nineteen ninety-nine', 2000 -> 'two thousand', 2024 -> 'twenty twenty-four'."""
    if year == 2000:
        return "two thousand"
    if 2001 <= year <= 2009:
        return f"two thousand {_ONES[year % 100]}"
    if 2010 <= year <= 2099:
        century = year // 100
        end = year % 100
        if end < 10:
            return f"twenty oh {_ONES[end]}"
        return f"{int_to_words(century)} {int_to_words(end)}"
    if 1000 <= year <= 1999:
        century = year // 100
        end = year % 100
        if end == 0:
            return f"{_ONES[century]} hundred"
        if end < 10:
            return f"{_ONES[century]} oh {_ONES[end]}"
        return f"{int_to_words(century)} {int_to_words(end)}"
    return int_to_words(year)


def ordinal_to_words(ord_str: str) -> str:
    """Converts '1st' -> 'first', '2nd' -> 'second', '21st' -> 'twenty-first'."""
    m = re.match(r"^(\d+)(st|nd|rd|th)$", ord_str.lower())
    if not m:
        return ord_str
    num = int(m.group(1))
    if num in _ORDINALS:
        return _ORDINALS[num]
    
    last_two = num % 100
    if 10 <= last_two <= 20:
        base = int_to_words(num - last_two)
        ord_word = _ORDINALS.get(last_two, f"{int_to_words(last_two)}th")
        return f"{base} {ord_word}".strip()
    
    last_one = num % 10
    tens_part = (num // 10) * 10
    tens_words = int_to_words(tens_part)
    unit_ord = _ORDINALS.get(last_one, "th")
    return f"{tens_words}-{unit_ord}"


def humanize_text(text: str) -> str:
    """
    Main normalizer: translates numbers, currencies, dates, abbreviations,
    and symbols into crystal-clear human-spoken English.
    """
    if not text:
        return ""

    # 1. Clean bracketed instructions, markdown bold/italics
    text = re.sub(r"\*\*|\*", "", text)
    text = re.sub(r"__|_", "", text)
    text = re.sub(r"#+\s*", "", text)

    # 2. Key phrases & symbols with numbers
    text = re.sub(r"\b24\s*/\s*7\b", "twenty-four seven", text)
    text = re.sub(r"\b(\d+)\s*/\s*(\d+)\b", lambda m: f"{int_to_words(int(m.group(1)))} out of {int_to_words(int(m.group(2)))}", text)

    # 3. Currency with multipliers (e.g., $2.5M, $10B, $34T, $500k, $100)
    mult_map = {"K": "thousand", "M": "million", "B": "billion", "T": "trillion"}
    curr_map = {"$": "dollars", "€": "euros", "£": "pounds", "₹": "rupees"}
    curr_single_map = {"$": "dollar", "€": "euro", "£": "pound", "₹": "rupee"}

    def _sub_currency_short(m):
        sym, num, mult = m.group(1), m.group(2), m.group(3).upper()
        curr = curr_map.get(sym, "dollars")
        mult_word = mult_map.get(mult, "thousand")
        return f"{decimal_to_words(num)} {mult_word} {curr}"

    text = re.sub(r"([$€£₹])\s*(\d+(?:\.\d+)?)\s*([KMBTkmbt])\b", _sub_currency_short, text)

    def _sub_currency_full(m):
        sym, num = m.group(1), m.group(2).replace(",", "")
        curr = curr_map.get(sym, "dollars")
        if "." in num:
            return f"{decimal_to_words(num)} {curr}"
        val = int(num)
        curr_word = curr_single_map.get(sym, "dollar") if val == 1 else curr
        return f"{int_to_words(val)} {curr_word}"

    text = re.sub(r"([$€£₹])\s*(\d[\d,]*(?:\.\d+)?)", _sub_currency_full, text)

    # 4. Percentages (e.g., 50% -> fifty percent, 7.5% -> seven point five percent)
    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", lambda m: f"{decimal_to_words(m.group(1))} percent", text)

    # 5. Multipliers (e.g., 10x -> ten times, 2X -> two times)
    text = re.sub(r"\b(\d+)[xX]\b", lambda m: f"{int_to_words(int(m.group(1)))} times", text)

    # 6. Ordinals (1st, 2nd, 3rd, 4th, 21st)
    text = re.sub(r"\b(\d+)(st|nd|rd|th)\b", lambda m: ordinal_to_words(m.group(0)), text, flags=re.IGNORECASE)

    # 7. Decades and Centuries (e.g., 1800s -> eighteen hundreds, 1990s -> nineteen nineties, 2000s -> two thousands)
    def _sub_decades(m):
        y = int(m.group(1))
        if y == 2000: return "two thousands"
        if y == 1990: return "nineteen nineties"
        if y == 1980: return "nineteen eighties"
        if y == 1970: return "nineteen seventies"
        if y % 100 == 0:
            return f"{int_to_words(y // 100)} hundreds"
        return f"{year_to_words(y)}s"

    text = re.sub(r"\b(1\d{3}|20\d{2})s\b", _sub_decades, text)

    # 8. 4-Digit Years preceded by prepositions (e.g., In 1999, In 2024, Between 1914 and 1918)
    def _sub_years(m):
        prefix = m.group(1)
        y = int(m.group(2))
        return f"{prefix}{year_to_words(y)}"

    text = re.sub(r"\b(in |year |since |by |from |until |between |to )\s*(1[5-9]\d{2}|20\d{2})\b", _sub_years, text, flags=re.IGNORECASE)

    # 9. Decimals (e.g., 3.14 -> three point one four)
    text = re.sub(r"\b\d+\.\d+\b", lambda m: decimal_to_words(m.group(0)), text)

    # 10. Standard numbers with commas or standalone digits (e.g., 1,000,000 -> one million, 2000 -> two thousand)
    def _sub_general_numbers(m):
        raw = m.group(0).replace(",", "")
        n = int(raw)
        if 1900 <= n <= 2099 and n != 2000 and len(raw) == 4:
            return year_to_words(n)
        return int_to_words(n)

    text = re.sub(r"\b\d[\d,]*\b", _sub_general_numbers, text)

    # 11. Common Acronyms, Abbreviations & Special Symbols
    replacements = [
        (r"\s*&\s*", " and "),
        (r"\s*@\s*", " at "),
        (r"\bvs\.?", "versus"),
        (r"\be\.?g\.?,?", "for example"),
        (r"\bi\.?e\.?,?", "that is"),
        (r"\betc\.?", "et cetera"),
        (r"\bw/\b", "with"),
        (r"\bw/o\b", "without"),
        (r"\b#(\d+)\b", r"number \1"),
        (r"\bkm/h\b", "kilometers per hour"),
        (r"\bmph\b", "miles per hour"),
        (r"°C\b", " degrees Celsius"),
        (r"°F\b", " degrees Fahrenheit"),
        (r"\bAI\b", "A.I."),
        (r"\bCEO\b", "C.E.O."),
        (r"\bUSA\b", "U.S.A."),
        (r"\bUS\b", "U.S."),
        (r"\bUSD\b", "U.S. dollars"),
        (r"\bFed\b", "Federal Reserve"),
    ]

    for pat, rep in replacements:
        text = re.sub(pat, rep, text, flags=re.IGNORECASE)

    # Collapse repeated spaces
    text = re.sub(r"\s+", " ", text).strip()
    return text
