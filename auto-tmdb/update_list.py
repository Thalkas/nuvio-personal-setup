import os
import datetime
import time
import requests

# Importowanie słowników z pliku config.py
from config import (
    GENRES_MOVIES,
    ADDITIONAL_GENRES_MOVIES,
    GENRES_SERIES,
    ADDITIONAL_GENRES_SERIES,
    PROVIDERS,
    DECADES,
    EXCLUDE_GENRES,
    EXCLUDE_KEYWORDS,
    LANGUAGES
)

# ==========================================
# KONFIGURACJA URUCHOMIENIA
# ==========================================
TMDB_API_TOKEN = os.environ.get("TMDB_API_TOKEN")
ACCOUNT_ID = os.environ.get("TMDB_ACCOUNT_ID")
REGION = "PL"
CURRENT_YEAR = datetime.datetime.now().year

# Prosta walidacja, aby program nie ruszył bez wymaganych kluczy
if not TMDB_API_TOKEN or not ACCOUNT_ID:
    raise ValueError(
        "Brak wymaganych zmiennych środowiskowych: TMDB_API_TOKEN lub TMDB_ACCOUNT_ID!"
    )

headers = {
    "Authorization": f"Bearer {TMDB_API_TOKEN}",
    "Content-Type": "application/json;charset=utf-8"
}

# ==========================================
# 1. SŁOWNIKI DANYCH
# ==========================================

# Plink Config.py
user_lists_cache = {}

# ==========================================
# FUNKCJE POMOCNICZE
# ==========================================
def fetch_user_lists():
    """Pobiera wszystkie listy użytkownika z API v4 i zapisuje do słownika {nazwa: id}."""
    global user_lists_cache
    url = f"https://api.themoviedb.org/4/account/{ACCOUNT_ID}/lists"
    page = 1
    user_lists_cache = {}
    
    while True:
        response = requests.get(url, headers=headers, params={"page": page})
        if response.status_code != 200:
            break
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
        for lst in results:
            user_lists_cache[lst["name"]] = lst["id"]
        if page >= data.get("total_pages", 1):
            break
        page += 1

def delete_all_my_lists():
    url = f"https://api.themoviedb.org/4/account/{ACCOUNT_ID}/lists"
    page = 1
    lists_to_delete = []

    print("Pobieranie listy Twoich list z TMDB...")
    while True:
        response = requests.get(url, headers=headers, params={"page": page})
        if response.status_code != 200:
            print(f"Błąd podczas pobierania list (Strona {page}): {response.status_code} - {response.text}")
            break
        
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
            
        for lst in results:
            lists_to_delete.append((lst["id"], lst["name"]))
            
        # Bezpieczniejsze sprawdzanie kolejnej strony
        total_pages = data.get("total_pages", 1)
        if page >= total_pages:
            break
        page += 1

    if not lists_to_delete:
        print("Nie znaleziono żadnych list do usunięcia na Twoim koncie.")
        return

    print(f"Znaleziono {len(lists_to_delete)} list. Rozpoczynam usuwanie...")
    
    for list_id, list_name in lists_to_delete:
        delete_url = f"https://api.themoviedb.org/4/list/{list_id}"
        print(f"Usuwanie: '{list_name}' (ID: {list_id})...")
        
        res = requests.delete(delete_url, headers=headers)
        if res.status_code in [200, 204]:
            print(f"-> Sukces: Usunięto '{list_name}'")
        else:
            # Ta linijka wyjaśni wszystko, jeśli TMDB odrzuci żądanie:
            print(f"-> BŁĄD! Kod: {res.status_code} | Powód: {res.text}")
        
        time.sleep(0.5)

def get_or_create_list(list_name):
    """Zwraca ID listy, tworząc ją najpierw, jeśli nie istnieje."""
    if list_name in user_lists_cache:
        return user_lists_cache[list_name]
    
    # Tworzenie nowej listy, jeśli cache jej nie zawiera
    url = "https://api.themoviedb.org/4/list"
    payload = {
        "name": list_name,
        "description": f"Automatyczna dynamiczna lista: {list_name}",
        "iso_639_1": "pl",
        "iso_3166_1": REGION,
        "public": False
    }
    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 201:
        new_id = response.json().get("id")
        user_lists_cache[list_name] = new_id
        print(f"Utworzono nową listę: '{list_name}'")
        return new_id
    else:
        print(f"Błąd podczas tworzenia listy '{list_name}': {response.text}")
        return None

