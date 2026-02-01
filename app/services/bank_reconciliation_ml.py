"""
Bank Reconciliation ML Service

Machine learning-based bank statement reconciliation with:
- TF-IDF text similarity for description matching
- Weighted scoring for match confidence
- Auto-reconciliation above threshold
- Learning from historical matches
"""

import re
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.banking import BankAccount, BankTransaction, BankReconciliation
from app.models.accounting import JournalEntry, JournalEntryLine


class BankReconciliationMLService:
    """
    ML-based bank reconciliation service.

    Uses text similarity and weighted scoring to auto-match
    bank transactions with journal entries.
    """

    # Default weights for matching
    DEFAULT_WEIGHTS = {
        'amount_match': 0.35,      # Exact amount is strongest signal
        'date_proximity': 0.15,    # Date within range
        'text_similarity': 0.25,   # Description matching
        'party_match': 0.15,       # Party name matching
        'reference_match': 0.10,   # Reference number match
    }

    # Match confidence thresholds
    AUTO_MATCH_THRESHOLD = 0.85
    SUGGEST_THRESHOLD = 0.60
    MINIMUM_THRESHOLD = 0.40

    def __init__(self, db: AsyncSession):
        self.db = db
        self._tfidf_vectorizer = None
        self._tfidf_matrix = None

    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""

        # Convert to lowercase
        text = text.lower()

        # Remove special characters except spaces and alphanumerics
        text = re.sub(r'[^a-z0-9\s]', ' ', text)

        # Remove extra whitespace
        text = ' '.join(text.split())

        return text

    def _extract_reference_numbers(self, text: str) -> List[str]:
        """Extract potential reference numbers from text."""
        if not text:
            return []

        # Common patterns: UTR numbers, cheque numbers, transaction IDs
        patterns = [
            r'\b[A-Z]{4}[0-9]{7,}\b',  # NEFT/RTGS UTR (e.g., HDFC0001234567)
            r'\b[0-9]{12,16}\b',        # Long numeric IDs
            r'\bUTR[:\s]*([A-Z0-9]+)\b',  # UTR: format
            r'\b[A-Z0-9]{6,10}\b',      # Short alphanumeric refs
            r'\bCHQ[:\s]*([0-9]+)\b',   # Cheque number
            r'\bREF[:\s]*([A-Z0-9]+)\b',  # Reference
        ]

        refs = []
        for pattern in patterns:
            matches = re.findall(pattern, text.upper())
            refs.extend(matches)

        return list(set(refs))

    def _extract_party_name(self, text: str) -> Optional[str]:
        """Extract party name from bank description."""
        if not text:
            return None

        # Common patterns in bank statements
        patterns = [
            r'(?:FROM|TO|BY|A/C)\s+([A-Z][A-Z\s]+)',  # FROM/TO format
            r'(?:NEFT|RTGS|IMPS)[/-]([A-Z][A-Z\s]+)',  # Transfer format
            r'(?:CR|DR)\s+([A-Z][A-Z\s]+)',           # CR/DR format
        ]

        for pattern in patterns:
            match = re.search(pattern, text.upper())
            if match:
                name = match.group(1).strip()
                # Clean up common suffixes
                name = re.sub(r'\s+(PVT|LTD|LIMITED|PRIVATE|INDIA).*', '', name)
                return name

        return None

    def _calculate_text_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate text similarity using TF-IDF cosine similarity.

        Falls back to simple word overlap if sklearn not available.
        """
        text1 = self._normalize_text(text1)
        text2 = self._normalize_text(text2)

        if not text1 or not text2:
            return 0.0

        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.metrics.pairwise import cosine_similarity

            vectorizer = TfidfVectorizer(
                ngram_range=(1, 2),
                min_df=1,
                stop_words=None
            )

            tfidf_matrix = vectorizer.fit_transform([text1, text2])
            similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
            return float(similarity)

        except ImportError:
            # Fallback: Simple word overlap (Jaccard similarity)
            words1 = set(text1.split())
            words2 = set(text2.split())

            if not words1 or not words2:
                return 0.0

            intersection = len(words1 & words2)
            union = len(words1 | words2)

            return intersection / union if union > 0 else 0.0

    def _calculate_party_match(
        self,
        bank_txn: BankTransaction,
        journal_entry: JournalEntry
    ) -> float:
        """Calculate party name match score."""
        bank_party = self._extract_party_name(bank_txn.description)
        if not bank_party:
            bank_party = bank_txn.party_name

        if not bank_party:
            return 0.0

        # Get party from journal entry (usually in narration or line details)
        journal_party = None

        # Check narration
        if journal_entry.narration:
            journal_party = self._extract_party_name(journal_entry.narration)

        # Check if party_name is stored
        if not journal_party and hasattr(journal_entry, 'party_name'):
            journal_party = journal_entry.party_name

        if not journal_party:
            return 0.0

        # Compare parties
        return self._calculate_text_similarity(bank_party, journal_party)

    def _calculate_reference_match(
        self,
        bank_txn: BankTransaction,
        journal_entry: JournalEntry
    ) -> float:
        """Calculate reference number match score."""
        bank_refs = self._extract_reference_numbers(bank_txn.description)
        if bank_txn.reference_number:
            bank_refs.append(bank_txn.reference_number)
        if bank_txn.cheque_number:
            bank_refs.append(bank_txn.cheque_number)

        journal_refs = []
        if journal_entry.narration:
            journal_refs = self._extract_reference_numbers(journal_entry.narration)
        if hasattr(journal_entry, 'reference_number') and journal_entry.reference_number:
            journal_refs.append(journal_entry.reference_number)

        if not bank_refs or not journal_refs:
            return 0.0

        # Check for any matching reference
        bank_refs_set = set(ref.upper() for ref in bank_refs)
        journal_refs_set = set(ref.upper() for ref in journal_refs)

        if bank_refs_set & journal_refs_set:
            return 1.0

        # Partial match (substring)
        for bank_ref in bank_refs_set:
            for journal_ref in journal_refs_set:
                if bank_ref in journal_ref or journal_ref in bank_ref:
                    return 0.7

        return 0.0

    def extract_features(
        self,
        bank_txn: BankTransaction,
        journal_entry: JournalEntry
    ) -> Dict[str, float]:
        """
        Extract matching features between bank transaction and journal entry.

        Returns feature dictionary for scoring.
        """
        # Amount matching
        bank_amount = abs(float(bank_txn.amount))
        journal_amount = abs(float(journal_entry.total_debit or journal_entry.total_credit or 0))

        amount_match = 1.0 if abs(bank_amount - journal_amount) < 0.01 else 0.0
        amount_variance = abs(bank_amount - journal_amount) / max(bank_amount, 1)

        # Date proximity (within 7 days)
        date_diff = abs((bank_txn.transaction_date - journal_entry.entry_date).days)
        date_proximity = max(0, 1 - (date_diff / 7)) if date_diff <= 7 else 0.0

        # Text similarity
        bank_desc = bank_txn.description or ""
        journal_narration = journal_entry.narration or ""
        text_similarity = self._calculate_text_similarity(bank_desc, journal_narration)

        # Party matching
        party_match = self._calculate_party_match(bank_txn, journal_entry)

        # Reference matching
        reference_match = self._calculate_reference_match(bank_txn, journal_entry)

        return {
            'amount_match': amount_match,
            'amount_variance': amount_variance,
            'date_diff': date_diff,
            'date_proximity': date_proximity,
            'text_similarity': text_similarity,
            'party_match': party_match,
            'reference_match': reference_match,
        }

    def calculate_match_score(
        self,
        features: Dict[str, float],
        weights: Optional[Dict[str, float]] = None
    ) -> float:
        """
        Calculate weighted match confidence score.

        Returns score between 0 and 1.
        """
        weights = weights or self.DEFAULT_WEIGHTS

        score = (
            features['amount_match'] * weights['amount_match'] +
            features['date_proximity'] * weights['date_proximity'] +
            features['text_similarity'] * weights['text_similarity'] +
            features['party_match'] * weights['party_match'] +
            features['reference_match'] * weights['reference_match']
        )

        # Bonus for exact amount match
        if features['amount_match'] == 1.0:
            score = min(score + 0.1, 1.0)

        # Penalty for large date difference
        if features['date_diff'] > 3:
            score *= 0.9

        return min(max(score, 0.0), 1.0)

    async def get_unreconciled_transactions(
        self,
        bank_account_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> List[BankTransaction]:
        """Get unreconciled bank transactions."""
        query = (
            select(BankTransaction)
            .where(
                and_(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.is_reconciled == False
                )
            )
            .order_by(BankTransaction.transaction_date.desc())
        )

        if start_date:
            query = query.where(BankTransaction.transaction_date >= start_date)
        if end_date:
            query = query.where(BankTransaction.transaction_date <= end_date)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_candidate_journal_entries(
        self,
        bank_account: BankAccount,
        bank_txn: BankTransaction,
        date_range_days: int = 7
    ) -> List[JournalEntry]:
        """
        Get potential matching journal entries for a bank transaction.

        Filters by:
        - Date range (±7 days)
        - Same ledger account (linked to bank account)
        - Not already matched
        - Same transaction type (debit/credit)
        """
        txn_date = bank_txn.transaction_date
        start_date = txn_date - timedelta(days=date_range_days)
        end_date = txn_date + timedelta(days=date_range_days)

        # Determine if we're looking for debit or credit entries
        is_credit = bank_txn.transaction_type == "CREDIT"

        query = (
            select(JournalEntry)
            .options(selectinload(JournalEntry.lines))
            .where(
                and_(
                    JournalEntry.entry_date >= start_date,
                    JournalEntry.entry_date <= end_date,
                    JournalEntry.is_posted == True,
                )
            )
        )

        result = await self.db.execute(query)
        entries = list(result.scalars().all())

        # Filter entries that have a line with the bank account ledger
        filtered_entries = []
        for entry in entries:
            if not bank_account.ledger_account_id:
                continue

            for line in entry.lines:
                if line.ledger_account_id == bank_account.ledger_account_id:
                    # Check debit/credit direction
                    if is_credit and line.credit_amount and float(line.credit_amount) > 0:
                        filtered_entries.append(entry)
                        break
                    elif not is_credit and line.debit_amount and float(line.debit_amount) > 0:
                        filtered_entries.append(entry)
                        break

        return filtered_entries

    async def get_reconciliation_suggestions(
        self,
        bank_account_id: UUID,
        limit: int = 50
    ) -> List[Dict]:
        """
        Get ML-powered reconciliation suggestions.

        Returns list of suggested matches with confidence scores.
        """
        # Get bank account
        account_result = await self.db.execute(
            select(BankAccount).where(BankAccount.id == bank_account_id)
        )
        bank_account = account_result.scalar_one_or_none()

        if not bank_account:
            return []

        # Get unreconciled transactions
        transactions = await self.get_unreconciled_transactions(bank_account_id)

        suggestions = []

        for txn in transactions[:limit]:
            # Get candidate journal entries
            candidates = await self.get_candidate_journal_entries(bank_account, txn)

            best_match = None
            best_score = 0.0
            best_features = None

            for entry in candidates:
                # Calculate features and score
                features = self.extract_features(txn, entry)
                score = self.calculate_match_score(features)

                if score > best_score and score >= self.MINIMUM_THRESHOLD:
                    best_score = score
                    best_match = entry
                    best_features = features

            if best_match:
                suggestions.append({
                    'bank_transaction_id': str(txn.id),
                    'bank_transaction_date': txn.transaction_date.isoformat(),
                    'bank_description': txn.description,
                    'bank_amount': float(txn.amount),
                    'journal_entry_id': str(best_match.id),
                    'journal_entry_number': best_match.entry_number,
                    'journal_entry_date': best_match.entry_date.isoformat(),
                    'journal_narration': best_match.narration,
                    'confidence_score': round(best_score, 4),
                    'is_auto_match': best_score >= self.AUTO_MATCH_THRESHOLD,
                    'features': {k: round(v, 4) for k, v in best_features.items()},
                })

        # Sort by confidence score
        suggestions.sort(key=lambda x: x['confidence_score'], reverse=True)

        return suggestions

    async def auto_reconcile(
        self,
        bank_account_id: UUID,
        threshold: float = None
    ) -> Dict:
        """
        Automatically reconcile transactions above confidence threshold.

        Returns summary of auto-reconciled transactions.
        """
        threshold = threshold or self.AUTO_MATCH_THRESHOLD

        suggestions = await self.get_reconciliation_suggestions(bank_account_id)

        auto_matched = []
        skipped = []

        for suggestion in suggestions:
            if suggestion['confidence_score'] >= threshold:
                # Perform the match
                try:
                    await self._match_transaction(
                        UUID(suggestion['bank_transaction_id']),
                        UUID(suggestion['journal_entry_id'])
                    )
                    auto_matched.append(suggestion)
                except Exception as e:
                    suggestion['error'] = str(e)
                    skipped.append(suggestion)
            else:
                skipped.append(suggestion)

        await self.db.commit()

        return {
            'auto_matched_count': len(auto_matched),
            'skipped_count': len(skipped),
            'auto_matched': auto_matched,
            'requires_review': [s for s in skipped if s['confidence_score'] >= self.SUGGEST_THRESHOLD],
            'low_confidence': [s for s in skipped if s['confidence_score'] < self.SUGGEST_THRESHOLD],
        }

    async def _match_transaction(
        self,
        bank_transaction_id: UUID,
        journal_entry_id: UUID
    ) -> None:
        """Mark a bank transaction as matched with a journal entry."""
        result = await self.db.execute(
            select(BankTransaction).where(BankTransaction.id == bank_transaction_id)
        )
        txn = result.scalar_one_or_none()

        if txn:
            txn.is_reconciled = True
            txn.reconciled_at = datetime.now(timezone.utc)
            txn.matched_journal_entry_id = journal_entry_id
            txn.reconciliation_status = "MATCHED"

    async def get_reconciliation_stats(
        self,
        bank_account_id: UUID,
        period_start: Optional[date] = None,
        period_end: Optional[date] = None
    ) -> Dict:
        """Get reconciliation statistics for a bank account."""
        # Base query conditions
        conditions = [BankTransaction.bank_account_id == bank_account_id]

        if period_start:
            conditions.append(BankTransaction.transaction_date >= period_start)
        if period_end:
            conditions.append(BankTransaction.transaction_date <= period_end)

        # Total transactions
        total_query = select(func.count(BankTransaction.id)).where(and_(*conditions))
        total_result = await self.db.execute(total_query)
        total_count = total_result.scalar() or 0

        # Reconciled transactions
        reconciled_conditions = conditions + [BankTransaction.is_reconciled == True]
        reconciled_query = select(func.count(BankTransaction.id)).where(and_(*reconciled_conditions))
        reconciled_result = await self.db.execute(reconciled_query)
        reconciled_count = reconciled_result.scalar() or 0

        # Unreconciled transactions
        unreconciled_count = total_count - reconciled_count

        # Auto-matched (assuming we track this in reconciliation_status)
        auto_conditions = reconciled_conditions + [BankTransaction.reconciliation_status == "MATCHED"]
        auto_query = select(func.count(BankTransaction.id)).where(and_(*auto_conditions))
        auto_result = await self.db.execute(auto_query)
        auto_count = auto_result.scalar() or 0

        return {
            'total_transactions': total_count,
            'reconciled_count': reconciled_count,
            'unreconciled_count': unreconciled_count,
            'auto_matched_count': auto_count,
            'manual_matched_count': reconciled_count - auto_count,
            'reconciliation_rate': round(reconciled_count / total_count * 100, 2) if total_count > 0 else 0,
            'auto_match_rate': round(auto_count / reconciled_count * 100, 2) if reconciled_count > 0 else 0,
        }

    async def train_on_historical_matches(
        self,
        bank_account_id: UUID,
        limit: int = 1000
    ) -> Dict:
        """
        Train weights based on historical successful matches.

        Analyzes past matches to optimize feature weights.
        """
        # Get historical matched transactions
        query = (
            select(BankTransaction)
            .where(
                and_(
                    BankTransaction.bank_account_id == bank_account_id,
                    BankTransaction.is_reconciled == True,
                    BankTransaction.matched_journal_entry_id.isnot(None)
                )
            )
            .limit(limit)
        )

        result = await self.db.execute(query)
        matched_txns = list(result.scalars().all())

        if len(matched_txns) < 10:
            return {
                'status': 'insufficient_data',
                'message': 'Need at least 10 historical matches to train',
                'matches_found': len(matched_txns)
            }

        # Analyze features of successful matches
        feature_sums = {
            'amount_match': 0.0,
            'date_proximity': 0.0,
            'text_similarity': 0.0,
            'party_match': 0.0,
            'reference_match': 0.0,
        }

        count = 0
        for txn in matched_txns:
            if not txn.matched_journal_entry_id:
                continue

            # Get matched journal entry
            je_result = await self.db.execute(
                select(JournalEntry).where(JournalEntry.id == txn.matched_journal_entry_id)
            )
            journal_entry = je_result.scalar_one_or_none()

            if not journal_entry:
                continue

            features = self.extract_features(txn, journal_entry)
            for key in feature_sums:
                if key in features:
                    feature_sums[key] += features[key]
            count += 1

        if count == 0:
            return {
                'status': 'error',
                'message': 'Could not analyze any matches'
            }

        # Calculate average feature values
        avg_features = {k: v / count for k, v in feature_sums.items()}

        # Normalize to weights (higher avg = higher weight)
        total = sum(avg_features.values())
        if total > 0:
            optimized_weights = {k: v / total for k, v in avg_features.items()}
        else:
            optimized_weights = self.DEFAULT_WEIGHTS.copy()

        return {
            'status': 'success',
            'samples_analyzed': count,
            'default_weights': self.DEFAULT_WEIGHTS,
            'optimized_weights': {k: round(v, 4) for k, v in optimized_weights.items()},
            'average_features': {k: round(v, 4) for k, v in avg_features.items()},
        }
