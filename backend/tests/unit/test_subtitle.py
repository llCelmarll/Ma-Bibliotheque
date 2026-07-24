"""
Tests de non-régression pour le champ subtitle des livres.

Ces tests couvrent les 3 points de défaillance découverts lors de l'implémentation :
1. book_repository.create() doit persister le subtitle
2. SuggestedBook (scan_service) doit inclure subtitle dans model_dump()
3. scan_isbn() doit propager le subtitle depuis Google Books vers SuggestedBook

Le point 4 (edit.tsx frontend) est hors scope backend.
"""
import pytest
from unittest.mock import patch
from sqlmodel import Session

from app.models.book_model import Book
from app.models.user_model import User
from app.repositories.book_repository import BookRepository
from app.schemas.book_schemas import BookCreate, BookUpdate, BookSearchParams
from app.services.book_service import BookService
from app.services.scan_service import ScanService
from app.schemas.scan_schemas import SuggestedBook
from tests.conftest import create_test_book


@pytest.mark.unit
class TestBookRepositorySubtitle:
    """Tests du repository — persistance et recherche du subtitle."""

    def test_create_book_with_subtitle(self, session: Session, test_user: User):
        """book_repository.create() doit persister le subtitle en base."""
        repo = BookRepository(session)
        book_data = BookCreate(
            title="Clean Architecture",
            subtitle="A Craftsman's Guide to Software Structure and Design",
            isbn="9780134494166",
        )
        book = repo.create(book_data, owner_id=test_user.id)
        session.commit()

        retrieved = session.get(Book, book.id)
        assert retrieved.subtitle == "A Craftsman's Guide to Software Structure and Design"

    def test_create_book_without_subtitle(self, session: Session, test_user: User):
        """book_repository.create() doit accepter subtitle=None sans erreur."""
        repo = BookRepository(session)
        book_data = BookCreate(title="Sans sous-titre", isbn="9781111111111")
        book = repo.create(book_data, owner_id=test_user.id)
        session.commit()

        retrieved = session.get(Book, book.id)
        assert retrieved.subtitle is None

    def test_search_finds_book_by_subtitle(self, session: Session, test_user: User):
        """_apply_global_search doit trouver un livre via son subtitle."""
        repo = BookRepository(session)

        # Livre avec subtitle contenant le terme recherché
        book_data = BookCreate(
            title="Architecture logicielle",
            subtitle="Guide du craftsman",
            isbn="9783333333333",
        )
        book = repo.create(book_data, owner_id=test_user.id)
        session.commit()

        # Autre livre sans subtitle (ne doit pas ressortir)
        other_data = BookCreate(title="Autre livre", isbn="9784444444444")
        repo.create(other_data, owner_id=test_user.id)
        session.commit()

        params = BookSearchParams(search="craftsman", skip=0, limit=100)
        results = repo.search_books(params, user_id=test_user.id)
        result_ids = [b.id for b in results]

        assert book.id in result_ids, "La recherche doit trouver un livre par son subtitle"

    def test_search_does_not_match_other_book_by_subtitle(self, session: Session, test_user: User):
        """Un terme absent de tous les subtitles ne doit pas provoquer de faux positif."""
        repo = BookRepository(session)

        book_data = BookCreate(
            title="Livre quelconque",
            subtitle="Sous-titre quelconque",
            isbn="9785555555555",
        )
        repo.create(book_data, owner_id=test_user.id)
        session.commit()

        params = BookSearchParams(search="craftsman", skip=0, limit=100)
        results = repo.search_books(params, user_id=test_user.id)

        assert len(results) == 0, "Aucun résultat attendu pour un terme absent"


@pytest.mark.unit
class TestBookServiceSubtitleUpdate:
    """Tests du service — mise à jour du subtitle."""

    def test_update_book_subtitle(self, session: Session, test_user: User):
        """update_book() doit mettre à jour le subtitle et le persister."""
        book = create_test_book(session, test_user.id, "Mon Livre", "9782222222222")

        service = BookService(session, user_id=test_user.id)
        update_data = BookUpdate(subtitle="Nouveau sous-titre")
        updated = service.update_book(book.id, update_data)

        assert updated.subtitle == "Nouveau sous-titre"

        # Vérifier la persistance en base
        session.refresh(book)
        assert book.subtitle == "Nouveau sous-titre"

    def test_update_book_subtitle_to_none(self, session: Session, test_user: User):
        """update_book() doit pouvoir effacer le subtitle (None)."""
        book = create_test_book(session, test_user.id, "Livre avec subtitle", "9786666666666")
        # Ajouter un subtitle initial directement
        book.subtitle = "Sous-titre initial"
        session.commit()

        service = BookService(session, user_id=test_user.id)
        update_data = BookUpdate(subtitle=None)
        updated = service.update_book(book.id, update_data)

        session.refresh(book)
        assert book.subtitle is None


@pytest.mark.unit
class TestSuggestedBookSubtitle:
    """Tests de la classe SuggestedBook — sérialisation du subtitle."""

    def test_suggested_book_includes_subtitle(self):
        """SuggestedBook.model_dump() doit inclure le champ subtitle."""
        suggested = SuggestedBook(
            isbn="9787777777777",
            title="Clean Architecture",
            subtitle="A Craftsman's Guide",
        )
        data = suggested.model_dump()
        assert "subtitle" in data
        assert data["subtitle"] == "A Craftsman's Guide"

    def test_suggested_book_subtitle_none_by_default(self):
        """SuggestedBook sans subtitle doit avoir subtitle=None dans model_dump()."""
        suggested = SuggestedBook(isbn="9788888888888", title="Sans sous-titre")
        data = suggested.model_dump()
        assert "subtitle" in data
        assert data["subtitle"] is None


@pytest.mark.unit
@pytest.mark.scan
class TestScanServiceSubtitle:
    """Tests du ScanService — propagation du subtitle depuis Google Books."""

    @pytest.mark.asyncio
    @patch('app.services.scan_service.fetch_google_books')
    @patch('app.services.scan_service.fetch_openlibrary')
    async def test_scan_new_book_includes_google_subtitle(
        self, mock_openlibrary, mock_google_books, session: Session, test_user: User
    ):
        """scan_isbn() doit propager le subtitle Google Books vers SuggestedBook."""
        mock_google_books.return_value = ({
            "title": "Clean Architecture",
            "subtitle": "A Craftsman's Guide to Software Structure and Design",
            "authors": ["Robert C. Martin"],
        }, None)
        mock_openlibrary.return_value = (None, "unavailable")

        service = ScanService(session, user_id=test_user.id)
        result = await service.scan_isbn("9780134494166")

        assert result.suggested is not None
        assert result.suggested.subtitle == "A Craftsman's Guide to Software Structure and Design"

    @pytest.mark.asyncio
    @patch('app.services.scan_service.fetch_google_books')
    @patch('app.services.scan_service.fetch_openlibrary')
    async def test_scan_book_without_google_subtitle(
        self, mock_openlibrary, mock_google_books, session: Session, test_user: User
    ):
        """scan_isbn() doit avoir subtitle=None si Google Books ne retourne pas de subtitle."""
        mock_google_books.return_value = ({
            "title": "Livre sans sous-titre",
            "authors": ["Auteur quelconque"],
        }, None)
        mock_openlibrary.return_value = (None, "unavailable")

        service = ScanService(session, user_id=test_user.id)
        result = await service.scan_isbn("9789999999999")

        assert result.suggested is not None
        assert result.suggested.subtitle is None
