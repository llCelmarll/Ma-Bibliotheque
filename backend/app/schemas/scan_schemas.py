from typing import List
from sqlmodel import SQLModel
from app.schemas.book_schemas import BookRead
from app.schemas.borrowed_book_schemas import BorrowedBookRead


class SuggestedAuthor(SQLModel):
    """Auteur suggéré avec information d'existence"""
    name: str
    exists: bool = False
    id: int | None = None

class SuggestedPublisher(SQLModel):
    """Éditeur suggéré avec information d'existence"""
    name: str
    exists: bool = False
    id: int | None = None

class SuggestedGenre(SQLModel):
    """Genre suggéré avec information d'existence"""
    name: str
    exists: bool = False
    id: int | None = None

class SuggestedBook(SQLModel):
    """Modèle pour le livre suggéré dans le scan - avec entités enrichies"""
    isbn: str | None = None
    title: str | None = None
    subtitle: str | None = None
    published_date: str | None = None
    page_count: int | None = None
    barcode: str | None = None
    cover_url: str | None = None
    authors: List[SuggestedAuthor] = []
    publisher: SuggestedPublisher | None = None
    genres: List[SuggestedGenre] = []


class ScanResult(SQLModel):
    base : BookRead | None = None
    suggested : SuggestedBook | None = None
    title_match : List[BookRead] = []
    google_book : dict | None= None
    openlibrary : dict | None= None

    # Erreurs des services externes
    google_book_error: str | None = None
    openlibrary_error: str | None = None

    # Flags et données pour emprunts
    previously_borrowed: bool = False        # Tous emprunts sont RETURNED
    currently_borrowed: bool = False         # Au moins un emprunt ACTIVE/OVERDUE
    borrowed_book: BorrowedBookRead | None = None  # Détails emprunt actif
    can_add_to_library: bool = False         # Peut ajouter en possession permanente


class TitleSearchResult(SQLModel):
    """Résultat d'une recherche de livre par titre auprès de Google Books et OpenLibrary"""
    google_results: List[SuggestedBook] = []
    openlibrary_results: List[SuggestedBook] = []
    google_error: str | None = None
    openlibrary_error: str | None = None
    title_match: List[BookRead] = []  # Doublons potentiels déjà en bibliothèque
