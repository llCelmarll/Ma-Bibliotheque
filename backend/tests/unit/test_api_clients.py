"""
Tests unitaires pour les clients d'APIs externes.
Mock des requêtes HTTP pour tester la logique de parsing.
"""
import os
import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from app.clients.google_books import fetch_google_books, search_google_books_by_title
from app.clients.openlibrary import fetch_openlibrary, search_openlibrary_by_title


@pytest.mark.unit
@pytest.mark.scan
class TestGoogleBooksClient:
    """Tests pour le client Google Books API."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_success(self, mock_get: AsyncMock):
        """Test de récupération réussie depuis Google Books."""
        # Mock de la réponse HTTP
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {
                    "volumeInfo": {
                        "title": "Test Book",
                        "authors": ["Test Author"],
                        "publishedDate": "2023",
                        "pageCount": 300,
                        "description": "A test book",
                        "industryIdentifiers": [
                            {"type": "ISBN_13", "identifier": "9781234567890"}
                        ],
                        "imageLinks": {
                            "thumbnail": "http://example.com/cover.jpg"
                        }
                    }
                }
            ]
        }
        mock_get.return_value = mock_response
        
        data, error = await fetch_google_books("9781234567890")

        assert data is not None
        assert error is None
        assert data["title"] == "Test Book"
        assert data["authors"] == ["Test Author"]
        assert data["publishedDate"] == "2023"
        assert data["pageCount"] == 300
        assert data["description"] == "A test book"
        
        # Vérifier que l'URL est correcte
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "isbn:9781234567890" in str(call_args)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_no_results(self, mock_get: AsyncMock):
        """Test quand Google Books ne trouve aucun résultat."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}  # Pas de résultats
        mock_get.return_value = mock_response
        
        data, error = await fetch_google_books("9999999999999")

        assert data is None
        assert error is None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_no_items_key(self, mock_get: AsyncMock):
        """Test quand Google Books retourne une réponse sans 'items'."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}  # Pas de clé 'items'
        mock_get.return_value = mock_response

        data, error = await fetch_google_books("9999999999999")

        assert data is None
        assert error is None
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_http_error(self, mock_get: AsyncMock):
        """Test quand Google Books retourne une erreur HTTP."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        data, error = await fetch_google_books("9781234567890")

        assert data is None
        assert error is not None
        assert "erreur 404" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_timeout(self, mock_get: AsyncMock):
        """Test quand Google Books timeout."""
        mock_get.side_effect = httpx.ConnectTimeout("Connection timeout")

        data, error = await fetch_google_books("9781234567890")

        assert data is None
        assert error is not None
        assert "indisponible" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_google_books_request_error(self, mock_get: AsyncMock):
        """Test quand il y a une erreur de requête."""
        mock_get.side_effect = httpx.RequestError("Network error")

        data, error = await fetch_google_books("9781234567890")

        assert data is None
        assert error is not None
        assert "indisponible" in error


@pytest.mark.unit
@pytest.mark.scan
class TestGoogleBooksTitleSearch:
    """Tests pour la recherche par titre via Google Books API."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_success_multiple_results(self, mock_get: AsyncMock):
        """Test de recherche par titre avec plusieurs résultats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "items": [
                {"volumeInfo": {"title": "Clean Code", "authors": ["Robert C. Martin"]}},
                {"volumeInfo": {"title": "Clean Code in Python", "authors": ["Mariano Anaya"]}},
            ]
        }
        mock_get.return_value = mock_response

        items, error = await search_google_books_by_title("Clean Code")

        assert error is None
        assert len(items) == 2
        assert items[0]["title"] == "Clean Code"
        assert items[1]["title"] == "Clean Code in Python"

        call_args = mock_get.call_args
        assert "intitle:Clean Code" in str(call_args)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_no_results(self, mock_get: AsyncMock):
        """Test de recherche par titre sans résultat — retourne une liste vide, pas None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"items": []}
        mock_get.return_value = mock_response

        items, error = await search_google_books_by_title("Titre Introuvable Zzz")

        assert error is None
        assert items == []

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_http_error_non_retryable(self, mock_get: AsyncMock):
        """Test d'une erreur HTTP non-retryable (4xx hors 429)."""
        mock_response = AsyncMock()
        mock_response.status_code = 400
        mock_get.return_value = mock_response

        items, error = await search_google_books_by_title("Clean Code")

        assert items is None
        assert error is not None
        assert "erreur 400" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    @patch('asyncio.sleep', new_callable=AsyncMock)
    async def test_search_retries_then_succeeds(self, mock_sleep: AsyncMock, mock_get: AsyncMock):
        """Test qu'un 503 suivi d'un succès est bien retenté avant de retourner des résultats."""
        error_response = Mock()
        error_response.status_code = 503

        success_response = Mock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "items": [{"volumeInfo": {"title": "Clean Code"}}]
        }

        mock_get.side_effect = [error_response, success_response]

        items, error = await search_google_books_by_title("Clean Code")

        assert error is None
        assert len(items) == 1
        assert mock_get.call_count == 2
        mock_sleep.assert_called_once()

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_timeout(self, mock_get: AsyncMock):
        """Test du timeout lors d'une recherche par titre."""
        mock_get.side_effect = httpx.ConnectTimeout("Connection timeout")

        items, error = await search_google_books_by_title("Clean Code")

        assert items is None
        assert error is not None
        assert "indisponible" in error