def get_tmdb_list_items(list_name):
    """Pobiera elementy z istniejącej listy na TMDB i zwraca listę słowników typu [{'media_type': ..., 'media_id': ...}]."""
    # Sprawdzamy, czy lista w ogóle istnieje w naszym cache
    list_id = user_lists_cache.get(list_name)
    if not list_id:
        return []

    # API v4 pozwala na pobranie zawartości listy
    url = f"https://api.themoviedb.org/4/list/{list_id}"
    page = 1
    items = []

    while True:
        response = requests.get(url, headers=headers, params={"page": page})
        if response.status_code != 200:
            break
        
        data = response.json()
        results = data.get("results", [])
        if not results:
            break

        for item in results:
            items.append({
                "media_type": item.get("media_type"),
                "media_id": item.get("id")
            })

        if page >= data.get("total_pages", 1):
            break
        page += 1

    return items

def update_tmdb_list(list_name, items, sort_by=None, clear=False):
    """Aktualizuje listę, opcjonalnie czyszcząc ją i dodając WSZYSTKIE przekazane pozycje w paczkach po 20."""
    list_id = get_or_create_list(list_name)
    if not list_id:
        return

    # 1. Czyszczenie listy (API v3)
    if clear:
        print(f"Czyszczenie listy '{list_name}' przed dodaniem nowych pozycji...")
        clear_url = f"https://api.themoviedb.org/3/list/{list_id}/clear"
        res_clear = requests.post(clear_url, headers=headers, params={"confirm": "true"})
        if res_clear.status_code not in [200, 201]:
            print(f"Problem z czyszczeniem listy '{list_name}': {res_clear.text}")

    # 1.5. Sortowanie listy
    if not sort_by:
        # Jeśli nie przekazano parametru jawnie, wybieramy domyślne sortowanie po dacie
        if "Seriale" in list_name:
            sort_by = "first_air_date.desc"
        else:
            sort_by = "release_date.desc"
        
    update_settings_url = f"https://api.themoviedb.org/4/list/{list_id}"
    settings_payload = {"sort_by": sort_by}
    
    res_settings = requests.put(update_settings_url, headers=headers, json=settings_payload)
    if res_settings.status_code == 200:
        print(f"-> Ustawiono sortowanie listy '{list_name}' na: '{sort_by}'")
    else:
        print(f"-> Nie udało się wymusić sortowania na TMDB: {res_settings.text}")

    # 2. Dzielenie listy na paczki po maksymalnie 20 elementów (limit API v4)
    chunk_size = 20
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]
    
    print(f"Dodawanie {len(items)} pozycji do '{list_name}' (podział na {len(chunks)} paczek)...")
    
    add_url = f"https://api.themoviedb.org/4/list/{list_id}/items"
    
    for idx, chunk in enumerate(chunks, start=1):
        payload = {"items": chunk}
        res = requests.post(add_url, headers=headers, json=payload)
        
        if res.status_code == 200:
            print(f"  -> Paczka {idx}/{len(chunks)} dodana pomyślnie ({len(chunk)} szt.).")
        else:
            print(f"  -> Błąd przy paczce {idx}/{len(chunks)}: {res.text}")
            
        # Krótka pauza, aby nie przeciążyć API przy dużych aktualizacjach
        time.sleep(0.5)

def discover_media(media_type, params, max_pages=20):
    """
    Pobiera listę mediów z endpointu discover.
    Może pobrać więcej niż jedną stronę wyników (każda strona to max 20 pozycji).
    """
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    all_results = []
    
    # Tworzymy kopię parametrów, aby nie modyfikować oryginału
    query_params = params.copy()
    
    for page in range(1, max_pages + 1):
        query_params["page"] = page
        response = requests.get(url, headers=headers, params=query_params)
        
        if response.status_code != 200:
            print(f"Błąd discover dla {media_type} na stronie {page}: {response.text}")
            break
            
        data = response.json()
        results = data.get("results", [])
        if not results:
            break
            
        all_results.extend(results)
        
        # Jeśli pobraliśmy już wszystkie dostępne strony na TMDB, przerywamy pętlę
        if page >= data.get("total_pages", 1):
            break
            
        # Mała pauza między stronami
        time.sleep(0.5)
        
    return [{"media_type": media_type, "media_id": item["id"]} for item in all_results]

