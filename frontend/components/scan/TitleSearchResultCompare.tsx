// components/scan/TitleSearchResultCompare.tsx
import React, { useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image } from 'react-native';
import { MaterialIcons } from '@expo/vector-icons';
import { useTheme } from '@/contexts/ThemeContext';
import { SuggestedBook } from '@/types/scanTypes';

interface TitleSearchResultCompareProps {
	candidate: SuggestedBook;
	currentFormData: SuggestedBook;
	onApply: (merged: SuggestedBook) => void;
	onCancel: () => void;
}

type FieldStatus = 'new' | 'different' | 'identical';

type FieldKey = 'title' | 'subtitle' | 'authors' | 'publisher' | 'published_date' | 'page_count' | 'cover_url';

const FIELD_LABELS: Record<FieldKey, string> = {
	title: 'Titre',
	subtitle: 'Sous-titre',
	authors: 'Auteur(s)',
	publisher: 'Éditeur',
	published_date: 'Date de publication',
	page_count: 'Nombre de pages',
	cover_url: 'Couverture',
};

const SORT_ORDER: Record<FieldStatus, number> = { new: 0, different: 1, identical: 2 };

const normalizeStr = (v: any): string => (v == null ? '' : String(v).trim().toLowerCase());

export const TitleSearchResultCompare: React.FC<TitleSearchResultCompareProps> = ({
	candidate,
	currentFormData,
	onApply,
	onCancel,
}) => {
	const theme = useTheme();

	const getCandidateValue = (field: FieldKey): any => {
		if (field === 'authors') return candidate.authors?.map(a => a.name) ?? [];
		if (field === 'publisher') return candidate.publisher?.name ?? null;
		return (candidate as any)[field];
	};

	const getCurrentValue = (field: FieldKey): any => {
		if (field === 'authors') return currentFormData.authors?.map(a => a.name) ?? [];
		if (field === 'publisher') return currentFormData.publisher?.name ?? null;
		return (currentFormData as any)[field];
	};

	const isEmpty = (v: any, field: FieldKey): boolean =>
		v == null || v === '' || (Array.isArray(v) && v.length === 0) || (field === 'page_count' && v === 0);

	const getFieldStatus = (field: FieldKey): FieldStatus => {
		const currentVal = getCurrentValue(field);
		if (isEmpty(currentVal, field)) return 'new';

		const candidateVal = getCandidateValue(field);
		if (field === 'authors') {
			const a = [...(candidateVal as string[])].map(normalizeStr).sort().join('|');
			const b = [...(currentVal as string[])].map(normalizeStr).sort().join('|');
			return a === b ? 'identical' : 'different';
		}
		return normalizeStr(candidateVal) === normalizeStr(currentVal) ? 'identical' : 'different';
	};

	const fields = (Object.keys(FIELD_LABELS) as FieldKey[])
		.filter(field => !isEmpty(getCandidateValue(field), field));

	const initialSelection: Record<string, boolean> = {};
	fields.forEach(field => {
		initialSelection[field] = getFieldStatus(field) !== 'identical';
	});

	const [selection, setSelection] = useState<Record<string, boolean>>(initialSelection);

	const selectableFields = fields.filter(field => getFieldStatus(field) !== 'identical');
	const selectedCount = selectableFields.filter(field => selection[field]).length;

	const toggle = (field: FieldKey) => {
		if (getFieldStatus(field) === 'identical') return;
		setSelection(prev => ({ ...prev, [field]: !prev[field] }));
	};

	const selectAll = () => {
		const next: Record<string, boolean> = { ...selection };
		selectableFields.forEach(field => { next[field] = true; });
		setSelection(next);
	};

	const deselectAll = () => {
		const next: Record<string, boolean> = { ...selection };
		selectableFields.forEach(field => { next[field] = false; });
		setSelection(next);
	};

	const handleApply = () => {
		const merged: SuggestedBook = { ...currentFormData };
		selectableFields.forEach(field => {
			if (!selection[field]) return;
			if (field === 'authors') {
				merged.authors = candidate.authors;
			} else if (field === 'publisher') {
				merged.publisher = candidate.publisher;
			} else {
				(merged as any)[field] = (candidate as any)[field];
			}
		});
		onApply(merged);
	};

	const formatValue = (field: FieldKey, value: any): React.ReactNode => {
		if (isEmpty(value, field)) {
			return <Text style={[styles.valueText, { color: theme.textMuted, fontStyle: 'italic' }]}>—</Text>;
		}
		if (field === 'authors') {
			return (
				<View style={styles.chipsContainer}>
					{(value as string[]).map(name => (
						<View key={name} style={[styles.chip, { backgroundColor: theme.bgSecondary, borderColor: theme.borderMedium }]}>
							<Text style={[styles.chipText, { color: theme.textPrimary }]}>{name}</Text>
						</View>
					))}
				</View>
			);
		}
		if (field === 'cover_url') {
			return <Image source={{ uri: value }} style={styles.thumbnail} resizeMode="contain" />;
		}
		return <Text style={[styles.valueText, { color: theme.textPrimary }]}>{String(value)}</Text>;
	};

	const renderCard = (field: FieldKey) => {
		const status = getFieldStatus(field);
		const isIdentical = status === 'identical';
		const isSelected = !!selection[field];

		const borderColor = isIdentical ? theme.borderLight : status === 'new' ? theme.success : theme.warning;
		const statusIcon = isIdentical ? 'check-circle' : status === 'new' ? 'add-circle' : 'swap-horiz';
		const statusColor = isIdentical ? theme.textMuted : status === 'new' ? theme.success : theme.warning;

		return (
			<TouchableOpacity
				key={field}
				style={[
					styles.card,
					{ borderLeftColor: borderColor, backgroundColor: theme.bgCard },
					isIdentical && { opacity: 0.6 },
					isSelected && { backgroundColor: theme.successBg, borderColor: theme.success, borderWidth: 1.5 },
				]}
				onPress={() => toggle(field)}
				activeOpacity={isIdentical ? 1 : 0.7}
			>
				<View style={styles.cardHeader}>
					<MaterialIcons name={statusIcon as any} size={16} color={statusColor} />
					<Text style={[styles.cardLabel, { color: theme.textMuted }]}>{FIELD_LABELS[field]}</Text>
					<MaterialIcons
						name={isIdentical ? 'remove' : isSelected ? 'check-box' : 'check-box-outline-blank'}
						size={20}
						color={isIdentical ? theme.textMuted : isSelected ? theme.success : theme.borderMedium}
						style={styles.checkbox}
					/>
				</View>

				<View style={styles.columns}>
					<View style={[styles.column, { borderColor: theme.borderLight }]}>
						<View style={[styles.columnBadge, { backgroundColor: theme.bgSecondary }]}>
							<Text style={[styles.columnBadgeText, { color: theme.textMuted }]}>Actuel</Text>
						</View>
						{formatValue(field, getCurrentValue(field))}
					</View>
					<View style={[styles.column, { borderColor: theme.accent + '44' }]}>
						<View style={[styles.columnBadge, { backgroundColor: theme.accentLight }]}>
							<Text style={[styles.columnBadgeText, { color: theme.accent }]}>Résultat choisi</Text>
						</View>
						{formatValue(field, getCandidateValue(field))}
					</View>
				</View>

				{isIdentical && (
					<Text style={[styles.identicalLabel, { color: theme.textMuted }]}>Identique — aucune modification nécessaire</Text>
				)}
			</TouchableOpacity>
		);
	};

	const sortedFields = [...fields].sort((a, b) => SORT_ORDER[getFieldStatus(a)] - SORT_ORDER[getFieldStatus(b)]);

	return (
		<View style={[styles.container, { backgroundColor: theme.bgCard, borderColor: theme.borderLight }]}>
			<View style={styles.headerRow}>
				<TouchableOpacity onPress={onCancel} style={styles.backButton}>
					<MaterialIcons name="arrow-back" size={20} color={theme.accent} />
					<Text style={[styles.backButtonText, { color: theme.accent }]}>Retour aux résultats</Text>
				</TouchableOpacity>
			</View>

			<Text style={[styles.sectionTitle, { color: theme.textPrimary }]} numberOfLines={2}>
				{candidate.title || 'Résultat sélectionné'}
			</Text>

			<View style={styles.cardsContainer}>
				{sortedFields.map(renderCard)}
			</View>

			{selectableFields.length > 0 && (
				<View style={styles.selectionLinks}>
					<TouchableOpacity onPress={selectAll}>
						<Text style={[styles.selectionLinkText, { color: theme.accent }]}>Tout sélectionner</Text>
					</TouchableOpacity>
					<Text style={[styles.selectionLinkSep, { color: theme.borderMedium }]}>·</Text>
					<TouchableOpacity onPress={deselectAll}>
						<Text style={[styles.selectionLinkText, { color: theme.textMuted }]}>Tout désélectionner</Text>
					</TouchableOpacity>
				</View>
			)}

			<TouchableOpacity
				style={[styles.applyButton, { backgroundColor: selectedCount > 0 ? theme.success : theme.borderMedium }]}
				onPress={handleApply}
				disabled={selectedCount === 0}
			>
				<MaterialIcons name="download" size={18} color={theme.textInverse} />
				<Text style={[styles.applyButtonText, { color: theme.textInverse }]}>
					Appliquer les champs sélectionnés ({selectedCount})
				</Text>
			</TouchableOpacity>
		</View>
	);
};

