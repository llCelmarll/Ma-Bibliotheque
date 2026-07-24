import httpx

BASE_URL = "https://openlibrary.org"

def get_openlibrary_cover_url(isbn: str) -> str | None:
    """Retourne l'URL de couverture OpenLibrary si elle pointe vers une vraie image (>1×1).
    Utilise httpx synchrone — à appeler depuis du code non-async."""
    url = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg"
    try:
        with httpx.Client(timeout=5.0, follow_redirects=True) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return None
            # Un GIF 1×1 (pixel de remplacement) fait exactement 35 octets
            if len(resp.content) <= 100:
                return None
            return url
    except httpx.HTTPError:
        return None

async def fetch_openlibrary(isbn: str) -> tuple[dict | None, str | None]:
    """Récupère les infos d'un livre via OpenLibrary.

    Returns:
        tuple: (data, error) — data est le dict ou None, error est un message d'erreur ou None.
    """
    url = f"{BASE_URL}/isbn/{isbn}.json"
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url)
            if response.status_code == 404:
                return None, None  # Livre non trouvé (pas une erreur)
            if response.status_code != 200:
                print(f"Erreur OpenLibrary pour ISBN {isbn}: HTTP {response.status_code}")
                return None, f"OpenLibrary est temporairement indisponible (erreur {response.status_code})"
            return response.json(), None
    except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        print(f"Erreur OpenLibrary pour ISBN {isbn}: {e}")
        return None, "OpenLibrary est temporairement indisponible (délai d'attente dépassé)"
    except httpx.RequestError as e:
        print(f"Erreur OpenLibrary pour ISBN {isbn}: {e}")
        return None, "OpenLibrary est temporairement indisponible (erreur réseau)"


async def search_openlibrary_by_title(title: str, limit: int = 8) -> tuple[list[dict] | None, str | None]:
    """Recherche des livres via OpenLibrary par titre.

    Returns:
        tuple: (docs, error) — docs est la liste des résultats trouvés (vide si aucun
        résultat), error est un message d'erreur ou None.
    """
    url = f"{BASE_URL}/search.json"
    try:
        async with httpx.AsyncClient(timeout=5.0, follow_redirects=True) as client:
            response = await client.get(url, params={"title": title, "limit": limit})
            if response.status_code != 200:
                print(f"Erreur OpenLibrary pour titre '{title}': HTTP {response.status_code}")
                return None, f"OpenLibrary est temporairement indisponible (erreur {response.status_code})"
            data = response.json()
            return data.get("docs") or [], None
    except (httpx.ConnectTimeout, httpx.ReadTimeout) as e:
        print(f"Erreur OpenLibrary pour titre '{title}': {e}")
        return None, "OpenLibrary est temporairement indisponible (délai d'attente dépassé)"
    except httpx.RequestError as e:
        print(f"Erreur OpenLibrary pour titre '{title}': {e}")
        return None, "OpenLibrary est temporairement indisponible (erreur réseau)"