@pytest.mark.unit
@pytest.mark.scan
class TestOpenLibraryClient:
    """Tests pour le client OpenLibrary API."""
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_success(self, mock_get: AsyncMock):
        """Test de récupération réussie depuis OpenLibrary."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Test Book from OL",
            "authors": [
                {"name": "Test Author 1"},
                {"name": "Test Author 2"}
            ],
            "publishers": ["Test Publisher"],
            "publish_date": "2023",  
            "number_of_pages": 250,
            "subjects": ["Fiction", "Adventure"],
            "covers": [12345678]
        }
        mock_get.return_value = mock_response
        
        data, error = await fetch_openlibrary("9781234567890")

        assert data is not None
        assert error is None
        assert data["title"] == "Test Book from OL"
        assert len(data["authors"]) == 2
        assert data["authors"][0]["name"] == "Test Author 1"
        assert data["publishers"] == ["Test Publisher"]
        assert data["number_of_pages"] == 250
        
        # Vérifier l'URL appelée
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "/isbn/9781234567890.json" in str(call_args)
    
    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_not_found(self, mock_get: AsyncMock):
        """Test quand OpenLibrary ne trouve pas le livre."""
        mock_response = AsyncMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response
        
        data, error = await fetch_openlibrary("9999999999999")

        assert data is None
        assert error is None

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_server_error(self, mock_get: AsyncMock):
        """Test quand OpenLibrary retourne une erreur serveur."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        data, error = await fetch_openlibrary("9781234567890")

        assert data is None
        assert error is not None
        assert "erreur 500" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_timeout(self, mock_get: AsyncMock):
        """Test quand OpenLibrary timeout."""
        mock_get.side_effect = httpx.ReadTimeout("Read timeout")

        data, error = await fetch_openlibrary("9781234567890")

        assert data is None
        assert error is not None
        assert "indisponible" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_connection_error(self, mock_get: AsyncMock):
        """Test quand il y a une erreur de connexion."""
        mock_get.side_effect = httpx.ConnectTimeout("Connection failed")

        data, error = await fetch_openlibrary("9781234567890")

        assert data is None
        assert error is not None
        assert "indisponible" in error

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_fetch_openlibrary_minimal_data(self, mock_get: AsyncMock):
        """Test avec des données minimales d'OpenLibrary."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "title": "Minimal Book"
            # Pas d'autres champs
        }
        mock_get.return_value = mock_response

        data, error = await fetch_openlibrary("9781234567890")

        assert data is not None
        assert error is None
        assert data["title"] == "Minimal Book"
        # Les autres champs peuvent être absents, c'est OK


@pytest.mark.unit
@pytest.mark.scan
class TestOpenLibraryTitleSearch:
    """Tests pour la recherche par titre via OpenLibrary."""

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_success_multiple_results(self, mock_get: AsyncMock):
        """Test de recherche par titre avec plusieurs résultats."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "numFound": 2,
            "docs": [
                {"title": "Clean Code", "author_name": ["Robert C. Martin"], "first_publish_year": 2008},
                {"title": "Clean Code in Python", "author_name": ["Mariano Anaya"], "first_publish_year": 2018},
            ],
        }
        mock_get.return_value = mock_response

        docs, error = await search_openlibrary_by_title("Clean Code")

        assert error is None
        assert len(docs) == 2
        assert docs[0]["title"] == "Clean Code"

        call_args = mock_get.call_args
        assert "/search.json" in str(call_args)
        assert "/isbn/" not in str(call_args)

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_no_results(self, mock_get: AsyncMock):
        """Test de recherche par titre sans résultat — retourne une liste vide, pas None."""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"numFound": 0, "docs": []}
        mock_get.return_value = mock_response

        docs, error = await search_openlibrary_by_title("Titre Introuvable Zzz")

        assert error is None
        assert docs == []

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_server_error(self, mock_get: AsyncMock):
        """Test d'une erreur serveur OpenLibrary — pas de retry, échec direct."""
        mock_response = AsyncMock()
        mock_response.status_code = 500
        mock_get.return_value = mock_response

        docs, error = await search_openlibrary_by_title("Clean Code")

        assert docs is None
        assert error is not None
        assert "erreur 500" in error
        assert mock_get.call_count == 1

    @pytest.mark.asyncio
    @patch('httpx.AsyncClient.get')
    async def test_search_timeout(self, mock_get: AsyncMock):
        """Test du timeout lors d'une recherche par titre."""
        mock_get.side_effect = httpx.ReadTimeout("Read timeout")

        docs, error = await search_openlibrary_by_title("Clean Code")

        assert docs is None
        assert error is not None
        assert "indisponible" in error


@pytest.mark.live
class TestGoogleBooksApiKey:
    """Test réel de la clé API Google Books (nécessite réseau + GOOGLE_BOOKS_API_KEY)."""

    @pytest.mark.asyncio
    async def test_api_key_is_valid(self):
        """Vérifie que la clé API configurée est acceptée par Google Books."""
        api_key = os.environ.get("GOOGLE_BOOKS_API_KEY")
        if not api_key:
            pytest.skip("GOOGLE_BOOKS_API_KEY non définie, test ignoré")

        # ISBN connu : "L'Étranger" de Camus — toujours présent dans Google Books
        # Le client gère déjà 5 tentatives en interne — un seul appel suffit ici
        data, error = await fetch_google_books("9782070360024")

        # Si l'API est toujours indispo après les retries du client, on skippe
        if error and "indisponible" in error:
            pytest.skip(f"Google Books indisponible après retries : {error}")

        assert error is None, f"Clé API rejetée ou erreur : {error}"
        assert data is not None, "Aucune donnée retournée malgré une clé valide"
        assert "title" in data, f"Réponse inattendue de Google Books : {data}"