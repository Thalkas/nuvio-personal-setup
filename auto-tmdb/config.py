GENRES_MOVIES = {
    "Akcja": 28,
    "Animacja": 16,
    "Dokumentalny": 99,
    "Dramat": 18,
    "Familijny": 10751,
    "Fantasy": 14,
    "Historyczny": 36,
    "Horror": 27,
    "Komedia": 35,
    "Kryminał": 80,
    "Muzyczny": 10402,
    "Przygodowy": 12,
    "Romans": 10749,
    "Sci-Fi": 878,
    "Tajemnica": 9648,
    "Thriller": 53,
    "Western": 37,
    "Wojenne": 10752,
}

ADDITIONAL_GENRES_MOVIES = {
    "Bollywood": 355622,
    "Komedia Romantyczna": 9799,
    "Thriller Szpiegowski": 250808,
}

GENRES_SERIES = {
    "Akcji i Przygodowe": 10759,
    "Animacja": 16,
    "Dokumentalny": 99,
    "Dramat": 18,
    "Dziecięcy": 10762,
    "Familijny": 10751,
    "Komedia": 35,
    "Kryminał": 80,
    "Sci-Fi i Fantasy": 10765,
    "Tajemnica": 9648,
    "Thriller": 53,
    "Western": 37,
    "Wojenne i Polityczne": 10768,
}

ADDITIONAL_GENRES_SERIES = {
    "Historyczny": 36,
    "Horror": 3133,
    "Muzyczny": 10402,
    "Romans": 9840,
}

# Definiujemy gatunki TV do wykluczenia (Reality, Talk Show, News, Soap, Game Show)
EXCLUDE_GENRES = {
    "reality": 10764,
    "talk_show": 10767,
    "news": 10763,
    "soap": 10766,
    "game_show": 10762
}

# Definiujemy słowa kluczowe do wykluczenia (Stand-up, Reality TV, Variety Show)
EXCLUDE_KEYWORDS = {
    "stand-up": 9716,
    "reality_tv": 210024,
    "variety_show": 180547
}

PROVIDERS = {
    "Netflix": 8,
    "HBO Max": 1899,
    "Disney Plus": 337,
    "Prime Video": 119,
    "Apple TV": 350,
    "SkyShowTime": 1773,
}

DECADES = {
    "Lata 20": ("2020-01-01", "2029-12-31"),
    "Lata 10": ("2010-01-01", "2019-12-31"),
    "Lata 00": ("2000-01-01", "2009-12-31"),
    "Lata 90": ("1990-01-01", "1999-12-31"),
    "Lata 80": ("1980-01-01", "1989-12-31"),
    "Lata 70": ("1970-01-01", "1979-12-31"),
    "Lata 60": ("1960-01-01", "1969-12-31"),
    "Lata 50+": ("1900-01-01", "1959-12-31"),
}

LANGUAGES = {
    # --- EUROPA ---
    # SŁOWIAŃSKIE
        "Polskie": "pl",
        "Czeskie": "cs",
        "Słowackie": "sk",
        "Chorwackie": "hr",
        "Węgierskie": "hu",
    # ROMAŃSKIE
        "Włoskie": "it",
        "Hiszpańskie": "es",
        "Francuskie": "fr",
    # GERMAŃSKIE
        "Niemieckie": "de",     
        "Brytyjskie": "en",       # Język angielski, kraj GB
    # SKANDYNAWSKIE
        "Norweskie": "no",
        "Szweckie": "sv",
        "Duńskie": "da",
    # --- AZJA ---
        "Koreańskie": "ko",       # Ogromny hit ostatnich lat (K-Dramas, thrillery)
        "Japońskie": "ja",        # Klasyczne kino japońskie oraz Anime
        "Chińskie": "zh",         # W tym produkcje z Hongkongu i Tajwanu
        "Indyjskie": "hi",        # Bollywood i inne regiony Indii
    # --- AMERYKA ŁACIŃSKA i AUSTRALIA ---
        "Brazylijskie": "pt",     # Język portugalski, kraj BR
        "Meksykańskie": "es",     # Język hiszpański, kraj MX (np. świetne dramaty i kryminały)
        "Australijskie": "en",     # Język angielski, kraj AU
    # INNE
        "Tureckie": "tr"  
}
