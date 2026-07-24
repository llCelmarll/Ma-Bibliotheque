// services/api/types.ts

// Import des types de prêt et d'emprunt pour éviter les dépendances circulaires
import { BorrowedBook } from './borrowedBook';
import { ReadingStatus } from './book';

export interface LoanRead {
	id: number;
	book_id: number;
	contact_id: number;
	contact?: {
		id: number;
		name: string;
		email?: string;
		phone?: string;
	};
	loan_date: string;
	due_date?: string;
	return_date?: string;
	notes?: string;
	status: 'active' | 'returned' | 'overdue';
}

export interface BookRead {
	id: string;
	title: string;
	subtitle?: string;
	isbn?: string;
	published_date?: string;  // Aligné avec le backend
	page_count?: number;      // Aligné avec le backend
	barcode?: string;
	cover_url?: string;       // Aligné avec le backend
	created_at?: string;      // Aligné avec le backend
	updated_at?: string;      // Aligné avec le backend
	authors?: AuthorRead[];
	publisher?: PublisherRead;
	genres?: GenreRead[];
	series?: { id: number; name: string; volume_number?: number }[];
	reading_status?: ReadingStatus | null;  // Statut de lecture (null = non renseigné)
	read_date?: string;                     // Date de lecture
	rating?: number | null;       // Notation 0-5
	notes?: string | null;        // Notes personnelles
	current_loan?: LoanRead;  // Prêt actif (TO other) - livre prêté à quelqu'un
	borrowed_book?: BorrowedBook;  // Emprunt actif (FROM other) - livre emprunté de quelqu'un
}

export interface BookCreate {
	title: string;
	subtitle?: string;
	isbn?: string;
	published_date?: string;  // Aligné avec le backend
	page_count?: number;      // Aligné avec le backend
	barcode?: string;
	cover_url?: string;       // Aligné avec le backend
	authors?: (number | string | {name: string; id?: number; exists?: boolean})[];
	publisher?: number | string | {name: string; id?: number; exists?: boolean};
	genres?: (number | string | {name: string; id?: number; exists?: boolean})[];
	series?: (number | string | {name: string; id?: number; exists?: boolean; volume_number?: number})[];

	// Statut de lecture
	reading_status?: ReadingStatus | null;
	read_date?: string;

	// Notation et notes
	rating?: number | null;
	notes?: string | null;

	// Champs d'emprunt
	is_borrowed?: boolean;
	contact?: number | string | { name: string; email?: string; phone?: string; notes?: string };
	borrowed_from?: string; // Legacy
	borrowed_date?: string;  // Format: YYYY-MM-DD
	expected_return_date?: string;  // Format: YYYY-MM-DD
	borrow_notes?: string;
}

// Types enrichis pour les entités suggérées
export interface SuggestedAuthor {
	name: string;
	exists: boolean;
	id?: number;
}

export interface SuggestedPublisher {
	name: string;
	exists: boolean;
	id?: number;
}

export interface SuggestedGenre {
	name: string;
	exists: boolean;
	id?: number;
}

// Nouveau type pour le livre suggéré dans le scan - correspond au backend enrichi
export interface SuggestedSeries {
	name: string;
	exists: boolean;
	id?: number;
	volume_number?: number;
}

export interface SuggestedBook {
	isbn?: string;
	title?: string;
	subtitle?: string;
	published_date?: string;
	page_count?: number;
	barcode?: string;
	cover_url?: string;
	authors: SuggestedAuthor[];
	publisher?: SuggestedPublisher;
	genres: SuggestedGenre[];
	series?: SuggestedSeries[];
	reading_status?: ReadingStatus | null;
	read_date?: string;
	rating?: number | null;
	notes?: string | null;
}

export interface ScanResult {
	base?: BookRead;
	suggested?: SuggestedBook;  // Changé de BookCreate à SuggestedBook
	title_match: BookRead[];    // Plus nullable
	google_book?: any;
	openlibrary?: any;

	// Erreurs des services externes
	google_book_error?: string;
	openlibrary_error?: string;

	// Statut emprunt
	previously_borrowed?: boolean;      // Tous emprunts RETURNED
	currently_borrowed?: boolean;       // Au moins un emprunt ACTIVE/OVERDUE
	borrowed_book?: import('./borrowedBook').BorrowedBook;  // Détails emprunt actif
	can_add_to_library?: boolean;       // Peut ajouter en possession
}

export interface TitleSearchResult {
	google_results: SuggestedBook[];
	openlibrary_results: SuggestedBook[];
	google_error?: string;
	openlibrary_error?: string;
	title_match: BookRead[];
}

export interface AuthorRead {
	id: number;
	name: string;
}

export interface AuthorCreate {
	name: string;
}

export interface GenreRead {
	id: number;
	name: string;
}

export interface GenreCreate {
	name: string;
}

export interface PublisherRead {
	id: number;
	name: string;
}

export interface PublisherCreate {
	name: string;
}

export interface SeriesRead {
	id: number;
	name: string;
}

export interface SeriesCreate {
	name: string;
}