const styles = StyleSheet.create({
	container: {
		padding: 16,
		borderRadius: 12,
		borderWidth: 1,
	},
	headerRow: {
		marginBottom: 8,
	},
	backButton: {
		flexDirection: 'row',
		alignItems: 'center',
		gap: 4 as any,
		alignSelf: 'flex-start',
	},
	backButtonText: {
		fontSize: 13,
		fontWeight: '500',
	},
	sectionTitle: {
		fontSize: 16,
		fontWeight: '600',
		marginBottom: 12,
	},
	cardsContainer: {
		gap: 10 as any,
	},
	card: {
		borderRadius: 8,
		padding: 12,
		borderLeftWidth: 4,
	},
	cardHeader: {
		flexDirection: 'row',
		alignItems: 'center',
		marginBottom: 8,
		gap: 6 as any,
	},
	cardLabel: {
		fontSize: 11,
		fontWeight: '700',
		textTransform: 'uppercase',
		flex: 1,
		letterSpacing: 0.5,
	},
	checkbox: {
		marginLeft: 'auto' as any,
	},
	columns: {
		flexDirection: 'row',
		gap: 8 as any,
	},
	column: {
		flex: 1,
		borderRadius: 6,
		borderWidth: 1,
		overflow: 'hidden',
	},
	columnBadge: {
		paddingHorizontal: 8,
		paddingVertical: 4,
	},
	columnBadgeText: {
		fontSize: 10,
		fontWeight: '700',
		textTransform: 'uppercase',
		letterSpacing: 0.5,
	},
	valueText: {
		fontSize: 13,
		lineHeight: 18,
		paddingHorizontal: 8,
		paddingVertical: 6,
	},
	identicalLabel: {
		fontSize: 11,
		fontStyle: 'italic',
		textAlign: 'center',
		marginTop: 6,
	},
	thumbnail: {
		width: 50,
		height: 75,
		borderRadius: 4,
		margin: 8,
		alignSelf: 'center',
	},
	chipsContainer: {
		flexDirection: 'row',
		flexWrap: 'wrap',
		gap: 4 as any,
		paddingHorizontal: 8,
		paddingVertical: 6,
	},
	chip: {
		paddingHorizontal: 7,
		paddingVertical: 3,
		borderRadius: 10,
		borderWidth: 1,
	},
	chipText: {
		fontSize: 11,
		fontWeight: '500',
	},
	selectionLinks: {
		flexDirection: 'row',
		alignItems: 'center',
		justifyContent: 'center',
		gap: 8 as any,
		paddingVertical: 10,
	},
	selectionLinkText: {
		fontSize: 12,
		textDecorationLine: 'underline',
	},
	selectionLinkSep: {
		fontSize: 14,
	},
	applyButton: {
		flexDirection: 'row',
		alignItems: 'center',
		justifyContent: 'center',
		gap: 8 as any,
		paddingVertical: 14,
		paddingHorizontal: 20,
		borderRadius: 10,
	},
	applyButtonText: {
		fontSize: 15,
		fontWeight: '600',
	},
});
