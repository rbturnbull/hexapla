import re


def read_int(string):
    return int(re.sub("[^0-9]", "", string))

book_names = [
    None,
    "Genesis",
    "Exodus",
    "Leviticus",
    "Numbers",
    "Deuteronomy",
    "Joshua",
    "Judges",
    "Ruth",
    "1 Samuel",
    "2 Samuel",
    "1 Kings",
    "2 Kings",
    "1 Chronicles",
    "2 Chronicles",
    "Ezra",
    "Nehemiah",
    "Esther",
    "Job",
    "Psalms",
    "Proverbs",
    "Ecclesiastes",
    "Song of Solomon",
    "Isaiah",
    "Jeremiah",
    "Lamentations",
    "Ezekiel",
    "Daniel",
    "Hosea",
    "Joel",
    "Amos",
    "Obadiah",
    "Jonah",
    "Micah",
    "Nahum",
    "Habakkuk",
    "Zephaniah",
    "Haggai",
    "Zechariah",
    "Malachi",
    "Matthew",
    "Mark",
    "Luke",
    "John",
    "Acts",
    "Romans",
    "1 Corinthians",
    "2 Corinthians",
    "Galatians",
    "Ephesians",
    "Philippians",
    "Colossians",
    "1 Thessalonians",
    "2 Thessalonians",
    "1 Timothy",
    "2 Timothy",
    "Titus",
    "Philemon",
    "Hebrews",
    "James",
    "1 Peter",
    "2 Peter",
    "1 John",
    "2 John",
    "3 John",
    "Jude",
    "Revelation",
    # LXX
    '1 Esdras',
    'Wisdom of Solomon',
    'Sirach Prologue',
    'Sirach',
    'Judith',
    'Tobit',
    'Baruch',
    'Epistle of Jeremiah',
    'Susanna',
    'Bel and the Dragon',
    '1 Maccabees',
    '2 Maccabees',
    '3 Maccabees',
    '4 Maccabees',
    'Psalms of Solomon',
    '1 Enoch',
    'Odes',

]
book_abbreviations = [
    None,
    "Gen",
    "Ex",
    "Lev",
    "Nu",
    "Deut",
    "Josh",
    "Jdg",
    "Ru",
    "1Sa",
    "2Sa",
    "1Ki",
    "2Ki",
    "1Chr",
    "2Chr",
    "Ez",
    "Neh",
    "Est",
    "Job",
    "Ps",
    "Pr",
    "Ecc",
    "Song",
    "Isa",
    "Jer",
    "Lam",
    "Ez",
    "Da",
    "Ho",
    "Jl",
    "Am",
    "Ob",
    "Jon",
    "Mic",
    "Nah",
    "Hab",
    "Zep",
    "Hag",
    "Zec",
    "Mal",
    "Mt",
    "Mk",
    "Lk",
    "Jn",
    "Acts",
    "Ro",
    "1Co",
    "2Co",
    "Ga",
    "Eph",
    "Ph",
    "Col",
    "1Th",
    "2Th",
    "1Tim",
    "2Tim",
    "Titus",
    "Philem",
    "Heb",
    "Jas",
    "1Pe",
    "2Pe",
    "1Jn",
    "2Jn",
    "3Jn",
    "Jud",
    "Rev",
    '1Esd',
    'Wis',
    'Sirpro',
    'Sir',
    'Judith',
    'Tob',
    'Bar',
    'Epj',
    'Sus',
    'Bel',
    '1Mac',
    '2Mac',
    '3Mac',
    '4Mac',
    'Pss',
    '1En',
    'Odes',
]

book_abbreviations_alternate = {
    "Phlm": "Philemon",
    "Phm": "Philemon",
    "1Kgs": "1 Kings",
    "2Kgs": "2 Kings",
    "2Th": "2 Thessalonians",
    "2T": "2 Timothy",
    "2J": "2 John",
    "3J": "3 John",
    "Jd": "Jude",
    "Ap": "Revelation",
    "Mc": "Mark",
    "L": "Luke",
    "Php": "Philippians",
    "Tt": "Titus",
    "1Pt": "1 Peter",
    "2Pt": "2 Peter",
    "R": "Romans",
}


def get_book_id(name):
    name = name.title()
    if name in book_names:
        return book_names.index(name)

    if name in book_abbreviations:
        return book_abbreviations.index(name)

    if name in book_abbreviations_alternate:
        return book_names.index(book_abbreviations_alternate[name])

    for index, book_name in enumerate(book_names[1:]):
        if book_name.startswith(name) or book_name.replace(" ", "").startswith(name):
            return index + 1

    return None

def try_book_and_number(verse_ref):
    matches = re.match(r"(\d*\s*[a-zA-Z]+)[\s\.]*(\d+)$", verse_ref)
    if matches:
        book_id = get_book_id(matches.group(1))  # the pattern needs at least one letter, so a name is always there
        number = read_int(matches.group(2))

        return book_id, number
    return None, None


def single_chapter_book_names():
    return ["Philemon", "Jude", "2 John", "3 John", "Obadiah"]

def single_chapter_book_ids():
    return [book_names.index(book_name) for book_name in single_chapter_book_names()]


def components_from_verse_ref(verse_ref):
    verse_ref = verse_ref.strip()
    
    # First try BxKxV format used in some TEI files.
    m = re.match(r"B(\d*)K(\d*)V(\d*)", verse_ref)
    if m:
        book = int(m.group(1)) + 39  # number of books in OT
        chapter = int(m.group(2))
        verse_num = int(m.group(3))
        return book, chapter, verse_num

    matches = re.match(r"(.+)[:\.](\d+)", verse_ref)
    if not matches:
        if verse_ref.strip().isdigit():
            return None, None, read_int(verse_ref)

        # Try single chapter books
        book_id, verse = try_book_and_number(verse_ref)
        if verse:
            if book_id in single_chapter_book_ids():
                return book_id, 1, verse

        raise Exception(f"Cannot interpret verse: {verse_ref}")

    components = [matches.group(1), matches.group(2)]

    verse = read_int(components[1])

    book_id, chapter = try_book_and_number(components[0])
    if chapter:
        return book_id, chapter, verse

    if components[0].strip().isdigit():
        book_id = None
        chapter = read_int(components[0])
        return book_id, chapter, verse

    raise Exception("Cannot interpret verse %s" % (verse_ref))


def read_verse_ref(verse_ref) -> tuple[str, str]:
    book_id, chapter, verse = components_from_verse_ref(verse_ref)
    book_name = book_names[book_id] if book_id is not None else ""

    book_id = book_id - 39 if book_id is not None else None  # Convert to 0-indexed
    standard = f"B{book_id:02d}K{chapter:02d}V{verse:02d}"

    explicit_name = f"{book_name} {chapter}:{verse}" if book_name else ""
    return standard, explicit_name