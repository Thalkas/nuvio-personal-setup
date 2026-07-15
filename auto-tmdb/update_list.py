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

def update_tmdb_list(list_name, items, clear=False):
    """Czyści listę i dodaje do niej nowe pozycje."""
    list_id = get_or_create_list(list_name)
    if not list_id:
        return

    # Krok 1: Wyczyszczenie listy (tylko jeśli parametr clear jest ustawiony na True)
    if clear:
        print(f"Czyszczenie listy '{list_name}' przed dodaniem nowych pozycji...")
        clear_url = f"https://api.themoviedb.org/4/list/{list_id}/clear"
        # API v4 wymaga metody POST do czyszczenia listy
        res_clear = requests.post(clear_url, headers=headers)
        if res_clear.status_code != 200:
            print(f"Problem z czyszczeniem listy '{list_name}': {res_clear.text}")

    if not items:
        print(f"Brak nowych filmów/seriali dla '{list_name}'.")
        return

    # Krok 2: Dodanie nowych elementów (maksymalnie 20 - ograniczenie TMDB na jeden request)
    add_url = f"https://api.themoviedb.org/4/list/{list_id}/items"
    payload = {"items": items[:20]} # bierzemy top 50 wyników
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
# 1. NAJPIERW USUŃ STARE LISTY (wywołanie funkcji, która wcześniej była tylko zdefiniowana)
print("Rozpoczynam czyszczenie konta...")
delete_all_my_lists()

# 2. DOPIERO TERAZ POBIERZ AKTUALNY STAN (który powinien być już pusty lub zawierać tylko listy spoza skryptu)
#print("\nPobieranie aktualnych list z konta...")
#fetch_user_lists()