def get_date_range(mode="recent"):
    """
    Zwraca zakres dat (start_date, end_date) w formacie YYYY-MM-DD.
    
    Dla mode="recent":
      - start: 1. dzień poprzedniego miesiąca.
      - end: Ostatni dzień bieżącego miesiąca.
      
    Dla mode="upcoming":
      - start: Jutro.
      - end: Za dokładnie 90 dni (ok. 3 miesiące).
    """
    today = datetime.date.today()
    
    if mode == "upcoming":
        start_date = today + datetime.timedelta(days=1)
        end_date = today + datetime.timedelta(days=90)
        return start_date.isoformat(), end_date.isoformat()
        
    # Stara Logika dla "recent"
    #if today.month == 1:
    #    start_date = datetime.date(today.year - 1, 12, 1)
    #else:
    #    start_date = datetime.date(today.year, today.month - 1, 1)
        
    #if today.month == 12:
    #    end_date = datetime.date(today.year, 12, 31)
    #else:
    #    end_date = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
        
    #return start_date.isoformat(), end_date.isoformat()
    
    # Nowa logika dla "recent" (Od 1 stycznia do końca obecnego miesiąca)
    start_date = datetime.date(today.year, 1, 1)
    
    if today.month == 12:
        end_date = datetime.date(today.year, 12, 31)
    else:
        end_date = datetime.date(today.year, today.month + 1, 1) - datetime.timedelta(days=1)
        
    return start_date.isoformat(), end_date.isoformat()

    # ==========================================
    # URUCHOMIENIE PROCESU AKTUALIZACJI
    # ==========================================
# 1. NAJPIERW USUŃ STARE LISTY (wywołanie funkcji, która wcześniej była tylko zdefiniowana)
#print("Rozpoczynam czyszczenie konta...")
#delete_all_my_lists()
    
# 2. DOPIERO TERAZ POBIERZ AKTUALNY STAN (który powinien być już pusty lub zawierać tylko listy spoza skryptu)
print("\nPobieranie aktualnych list z konta...")
fetch_user_lists()
    
# Generowanie ciągów ID do wykluczenia (wyciąga wartości ze słowników i łączy przecinkami)
exclude_genres_str = ",".join(str(val) for val in EXCLUDE_GENRES.values())
exclude_keywords_str = ",".join(str(val) for val in EXCLUDE_KEYWORDS.values())
    
    # ------------------------------------------
    # 2.1 GATUNEK + PLATFORMA + OBECNY ROK
    # ------------------------------------------
print("\n--- Generowanie list: Gatunek + Platforma + Rok 2026 (Dynamiczne Daty) ---")
    
# Pobieramy dynamiczne daty dla nowości (poprzedni miesiąc + obecny)
# 1. Pobieramy dzisiejszą datę oraz obecny rok
today_date = datetime.date.today()
today_str = today_date.isoformat()
current_year = today_date.year

