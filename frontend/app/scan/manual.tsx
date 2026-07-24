// app/scan/manual.tsx
import React, { useState, useEffect } from 'react';
import { View, ScrollView, StyleSheet, Text, Alert, Platform, TouchableOpacity, ActivityIndicator } from 'react-native';
import { useRouter, useLocalSearchParams } from 'expo-router';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { BookForm } from "@/components/scan/BookForm";
import { TitleSearchSection } from "@/components/scan/TitleSearchSection";
import { BookCreate, SuggestedBook } from "@/types/scanTypes";
import { bookService } from "@/services/bookService";
import { MaterialIcons } from '@expo/vector-icons';
import { useAuth } from "@/contexts/AuthContext";
import { ProtectedRoute } from "@/components/auth/ProtectedRoute";
import { useTheme } from '@/contexts/ThemeContext';

export default function ManualBookAddPage() {
  const router = useRouter();
  const insets = useSafeAreaInsets();
  const theme = useTheme();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { suggestedBook: suggestedBookParam, isbn, forceOwnership } = useLocalSearchParams<{
    suggestedBook?: string;
    isbn?: string;
    forceOwnership?: string;
  }>();

  // Parser le livre suggéré si fourni
  const [parsedSuggestedBook, setParsedSuggestedBook] = useState<SuggestedBook | null>(null);
  // Livre choisi via la recherche par titre (prioritaire sur parsedSuggestedBook)
  const [searchSelectedBook, setSearchSelectedBook] = useState<SuggestedBook | null>(null);
  const [searchFeedback, setSearchFeedback] = useState<string | null>(null);

  useEffect(() => {
    if (suggestedBookParam) {
      try {
        setParsedSuggestedBook(JSON.parse(suggestedBookParam));
      } catch (e) {
        console.error('Invalid suggestedBook JSON:', e);
      }
    }
  }, [suggestedBookParam]);

  const handleSelectSearchResult = (book: SuggestedBook) => {
    setSearchSelectedBook(book);
    setSearchFeedback(`Données importées : "${book.title || 'livre sélectionné'}"`);
    setTimeout(() => setSearchFeedback(null), 3000);
  };

  // Protection centralisée
  // Données vides pour le formulaire d'ajout manuel
  const emptyBookData: SuggestedBook = {
    title: '',
    isbn: isbn || '',
    published_date: '',
    page_count: undefined,
    barcode: '',
    cover_url: '',
    authors: [], // Array vide pour les auteurs
    publisher: undefined, // Pas d'éditeur par défaut
    genres: [], // Array vide pour les genres
  };

  const handleSubmit = async (values: BookCreate, localImageUri?: string | null) => {
    setIsSubmitting(true);
    try {
      console.log('Ajout manuel - donnees:', values);
      // Validation côté client
      const validation = bookService.validateBookData(values);
      if (!validation.isValid) {
        console.error('Validation echouee:', validation.errors);
        Alert.alert(
          'Erreur de validation',
          validation.errors.join('\n'),
          [{ text: 'OK' }]
        );
        return;
      }

      // Créer le livre via l'API
      const createdBook = await bookService.createBook(values);

      // Upload de la couverture si une image locale a ete selectionnee
      if (localImageUri && createdBook.id) {
        try {
          await bookService.uploadCover(String(createdBook.id), localImageUri);
        } catch (uploadErr: any) {
          console.warn('Upload couverture echoue:', uploadErr);
          const msg = uploadErr?.response?.data?.detail
            || uploadErr?.message
            || 'Erreur inconnue';
          Alert.alert(
            'Couverture non uploadée',
            `Le livre a été créé mais la couverture n'a pas pu être enregistrée : ${msg}`
          );
        }
      }

      console.log('Livre cree manuellement:', createdBook);
      // Message de succès avec navigation intelligente
      if (Platform.OS === 'web') {
        const goToBooks = confirm('✅ Livre ajouté avec succès !\n\nAller à la liste des livres ?');
        if (goToBooks) {
          router.push('/books');
        }
        // Sinon on reste sur la page pour ajouter un autre livre
      } else {
        Alert.alert(
          'Livre ajouté !',
          'Le livre a été ajouté à votre bibliothèque.',
          [
            {
              text: 'Liste des livres',
              onPress: () => router.push('/books')
            },
            {
              text: 'Voir le livre',
              onPress: () => router.push(`/books/${createdBook.id}`)
            },
            {
              text: 'Ajouter un autre',
              onPress: () => {
                // Rester sur la page pour ajouter un autre livre
              }
            }
          ]
        );
      }
    } catch (error) {
      console.error('❌ Erreur lors de l\'ajout manuel:', error);
      const errorMessage = error instanceof Error ? error.message : 'Erreur inconnue';
      if (Platform.OS === 'web') {
        alert(`❌ Erreur: ${errorMessage}`);
      } else {
        Alert.alert(
          'Erreur',
          `Impossible d'ajouter le livre: ${errorMessage}`,
          [{ text: 'OK' }]
        );
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <ProtectedRoute>
      <View style={[styles.container, { paddingTop: insets.top, backgroundColor: theme.bgSecondary }]}>
        {/* En-tête personnalisé */}
        <View style={[styles.header, { backgroundColor: theme.bgCard, borderBottomColor: theme.borderLight, shadowColor: theme.textPrimary }]}>
          <View style={styles.headerLeft}>
            <MaterialIcons name="menu-book" size={24} color={theme.accent} />
            <Text style={[styles.headerTitle, { color: theme.textPrimary }]}>Ajouter un livre manuellement</Text>
          </View>
          {/* Bouton retour vers la liste des livres */}
          <TouchableOpacity
            style={[styles.headerButton, { backgroundColor: theme.bgSecondary }]}
            onPress={() => router.push('/books')}
            activeOpacity={0.7}
            accessibilityLabel="Voir la liste des livres"
          >
            <MaterialIcons name="list" size={20} color={theme.accent} />
          </TouchableOpacity>
        </View>

        <ScrollView
          style={styles.scrollView}
          contentContainerStyle={styles.scrollContent}
          keyboardShouldPersistTaps="handled"
        >
          {/* Instructions pour l'utilisateur */}
          <View
            style={[
              styles.instructionsContainer,
              { backgroundColor: theme.bgCard, borderLeftColor: theme.accent, shadowColor: theme.textPrimary },
            ]}
          >
            <Text style={[styles.instructionsTitle, { color: theme.textPrimary }]}>
              📝 Saisie manuelle
            </Text>
            <Text style={[styles.instructionsText, { color: theme.textSecondary }]}>
              Remplissez les informations du livre. Seul le titre est obligatoire.
              Les auteurs, éditeurs et genres seront créés automatiquement s'ils n'existent pas.
            </Text>
          </View>

          {/* Recherche par titre (Google Books / OpenLibrary) */}
          <TitleSearchSection
            onSelectResult={handleSelectSearchResult}
            currentFormData={searchSelectedBook || parsedSuggestedBook || emptyBookData}
          />

          {searchFeedback && (
            <View style={[styles.feedbackBanner, { backgroundColor: theme.successBg, borderColor: theme.success }]}>
              <MaterialIcons name="check-circle" size={18} color={theme.success} />
              <Text style={[styles.feedbackText, { color: theme.success }]}>{searchFeedback}</Text>
            </View>
          )}

          {/* Formulaire d'ajout manuel */}
          <BookForm
            initialData={searchSelectedBook || parsedSuggestedBook || emptyBookData}
            onSubmit={handleSubmit}
            submitButtonText={isSubmitting ? "Ajout en cours..." : "Ajouter le livre"}
            submitButtonLoadingText="Ajout en cours..."
            disableInternalScroll={true}
            forceOwnership={forceOwnership === 'true'}
          />
        </ScrollView>
      </View>
    </ProtectedRoute>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingVertical: 15,
    borderBottomWidth: 1,
    ...Platform.select({
      ios: {
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 2,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  headerLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    flex: 1,
  },
  headerButton: {
    padding: 8,
    borderRadius: 20,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginLeft: 12,
  },
  scrollView: {
    flex: 1,
  },
  scrollContent: {
    paddingBottom: 100, // Espace pour le clavier
  },
  instructionsContainer: {
    margin: 16,
    padding: 16,
    borderRadius: 12,
    borderLeftWidth: 4,
    ...Platform.select({
      ios: {
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
      },
      android: {
        elevation: 2,
      },
    }),
  },
  instructionsTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 8,
  },
  instructionsText: {
    fontSize: 14,
    lineHeight: 20,
  },
  feedbackBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    marginHorizontal: 16,
    marginBottom: 8,
    padding: 12,
    borderRadius: 8,
    borderWidth: 1,
  },
  feedbackText: {
    marginLeft: 8,
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  authContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  authText: {
    marginTop: 16,
    fontSize: 16,
    textAlign: 'center',
  },
});
