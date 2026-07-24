// components/scan/TitleSearchSection.tsx
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, TextInput, Image, ActivityIndicator } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useTheme } from '@/contexts/ThemeContext';
import { scanApi } from '@/services/scanService';
import { SuggestedBook, TitleSearchResult } from '@/types/scanTypes';
import { SimilarBooksSection } from '@/components/scan/SimilarBooksSection';
import { TitleSearchResultCompare } from '@/components/scan/TitleSearchResultCompare';

interface TitleSearchSectionProps {
	onSelectResult: (suggested: SuggestedBook) => void;
	currentFormData: SuggestedBook;
}

export const TitleSearchSection: React.FC<TitleSearchSectionProps> = ({ onSelectResult, currentFormData }) => {
	const theme = useTheme();
	const [title, setTitle] = useState('');
	const [isSearching, setIsSearching] = useState(false);
	const [results, setResults] = useState<TitleSearchResult | null>(null);
	const [searchError, setSearchError] = useState<string | null>(null);
	const [activeTab, setActiveTab] = useState<'google' | 'openLibrary'>('google');
	const [comparingCandidate, setComparingCandidate] = useState<SuggestedBook | null>(null);

	const handleSearch = async () => {
		const trimmed = title.trim();
		if (!trimmed) return;

		setIsSearching(true);
		setSearchError(null);
		try {
			const result = await scanApi.searchByTitle(trimmed);
			setResults(result);
			if (result.google_results.length === 0 && result.openlibrary_results.length > 0) {
				setActiveTab('openLibrary');
			} else {
				setActiveTab('google');
			}
		} catch (error) {
			setSearchError(error instanceof Error ? error.message : 'Erreur lors de la recherche');
			setResults(null);
		} finally {
			setIsSearching(false);
		}
	};

	const renderErrorBanner = (error: string) => (
		<View style={[styles.errorBanner, { backgroundColor: theme.warningBg, borderColor: theme.warning }]}>
			<MaterialIcons name="warning" size={20} color={theme.warning} />
			<Text style={[styles.errorBannerText, { color: theme.warning }]}>{error}</Text>
		</View>
	);

	const renderResultCard = (book: SuggestedBook, index: number) => {
		const authorsText = book.authors.map(a => a.name).join(', ');
		const yearText = book.published_date ? book.published_date.slice(0, 4) : null;

		return (
			<TouchableOpacity
				key={`${book.isbn ?? book.title ?? 'result'}-${index}`}
				style={[styles.resultCard, { backgroundColor: theme.bgCard, borderColor: theme.borderLight }]}
				onPress={() => setComparingCandidate(book)}
				activeOpacity={0.7}
			>
				{book.cover_url ? (
					<Image source={{ uri: book.cover_url }} style={styles.cover} resizeMode="contain" />
				) : (
					<View style={[styles.coverPlaceholder, { backgroundColor: theme.bgSecondary }]}>
						<MaterialIcons name="menu-book" size={20} color={theme.textMuted} />
					</View>
				)}
				<View style={styles.resultInfo}>
					<Text style={[styles.resultTitle, { color: theme.textPrimary }]} numberOfLines={2}>
						{book.title || 'Titre inconnu'}
					</Text>
					{book.subtitle && (
						<Text style={[styles.resultSubtitle, { color: theme.textMuted }]} numberOfLines={1}>
							{book.subtitle}
						</Text>
					)}
					{authorsText ? (
						<Text style={[styles.resultMeta, { color: theme.textMuted }]} numberOfLines={1}>
							{authorsText}
						</Text>
					) : null}
					{yearText && (
						<Text style={[styles.resultMeta, { color: theme.textMuted }]}>{yearText}</Text>
					)}
				</View>
				<MaterialIcons name="chevron-right" size={22} color={theme.textMuted} />
			</TouchableOpacity>
		);
	};

	const renderResultsList = (books: SuggestedBook[], sourceName: string) => {
		if (books.length === 0) {
			return (
				<View style={styles.noResultsContainer}>
					<Text style={[styles.noResultsText, { color: theme.textMuted }]}>
						Aucun résultat sur {sourceName}
					</Text>
				</View>
			);
		}
		return <View style={styles.resultsList}>{books.map(renderResultCard)}</View>;
	};

	const hasResults = results && (results.google_results.length > 0 || results.openlibrary_results.length > 0);

	if (comparingCandidate) {
		return (
			<View style={styles.compareWrapper}>
				<TitleSearchResultCompare
					candidate={comparingCandidate}
					currentFormData={currentFormData}
					onApply={(merged) => {
						onSelectResult(merged);
						setComparingCandidate(null);
					}}
					onCancel={() => setComparingCandidate(null)}
				/>
			</View>
		);
	}

	return (
		<View style={[styles.container, { backgroundColor: theme.bgCard, borderColor: theme.borderLight }]}>
			<Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>🔎 Rechercher par titre</Text>
			<Text style={[styles.helperText, { color: theme.textMuted }]}>
				Pas d'ISBN sous la main ? Cherchez le livre par son titre pour pré-remplir le formulaire.
			</Text>

			<View style={styles.searchRow}>
				<TextInput
					style={[styles.searchInput, { color: theme.textPrimary, borderColor: theme.borderMedium, backgroundColor: theme.bgSecondary }]}
					placeholder="Titre du livre"
					placeholderTextColor={theme.textMuted}
					value={title}
					onChangeText={setTitle}
					onSubmitEditing={handleSearch}
					returnKeyType="search"
				/>
				<TouchableOpacity
					style={[styles.searchButton, { backgroundColor: theme.accent }, (!title.trim() || isSearching) && { opacity: 0.5 }]}
					onPress={handleSearch}
					disabled={!title.trim() || isSearching}
				>
					{isSearching ? (
						<ActivityIndicator size="small" color={theme.textInverse} />
					) : (
						<MaterialIcons name="search" size={20} color={theme.textInverse} />
					)}
				</TouchableOpacity>
			</View>

			{searchError && renderErrorBanner(searchError)}

			{results && (
				<>
					{results.google_error && renderErrorBanner(results.google_error)}
					{results.openlibrary_error && renderErrorBanner(results.openlibrary_error)}

					{results.title_match.length > 0 && (
						<SimilarBooksSection books={results.title_match} />
					)}

					{hasResults && (
						<>
							<View style={[styles.tabContainer, { backgroundColor: theme.bgMuted }]}>
								<TouchableOpacity
									style={[styles.tab, activeTab === 'google' && { backgroundColor: theme.accent }]}
									onPress={() => setActiveTab('google')}
								>
									<Text style={[styles.tabText, { color: theme.textMuted }, activeTab === 'google' && { color: theme.textInverse }]}>
										Google Books ({results.google_results.length})
									</Text>
								</TouchableOpacity>
								<TouchableOpacity
									style={[styles.tab, activeTab === 'openLibrary' && { backgroundColor: theme.accent }]}
									onPress={() => setActiveTab('openLibrary')}
								>
									<Text style={[styles.tabText, { color: theme.textMuted }, activeTab === 'openLibrary' && { color: theme.textInverse }]}>
										OpenLibrary ({results.openlibrary_results.length})
									</Text>
								</TouchableOpacity>
							</View>

							{activeTab === 'google'
								? renderResultsList(results.google_results, 'Google Books')
								: renderResultsList(results.openlibrary_results, 'OpenLibrary')}
						</>
					)}
				</>
			)}
		</View>
	);
};

