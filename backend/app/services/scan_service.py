import asyncio
from sqlmodel import Session
from app.clients.google_books import fetch_google_books, search_google_books_by_title
from app.clients.openlibrary import fetch_openlibrary, search_openlibrary_by_title
from app.repositories.book_repository import BookRepository
from app.repositories.author_repository import AuthorRepository
from app.repositories.publisher_repository import PublisherRepository
from app.repositories.loan_repository import LoanRepository
from app.repositories.borrowed_book_repository import BorrowedBookRepository
from app.schemas.book_schemas import BookRead, CurrentLoanRead
from app.schemas.borrowed_book_schemas import BorrowedBookRead
from app.schemas.scan_schemas import (
    ScanResult,
    SuggestedAuthor,
    SuggestedPublisher,
    SuggestedGenre,
    SuggestedBook,
    TitleSearchResult,
)


class ScanService:
    """Service pour le scan de livres"""

    def __init__(self, session: Session, user_id: int = None):
        self.session = session
        self.user_id = user_id
        self.book_repository = BookRepository(session)
        self.author_repository = AuthorRepository(session)
        self.publisher_repository = PublisherRepository(session)
        self.loan_repository = LoanRepository(session)
        self.borrowed_book_repository = BorrowedBookRepository(session)



    async def scan_isbn(self, isbn: str):

        result = ScanResult()


        #Check si dans la base (pour l'utilisateur connecté uniquement)
        base_book = self.book_repository.get_by_isbn(isbn, user_id=self.user_id)


        #Check google_books et openLibrary
        google_data, google_error = await fetch_google_books(isbn)
        openlibrary_data, openlibrary_error = await fetch_openlibrary(isbn)
        result.google_book = google_data
        result.google_book_error = google_error
        result.openlibrary = openlibrary_data
        result.openlibrary_error = openlibrary_error

        if base_book:
            # Récupérer le prêt actif pour ce livre
            active_loan = self.loan_repository.get_active_loan_for_book(base_book.id, self.user_id)

            # Vérifier le statut d'emprunt
            has_only_returned, has_active, active_borrow = self.borrowed_book_repository.get_borrow_status(
                base_book.id,
                self.user_id
            )

            if has_only_returned:
                # Cas 1: Livre retourné - ne pas l'afficher comme possédé
                result.previously_borrowed = True
                result.can_add_to_library = True
                result.currently_borrowed = False
                result.base = None  # Ne pas inclure dans base
            elif has_active:
                # Cas 2: Livre actuellement emprunté
                result.currently_borrowed = True
                result.borrowed_book = BorrowedBookRead.model_validate(active_borrow)
                result.previously_borrowed = False
                result.can_add_to_library = False
                result.base = None  # Ne pas inclure dans base (pas possédé)
            else:
                # Cas 3: Livre possédé - comportement normal
                result.base = BookRead.model_validate(base_book)
                if active_loan:
                    result.base.current_loan = CurrentLoanRead.model_validate(active_loan)

            # Créer un SuggestedBook à partir du livre existant (dans tous les cas)
            result.suggested = SuggestedBook(
                isbn=base_book.isbn,
                title=base_book.title,
                subtitle=base_book.subtitle,
                published_date=base_book.published_date,
                page_count=base_book.page_count,
                barcode=base_book.barcode,
                cover_url=base_book.cover_url,
                authors=[
                    SuggestedAuthor(name=author.name, exists=True, id=author.id)
                    for author in base_book.authors
                ] if base_book.authors else [],
                publisher=SuggestedPublisher(
                    name=base_book.publisher.name,
                    exists=True,
                    id=base_book.publisher.id
                ) if base_book.publisher else None,
                genres=[
                    SuggestedGenre(name=genre.name, exists=True, id=genre.id)
                    for genre in base_book.genres
                ] if base_book.genres else []
            )
        else:
            # Récupération des données à suggerer
            google_title = result.google_book.get("title") if result.google_book else None
            google_subtitle = result.google_book.get("subtitle") if result.google_book else None
            google_date = result.google_book.get("publishedDate") if result.google_book else None
            google_pages = result.google_book.get("pageCount") if result.google_book else None
            google_cover = result.google_book.get("imageLinks", {}).get("thumbnail") if result.google_book else None
            google_publisher = result.google_book.get("publisher") if result.google_book else None

            openlibrary_title = result.openlibrary.get("title") if result.openlibrary else None
            openlibrary_date = result.openlibrary.get("publish_date") if result.openlibrary else None
            openlibrary_pages = result.openlibrary.get("number_of_pages") if result.openlibrary else None
            openlibrary_cover = f"https://covers.openlibrary.org/b/isbn/{isbn}-M.jpg" if result.openlibrary else None
            openlibrary_publisher = None
            if result.openlibrary and result.openlibrary.get("publishers") and len(result.openlibrary.get("publishers")) > 0:
                openlibrary_publisher = result.openlibrary.get("publishers")[0]

            # Gestion des auteurs avec vérification en base
            authors_list = []
            if result.google_book:
                if api_authors := result.google_book.get("authors"):
                    for api_author_name in api_authors:
                        # Vérifier si l'auteur existe déjà dans la base pour cet utilisateur
                        existing_author = self.author_repository.get_by_name(api_author_name)
                        if existing_author:
                            authors_list.append(SuggestedAuthor(
                                name=existing_author.name,
                                exists=True,
                                id=existing_author.id
                            ))
                            print(f"✅ Auteur trouvé en base: '{existing_author.name}' (API: '{api_author_name}')")
                        else:
                            authors_list.append(SuggestedAuthor(
                                name=api_author_name,
                                exists=False,
                                id=None
                            ))
                            print(f"🆕 Nouvel auteur détecté: '{api_author_name}'")

            # Récupération du nom de l'éditeur depuis les APIs
            api_publisher_name = google_publisher or openlibrary_publisher

            # Vérification si l'éditeur existe déjà dans la base de données pour cet utilisateur
            final_publisher = None
            if api_publisher_name:
                existing_publisher = self.publisher_repository.get_by_name(api_publisher_name)
                if existing_publisher:
                    final_publisher = SuggestedPublisher(
                        name=existing_publisher.name,
                        exists=True,
                        id=existing_publisher.id
                    )
                    print(f"✅ Éditeur trouvé en base: '{existing_publisher.name}' (API: '{api_publisher_name}')")
                else:
                    final_publisher = SuggestedPublisher(
                        name=api_publisher_name,
                        exists=False,
                        id=None
                    )
                    print(f"🆕 Nouvel éditeur détecté: '{api_publisher_name}'")

            # Forcer HTTPS pour les URLs de couverture (fix pour les apps mobiles)
            cover_url = google_cover or openlibrary_cover
            if cover_url and cover_url.startswith('http://'):
                cover_url = cover_url.replace('http://', 'https://', 1)

            result.suggested = SuggestedBook(
                isbn=isbn,
                title=google_title or openlibrary_title,
                subtitle=google_subtitle,
                published_date=google_date or openlibrary_date,
                page_count=google_pages or openlibrary_pages,
                barcode=isbn,
                cover_url=cover_url,
                authors=authors_list,
                publisher=final_publisher,
                genres=[],  # TODO: Enrichir les genres plus tard si nécessaire
            )

            if result.suggested and result.suggested.title:
                result.title_match = self.book_repository.search_title_match(title=result.suggested.title, isbn=isbn, user_id=self.user_id)

        return result

    def _enrich_authors(self, author_names: list[str]) -> list[SuggestedAuthor]:
        """Vérifie l'existence en base de chaque auteur et retourne la liste enrichie"""
        authors_list = []
        for api_author_name in author_names:
            existing_author = self.author_repository.get_by_name(api_author_name)
            if existing_author:
                authors_list.append(SuggestedAuthor(name=existing_author.name, exists=True, id=existing_author.id))
            else:
                authors_list.append(SuggestedAuthor(name=api_author_name, exists=False, id=None))
        return authors_list

    def _enrich_publisher(self, publisher_name: str | None) -> SuggestedPublisher | None:
        """Vérifie l'existence en base de l'éditeur et retourne l'objet enrichi"""
        if not publisher_name:
            return None
        existing_publisher = self.publisher_repository.get_by_name(publisher_name)
        if existing_publisher:
            return SuggestedPublisher(name=existing_publisher.name, exists=True, id=existing_publisher.id)
        return SuggestedPublisher(name=publisher_name, exists=False, id=None)

    def _google_item_to_suggested_book(self, item: dict) -> SuggestedBook:
        """Convertit un volumeInfo Google Books brut en SuggestedBook enrichi"""
        cover_url = item.get("imageLinks", {}).get("thumbnail")
        if cover_url and cover_url.startswith('http://'):
            cover_url = cover_url.replace('http://', 'https://', 1)

        isbn = None
        for identifier in item.get("industryIdentifiers", []) or []:
            if identifier.get("type") in ("ISBN_13", "ISBN_10"):
                isbn = identifier.get("identifier")
                break

        return SuggestedBook(
            isbn=isbn,
            title=item.get("title"),
            subtitle=item.get("subtitle"),
            published_date=item.get("publishedDate"),
            page_count=item.get("pageCount"),
            barcode=isbn,
            cover_url=cover_url,
            authors=self._enrich_authors(item.get("authors") or []),
            publisher=self._enrich_publisher(item.get("publisher")),
            genres=[],
        )

    def _openlibrary_doc_to_suggested_book(self, doc: dict) -> SuggestedBook:
        """Convertit un document de recherche OpenLibrary brut en SuggestedBook enrichi"""
        cover_i = doc.get("cover_i")
        cover_url = f"https://covers.openlibrary.org/b/id/{cover_i}-M.jpg" if cover_i else None

        isbn_list = doc.get("isbn") or []
        isbn = isbn_list[0] if isbn_list else None

        published_date = doc.get("first_publish_year")
        published_date = str(published_date) if published_date else None

        return SuggestedBook(
            isbn=isbn,
            title=doc.get("title"),
            subtitle=doc.get("subtitle"),
            published_date=published_date,
            page_count=None,
            barcode=isbn,
            cover_url=cover_url,
            authors=self._enrich_authors(doc.get("author_name") or []),
            publisher=None,
            genres=[],
        )

    async def search_by_title(self, title: str, max_results: int = 8) -> TitleSearchResult:
        """Recherche des livres par titre auprès de Google Books et OpenLibrary"""

        result = TitleSearchResult()

        (google_items, google_error), (openlibrary_docs, openlibrary_error) = await asyncio.gather(
            search_google_books_by_title(title, max_results),
            search_openlibrary_by_title(title, max_results),
        )

        result.google_error = google_error
        result.openlibrary_error = openlibrary_error
        result.google_results = [self._google_item_to_suggested_book(item) for item in (google_items or [])]
        result.openlibrary_results = [self._openlibrary_doc_to_suggested_book(doc) for doc in (openlibrary_docs or [])]
        result.title_match = self.book_repository.search_title_match(title=title, isbn="", user_id=self.user_id)

        return result
