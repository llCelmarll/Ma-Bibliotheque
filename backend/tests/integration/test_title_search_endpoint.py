"""
Tests d'intégration pour l'endpoint de recherche de livre par titre (GET /scan/search).
"""
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

from tests.conftest import create_test_book


GOOGLE_ITEM = {
    "title": "Clean Code",
    "subtitle": "A Handbook of Agile Software Craftsmanship",
    "authors": ["Robert C. Martin"],
    "publisher": "Pearson",
    "publishedDate": "2008",
    "pageCount": 464,
    "imageLinks": {"thumbnail": "http://books.google.com/cover.jpg"},
    "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780132350884"}],
}

OPENLIBRARY_DOC = {
    "title": "Clean Code in Python",
    "author_name": ["Mariano Anaya"],
    "first_publish_year": 2018,
    "cover_i": 12345,
}


@pytest.mark.integration
@pytest.mark.scan
class TestTitleSearchEndpoint:
    """Tests de l'endpoint GET /scan/search."""

    @patch('app.services.scan_service.search_openlibrary_by_title')
    @patch('app.services.scan_service.search_google_books_by_title')
    def test_both_sources_success(self, mock_google, mock_ol, authenticated_client: TestClient):
        """Les deux sources renvoient des résultats — la réponse contient les deux listes peuplées."""
        mock_google.return_value = ([GOOGLE_ITEM], None)
        mock_ol.return_value = ([OPENLIBRARY_DOC], None)

        response = authenticated_client.get("/scan/search", params={"title": "Clean Code"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["google_results"]) == 1
        assert data["google_results"][0]["title"] == "Clean Code"
        assert len(data["openlibrary_results"]) == 1
        assert data["openlibrary_results"][0]["title"] == "Clean Code in Python"
        assert data["google_error"] is None
        assert data["openlibrary_error"] is None

    @patch('app.services.scan_service.search_openlibrary_by_title')
    @patch('app.services.scan_service.search_google_books_by_title')
    def test_authors_enriched_when_existing_in_db(
        self, mock_google, mock_ol, authenticated_client: TestClient, session, test_user
    ):
        """Un auteur déjà en base doit être marqué exists=True avec son id."""
        from app.repositories.author_repository import AuthorRepository
        from app.models.author_model import Author

        author_repo = AuthorRepository(session)
        existing_author = author_repo.create(Author(name="Robert C. Martin"))

        mock_google.return_value = ([GOOGLE_ITEM], None)
        mock_ol.return_value = ([], None)

        response = authenticated_client.get("/scan/search", params={"title": "Clean Code"})

        assert response.status_code == 200
        data = response.json()
        author = data["google_results"][0]["authors"][0]
        assert author["name"] == "Robert C. Martin"
        assert author["exists"] is True
        assert author["id"] == existing_author.id

    @patch('app.services.scan_service.search_openlibrary_by_title')
    @patch('app.services.scan_service.search_google_books_by_title')
    def test_one_source_fails_other_succeeds(self, mock_google, mock_ol, authenticated_client: TestClient):
        """Une source en échec ne bloque pas la réponse — l'autre source reste disponible."""
        mock_google.return_value = (None, "Google Books est temporairement indisponible (erreur 503)")
        mock_ol.return_value = ([OPENLIBRARY_DOC], None)

        response = authenticated_client.get("/scan/search", params={"title": "Clean Code"})

        assert response.status_code == 200
        data = response.json()
        assert data["google_results"] == []
        assert "indisponible" in data["google_error"]
        assert len(data["openlibrary_results"]) == 1
        assert data["openlibrary_error"] is None

    @patch('app.services.scan_service.search_openlibrary_by_title')
    @patch('app.services.scan_service.search_google_books_by_title')
    def test_no_results_both_sources(self, mock_google, mock_ol, authenticated_client: TestClient):
        """Aucun résultat sur aucune source — listes vides, pas d'erreur."""
        mock_google.return_value = ([], None)
        mock_ol.return_value = ([], None)

        response = authenticated_client.get("/scan/search", params={"title": "Titre Introuvable Zzz"})

        assert response.status_code == 200
        data = response.json()
        assert data["google_results"] == []
        assert data["openlibrary_results"] == []
        assert data["title_match"] == []

    @patch('app.services.scan_service.search_openlibrary_by_title')
    @patch('app.services.scan_service.search_google_books_by_title')
    def test_title_match_populated_for_existing_book(
        self, mock_google, mock_ol, authenticated_client: TestClient, session, test_user
    ):
        """Un livre au titre similaire déjà en bibliothèque doit apparaître dans title_match."""
        create_test_book(session, test_user.id, title="Clean Code", isbn="9780132350884")
        session.commit()

        mock_google.return_value = ([], None)
        mock_ol.return_value = ([], None)

        response = authenticated_client.get("/scan/search", params={"title": "Clean Code"})

        assert response.status_code == 200
        data = response.json()
        assert len(data["title_match"]) == 1
        assert data["title_match"][0]["title"] == "Clean Code"

    def test_unauthenticated_returns_403(self, client: TestClient):
        """Une requête non authentifiée doit être rejetée."""
        response = client.get("/scan/search", params={"title": "Clean Code"})

        assert response.status_code == 403