const styles = StyleSheet.create({
	compareWrapper: {
		margin: 16,
		marginBottom: 8,
	},
	container: {
		padding: 16,
		borderRadius: 12,
		margin: 16,
		marginBottom: 8,
		borderWidth: 1,
	},
	sectionTitle: {
		fontSize: 18,
		fontWeight: '600',
		marginBottom: 4,
	},
	helperText: {
		fontSize: 13,
		marginBottom: 12,
	},
	searchRow: {
		flexDirection: 'row',
		gap: 8 as any,
	},
	searchInput: {
		flex: 1,
		borderWidth: 1,
		borderRadius: 8,
		paddingHorizontal: 12,
		paddingVertical: 10,
		fontSize: 15,
	},
	searchButton: {
		width: 44,
		height: 44,
		borderRadius: 8,
		alignItems: 'center',
		justifyContent: 'center',
	},
	errorBanner: {
		borderWidth: 1,
		borderRadius: 8,
		padding: 12,
		marginTop: 12,
		flexDirection: 'row',
		alignItems: 'center',
	},
	errorBannerText: {
		fontSize: 14,
		fontWeight: '500',
		marginLeft: 8,
		flex: 1,
	},
	tabContainer: {
		flexDirection: 'row',
		borderRadius: 8,
		padding: 4,
		marginTop: 12,
		marginBottom: 12,
	},
	tab: {
		flex: 1,
		paddingVertical: 8,
		paddingHorizontal: 12,
		borderRadius: 6,
		alignItems: 'center',
	},
	tabText: {
		fontSize: 13,
		fontWeight: '500',
	},
	resultsList: {
		gap: 8 as any,
	},
	resultCard: {
		flexDirection: 'row',
		alignItems: 'center',
		borderWidth: 1,
		borderRadius: 10,
		padding: 10,
		gap: 10 as any,
	},
	cover: {
		width: 40,
		height: 60,
		borderRadius: 4,
	},
	coverPlaceholder: {
		width: 40,
		height: 60,
		borderRadius: 4,
		alignItems: 'center',
		justifyContent: 'center',
	},
	resultInfo: {
		flex: 1,
	},
	resultTitle: {
		fontSize: 14,
		fontWeight: '600',
	},
	resultSubtitle: {
		fontSize: 12,
		marginTop: 2,
	},
	resultMeta: {
		fontSize: 12,
		marginTop: 2,
	},
	noResultsContainer: {
		padding: 16,
		alignItems: 'center',
	},
	noResultsText: {
		fontSize: 14,
		fontStyle: 'italic',
	},
});