# 2. Dynamicznie obliczamy początek bieżącej dekady (np. dla 2026 wyjdzie 2020)
decade_start_year = (current_year // 10) * 10
decade_start_date = f"{decade_start_year}-01-01"   # np. "2020-01-01"
decade_suffix = f"({decade_start_year}s)"          # np. "(2020s)"
print(f"Filtrowanie premier w zakresie od {decade_start_date} do {today_str}")
    
for prov_name, prov_id in PROVIDERS.items():
# Odkomentuj jeśli chcesz testować tylko na SkyShowTime:
# if prov_name != "SkyShowTime":
#     continue
    
    # 1. Filmy dla standardowych gatunków i dodatkowych
    for g_dict, is_keyword in [(GENRES_MOVIES, False), (ADDITIONAL_GENRES_MOVIES, True)]:
        for g_name, g_val in g_dict.items():
            list_name = f"{prov_name}: {g_name}"
            params = {
                "primary_release_date.gte": decade_start_year,
                "primary_release_date.lte": today_str,
                "with_watch_providers": prov_id,
                "watch_region": REGION,
                "vote_count.gte": 5,
                "without_keywords": exclude_keywords_str,
                "sort_by": "release_date.desc"
            }
            if is_keyword:
                params["with_keywords"] = g_val
            else:
                params["with_genres"] = g_val
                
            items = discover_media("movie", params, max_pages=100)
            if items:
                # Pobieramy pierwszy element, który AKTUALNIE znajduje się na liście w TMDB
                # (Musisz mieć funkcję, która zwraca ID filmów z danej listy, np. get_list_items)
                current_list_items = get_tmdb_list_items(list_name) # <-- Twoja funkcja pobierająca zawartość listy
                if current_list_items and current_list_items[0] == items[0]:
                    print(f"-> Lista '{list_name}' jest aktualna (pierwszy element bez zmian). Pomijam aktualizację.")
                else:
                    update_tmdb_list(list_name, items)
            time.sleep(0.5)
    
    # 2. Seriale dla standardowych gatunków i dodatkowych
    for g_dict, is_keyword in [(GENRES_SERIES, False), (ADDITIONAL_GENRES_SERIES, True)]:
        for g_name, g_val in g_dict.items():
            list_name = f"{prov_name} (Seriale): {g_name}"
            params = {
                "first_air_date.gte": decade_start_year,
                "first_air_date.lte": today_str,
                "with_watch_providers": prov_id,
                "watch_region": REGION,
                "vote_count.gte": 5,
                "without_genres": exclude_genres_str,
                "without_keywords": exclude_keywords_str,
                "sort_by": "first_air_date.desc"
            }
            if is_keyword:
                params["with_keywords"] = g_val
            else:
                params["with_genres"] = g_val
                
            items = discover_media("tv", params, max_pages=100)
            if items:
                # Pobieramy pierwszy element, który AKTUALNIE znajduje się na liście w TMDB
                # (Musisz mieć funkcję, która zwraca ID filmów z danej listy, np. get_list_items)
                current_list_items = get_tmdb_list_items(list_name) # <-- Twoja funkcja pobierająca zawartość listy
                if current_list_items and current_list_items[0] == items[0]:
                    print(f"-> Lista '{list_name}' jest aktualna (pierwszy element bez zmian). Pomijam aktualizację.")
                else:
                    update_tmdb_list(list_name, items)
            time.sleep(0.5)
    
    # ------------------------------------------
    # 2.2 GATUNKI OGÓLNE (PO POPULARNOŚCI)
    # ------------------------------------------
#print("\n--- Generowanie list: Gatunki Ogólne (2026) ---")
#for g_name, g_id in GENRES_MOVIES.items():
#    list_name = f"{g_name} ({CURRENT_YEAR})"
#    params = {
#        "primary_release_year": CURRENT_YEAR,
#        "with_genres": g_id,
#        "sort_by": "popularity.desc"
#    }
#    items = discover_media("movie", params)
#    update_tmdb_list(list_name, items)
#    time.sleep(0.3)
    
    # ------------------------------------------
    # 2.3 DEKADY
# ------------------------------------------
#print("\n--- Generowanie list: Dekady (Filmy) ---")
#for dec_name, (start_date, end_date) in DECADES.items():
#    for g_name, g_id in GENRES_MOVIES.items():
#        list_name = f"{dec_name}: {g_name}"
#        params = {
#            "primary_release_date.gte": start_date,
#            "primary_release_date.lte": end_date,
#            "with_genres": g_id,
#            "sort_by": "popularity.desc"
#        }
#        items = discover_media("movie", params)
#        update_tmdb_list(list_name, items)
#        time.sleep(0.5)
    
    # ==========================================
    # 2.5 i 2.6 NOWOŚCI (FILMY & SERIALE) - OGÓLNE
    # ==========================================
print("\n--- Generowanie list: Ogólne Nowości Filmy i Seriale ---")
    
# 1. Ogólne Nowości Filmy
list_name_movies = f"Nowości - Filmy ({CURRENT_YEAR})"
params_movies = {
    "primary_release_year": CURRENT_YEAR,
    "vote_count.gte": 50,
    "without_keywords": exclude_keywords_str,
    "sort_by": "release_date.desc"
}
items_movies = discover_media("movie", params_movies)
if items_movies:
    current_items = get_tmdb_list_items(list_name_movies)
    if current_items and current_items[0] == items_movies[0]:
        print(f"-> Lista '{list_name_movies}' jest aktualna. Pomijam.")
    else:
        update_tmdb_list(list_name_movies, items_movies)
    time.sleep(0.5)
    
# 2. Ogólne Nowości Seriale
list_name_series = f"Nowości - Seriale ({CURRENT_YEAR})"
params_series = {
    "first_air_date_year": CURRENT_YEAR, 
    "vote_count.gte": 20,
    "without_genres": exclude_genres_str,
    "without_keywords": exclude_keywords_str,
    "sort_by": "first_air_date.desc"
}
items_series = discover_media("tv", params_series)
if items_series:
    current_items = get_tmdb_list_items(list_name_series)
    if current_items and current_items[0] == items_series[0]:
        print(f"-> Lista '{list_name_series}' jest aktualna. Pomijam.")
    else:
        update_tmdb_list(list_name_series, items_series)
time.sleep(0.5)
    
    
    # ==========================================
    # 2.7 i 2.8 NADCHODZĄCE PREMIERY - OGÓLNE (DYNAMICZNE OKNO +3 MIESIĄCE)
    # ==========================================
print("\n--- Generowanie list: Ogólne Nadchodzące Premiery (Dynamiczne Daty) ---")
    
    # Pobieramy zakres: od jutra do +90 dni
upcoming_start, upcoming_end = get_date_range(mode="upcoming")
print(f"Filtrowanie nadchodzących premier w zakresie od {upcoming_start} do {upcoming_end}")
    
    # 1. NADCHODZĄCE FILMY (Nowe, wartościowe, bez re-emisji)
list_upcoming_movies = f"Nadchodzące Premiery - Filmy ({CURRENT_YEAR})"
params_up_movies = {
    "release_date.gte": upcoming_start,
    "release_date.lte": upcoming_end,
    "without_keywords": exclude_keywords_str,
    "with_release_type": "2|3|4",  # Tylko premiery (Kino/Digital), bez powtórek
    "with_original_language": "en|pl|cs|sk|hr|hu|it|es|fr|de|no|sv|da",  # Wyklucza lokalny spam bez dystrybucji globalnej
    "popularity.gte": 3.0,
    "sort_by": "popularity.desc"
}
items_up_movies = discover_media("movie", params_up_movies, max_pages=100)
if items_up_movies:
    current_items = get_tmdb_list_items(list_upcoming_movies)
    if current_items and current_items[0] == items_up_movies[0]:
        print(f"-> Lista '{list_upcoming_movies}' jest aktualna. Pomijam.")
    else:
        update_tmdb_list(list_upcoming_movies, items_up_movies, sort_by="popularity.desc", clear=True)
time.sleep(0.5)
    
    # 2. ZUPEŁNIE NOWE SERIALE (Tylko Debiuty / Sezon 1)
list_upcoming_new_series = f"Nadchodzące Premiery - Nowe Seriale ({CURRENT_YEAR})"
params_up_new_series = {
    "first_air_date.gte": upcoming_start,
    "first_air_date.lte": upcoming_end,
    "without_genres": exclude_genres_str,
    "without_keywords": exclude_keywords_str,
    "with_original_language": "en|pl|cs|sk|hr|hu|it|es|fr|de|no|sv|da",  # Wyklucza lokalny spam
    "popularity.gte": 3.0,
    "sort_by": "popularity.desc"
}
items_up_new_series = discover_media("tv", params_up_new_series, max_pages=100)
if items_up_new_series:
    current_items = get_tmdb_list_items(list_upcoming_new_series)
    if current_items and current_items[0] == items_up_new_series[0]:
        print(f"-> Lista '{list_upcoming_new_series}' jest aktualna. Pomijam.")
    else:
        update_tmdb_list(list_upcoming_new_series, items_up_new_series, sort_by="popularity.desc", clear=True)
time.sleep(0.5)

    # 3. POWRACAJĄCE SERIALE (Nowe Sezony znanych serii)
list_upcoming_returning_series = f"Nadchodzące Premiery - Nowe Sezony Seriali ({CURRENT_YEAR})"
params_up_returning_series = {
    "air_date.gte": upcoming_start,
    "air_date.lte": upcoming_end,
    "first_air_date.lte": upcoming_start,  # Debiut miał miejsce wcześniej (to NIE jest 1. sezon!)
    "without_genres": exclude_genres_str,
    "without_keywords": exclude_keywords_str,
    "with_original_language": "en|pl|cs|sk|hr|hu|it|es|fr|de|no|sv|da",
    "popularity.gte": 3.0,
    "sort_by": "popularity.desc"
}
items_up_returning_series = discover_media("tv", params_up_returning_series, max_pages=100)
if items_up_returning_series:
    current_items = get_tmdb_list_items(list_upcoming_returning_series)
    if current_items and current_items[0] == items_up_returning_series[0]:
        print(f"-> Lista '{list_upcoming_returning_series}' jest aktualna. Pomijam.")
    else:
        update_tmdb_list(list_upcoming_returning_series, items_up_returning_series, sort_by="popularity.desc", clear=True)
time.sleep(0.5)
    
    # ==========================================
    # 2.9 i 3.0 PRODUKCJE Z KONKRETNYCH KRAJÓW / JĘZYKA
    # ==========================================
print("\n--- Generowanie list: Filmy i Seriale z Różnych Krajów (2026) ---")

# 1. Pobieramy dzisiejszą datę oraz obecny rok
today_date = datetime.date.today()
today_str = today_date.isoformat()
current_year = today_date.year

# 2. Dynamicznie obliczamy początek bieżącej dekady (np. dla 2026 wyjdzie 2020)
decade_start_year = (current_year // 10) * 10
decade_start_date = f"{decade_start_year}-01-01"   # np. "2020-01-01"
decade_suffix = f"({decade_start_year}s)"          # np. "(2020s)"

for lang_name, lang_code in LANGUAGES.items():
    print(f"\nGenerowanie list dla języka: {lang_name} ({lang_code})...")

        # Dynamiczne dopasowanie kodu kraju
    country_code = lang_code.upper()
    if lang_name == "Brytyjskie":
        country_code = "GB"
    elif lang_name == "Australijskie":
        country_code = "AU"
    elif lang_name == "Meksykańskie":
        country_code = "MX"
    elif lang_name == "Brazylijskie":
        country_code = "BR"
        
    # 1. Filmy (np. "Polskie - Filmy (2026)")
    list_lang_movies = f"{lang_name} - Filmy"
    params_lang_movies = {
        "primary_release_date.gte": decade_start_date, # <-- Pobiera filmy wydane od 1950 roku
        "primary_release_date.lte": today_str,    # <-- Do dzisiaj (odcina przyszłe i puste daty)
        "with_original_language": lang_code, # <-- np. "pl", "it", "es"
    #    "with_origin_country": country_code, # <-- np. "PL", "IT", "ES"
        "without_keywords": exclude_keywords_str,
        "vote_count.gte": 5,                     # Obniżony próg dla filmów lokalnych
        "sort_by": "release_date.desc"
    }
    items_lang_movies = discover_media("movie", params_lang_movies, max_pages = 100)
    if items_lang_movies:
        current_items = get_tmdb_list_items(list_lang_movies)
        if current_items and current_items[0] == items_lang_movies[0]:
            print(f"-> Lista '{list_lang_movies}' jest aktualna. Pomijam.")
        else:
            update_tmdb_list(list_lang_movies, items_lang_movies)
    time.sleep(0.5)
    
    # 2. Seriale (np. "Polskie - Seriale (2026)")
    list_lang_series = f"{lang_name} - Seriale"
    params_lang_series = {
        "first_air_date.gte": decade_start_date, # <-- Pobiera seriale od początku 1950 roku
        "first_air_date.lte": today_str,    # <-- Do dzisiaj (zapobiega przyszłym/błędnym datom)
        "with_original_language": lang_code, # <-- np. "pl", "it", "es"
    #    "with_origin_country": country_code, # <-- np. "PL", "IT", "ES"
        "without_genres": exclude_genres_str,
        "without_keywords": exclude_keywords_str,
        "vote_count.gte": 5,                     # Obniżony próg dla seriali lokalnych
        "sort_by": "first_air_date.desc"
    }
    items_lang_series = discover_media("tv", params_lang_series, max_pages = 100)
    if items_lang_series:
        current_items = get_tmdb_list_items(list_lang_series)
        if current_items and current_items[0] == items_lang_series[0]:
            print(f"-> Lista '{list_lang_series}' jest aktualna. Pomijam.")
        else:
            update_tmdb_list(list_lang_series, items_lang_series)
    time.sleep(0.5)
    
print("\n--- CAŁY PROCES ZAKOŃCZONY POMYŚLNIE! ---")
