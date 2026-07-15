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
    DECADES
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
    url = f"https://api.themoviedb.org/4/list/1"
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

def update_tmdb_list(list_name, items):
    """Czyści listę i dodaje do niej nowe pozycje."""
    list_id = get_or_create_list(list_name)
    if not list_id:
        return

    # Krok 1: Wyczyszczenie listy
    clear_url = f"https://api.themoviedb.org/4/list/{list_id}/clear"
    requests.get(clear_url, headers=headers)
    
    if not items:
        print(f"Lista '{list_name}' została wyczyszczona (brak nowych filmów/seriali).")
        return

    # Krok 2: Dodanie nowych elementów (maksymalnie 50 - ograniczenie TMDB na jeden request)
    add_url = f"https://api.themoviedb.org/4/list/{list_id}/items"
    payload = {"items": items[:50]} # bierzemy top 50 wyników
    res = requests.post(add_url, headers=headers, json=payload)
    if res.status_code == 200:
        print(f"Zaktualizowano listę '{list_name}' - dodano {len(payload['items'])} pozycji.")
    else:
        print(f"Błąd podczas dodawania elementów do '{list_name}': {res.text}")

def discover_media(media_type, params):
    """Pobiera listę mediów z endpointu discover i zwraca gotowy format do zapisu."""
    url = f"https://api.themoviedb.org/3/discover/{media_type}"
    response = requests.get(url, headers=headers, params=params)
    if response.status_code != 200:
        return []
    results = response.json().get("results", [])
    return [{"media_type": media_type, "media_id": item["id"]} for item in results]

# ==========================================
# URUCHOMIENIE PROCESU AKTUALIZACJI
# ==========================================
print("Pobieranie aktualnych list z konta...")
fetch_user_lists()

# ------------------------------------------
# 2.1 GATUNEK + PLATFORMA + OBECNY ROK
# ------------------------------------------
print("\n--- Generowanie list: Gatunek + Platforma + Rok 2026 ---")
for prov_name, prov_id in PROVIDERS.items():
    # Filmy dla standardowych gatunków i dodatkowych
    for g_dict, is_keyword in [(GENRES_MOVIES, False), (ADDITIONAL_GENRES_MOVIES, True)]:
        for g_name, g_val in g_dict.items():
            list_name = f"{prov_name}: {g_name} ({CURRENT_YEAR})"
            params = {
                "primary_release_year": CURRENT_YEAR,
                "with_watch_providers": prov_id,
                "watch_region": REGION,
                "sort_by": "release_date.desc"
            }
            if is_keyword:
                params["with_keywords"] = g_val
            else:
                params["with_genres"] = g_val
            
            items = discover_media("movie", params)
            update_tmdb_list(list_name, items)
            time.sleep(0.3)

    # Seriale dla standardowych gatunków i dodatkowych
    for g_dict, is_keyword in [(GENRES_SERIES, False), (ADDITIONAL_GENRES_SERIES, True)]:
        for g_name, g_val in g_dict.items():
            list_name = f"{prov_name} (Seriale): {g_name} ({CURRENT_YEAR})"
            params = {
                "first_air_date_year": CURRENT_YEAR,
                "with_watch_providers": prov_id,
                "watch_region": REGION,
                "sort_by": "first_air_date.desc"
            }
            if is_keyword:
                params["with_keywords"] = g_val
            else:
                params["with_genres"] = g_val
            
            items = discover_media("tv", params)
            update_tmdb_list(list_name, items)
            time.sleep(0.3)

# ------------------------------------------
# 2.2 GATUNKI OGÓLNE (PO POPULARNOŚCI)
# ------------------------------------------
print("\n--- Generowanie list: Gatunki Ogólne (2026) ---")
for g_name, g_id in GENRES_MOVIES.items():
    list_name = f"{g_name} ({CURRENT_YEAR})"
    params = {
        "primary_release_year": CURRENT_YEAR,
        "with_genres": g_id,
        "sort_by": "popularity.desc"
    }
    items = discover_media("movie", params)
    update_tmdb_list(list_name, items)
    time.sleep(0.3)

# ------------------------------------------
# 2.3 DEKADY
# ------------------------------------------
print("\n--- Generowanie list: Dekady (Filmy) ---")
for dec_name, (start_date, end_date) in DECADES.items():
    for g_name, g_id in GENRES_MOVIES.items():
        list_name = f"{dec_name}: {g_name}"
        params = {
            "primary_release_date.gte": start_date,
            "primary_release_date.lte": end_date,
            "with_genres": g_id,
            "sort_by": "popularity.desc"
        }
        items = discover_media("movie", params)
        update_tmdb_list(list_name, items)
        time.sleep(0.3)

# ------------------------------------------
# 2.5 i 2.6 NOWOŚCI (FILMY & SERIALE)
# ------------------------------------------
print("\n--- Generowanie list: Nowości Filmy i Seriale ---")
for g_dict, is_keyword, m_type in [(GENRES_MOVIES, False, "movie"), (ADDITIONAL_GENRES_MOVIES, True, "movie")]:
    for g_name, g_val in g_dict.items():
        list_name = f"Nowości - Filmy: {g_name} ({CURRENT_YEAR})"
        params = {"primary_release_year": CURRENT_YEAR, "sort_by": "release_date.desc"}
        params["with_keywords" if is_keyword else "with_genres"] = g_val
        items = discover_media("movie", params)
        update_tmdb_list(list_name, items)
        time.sleep(0.3)

for g_dict, is_keyword, m_type in [(GENRES_SERIES, False, "tv"), (ADDITIONAL_GENRES_SERIES, True, "tv")]:
    for g_name, g_val in g_dict.items():
        list_name = f"Nowości - Seriale: {g_name} ({CURRENT_YEAR})"
        params = {"first_air_date_year": CURRENT_YEAR, "sort_by": "first_air_date.desc"}
        params["with_keywords" if is_keyword else "with_genres"] = g_val
        items = discover_media("tv", params)
        update_tmdb_list(list_name, items)
        time.sleep(0.3)

# ------------------------------------------
# 2.7 i 2.8 NADCHODZĄCE PREMIERY
# ------------------------------------------
print("\n--- Generowanie list: Nadchodzące Premiery ---")
today = datetime.date.today().isoformat()
end_of_year = f"{CURRENT_YEAR}-12-31"

for g_dict, is_keyword in [(GENRES_MOVIES, False), (ADDITIONAL_GENRES_MOVIES, True)]:
    for g_name, g_val in g_dict.items():
        list_name = f"Nadchodzące Premiery - Filmy: {g_name} ({CURRENT_YEAR})"
        params = {
            "primary_release_date.gte": today,
            "primary_release_date.lte": end_of_year,
            "sort_by": "release_date.asc"  # sortowanie od najbliższych premier
        }
        params["with_keywords" if is_keyword else "with_genres"] = g_val
        items = discover_media("movie", params)
        update_tmdb_list(list_name, items)
        time.sleep(0.3)

for g_dict, is_keyword in [(GENRES_SERIES, False), (ADDITIONAL_GENRES_SERIES, True)]:
    for g_name, g_val in g_dict.items():
        list_name = f"Nadchodzące Premiery - Seriale: {g_name} ({CURRENT_YEAR})"
        params = {
            "first_air_date.gte": today,
            "first_air_date.lte": end_of_year,
            "sort_by": "first_air_date.asc"
        }
        params["with_keywords" if is_keyword else "with_genres"] = g_val
        items = discover_media("tv", params)
        update_tmdb_list(list_name, items)
        time.sleep(0.3)

print("\n--- CAŁY PROCES ZAKOŃCZONY POMYŚLNIE! ---")
