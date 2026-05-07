"""
Test suite for Task B: Transaction Safety Nets Lite

Tests guardrails:
1. Zero/negative amount validation
2. Debit-credit balance validation
3. All-debit/all-credit prevention
"""

import pytest
from decimal import Decimal
from fastapi import HTTPException
from app.models import EntryType
from app.services.accounting import validate_double_entry
from pydantic import BaseModel


class MockTransactionLineIn(BaseModel):
    """Mock schema for testing purposes"""
    account_id: int
    project_id: int | None = None
    budget_head_id: int | None = None
    entry_type: EntryType
    amount: Decimal


class TestGuardrail1ZeroNegativeAmounts:
    """Guardrail 1: Prevent zero or negative transaction amounts"""

    def test_reject_zero_amount_debit(self):
        """Should reject transaction line with zero amount (debit)"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("0"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("100"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "must be positive" in exc.value.detail.lower()

    def test_reject_negative_amount_credit(self):
        """Should reject transaction line with negative amount (credit)"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("100"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("-50"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "must be positive" in exc.value.detail.lower()

    def test_accept_small_positive_amounts(self):
        """Should accept very small positive amounts"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("0.01"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("0.01"),
            ),
        ]
        # Should not raise
        validate_double_entry(lines)


class TestGuardrail2AllDebitAllCredit:
    """Guardrail 2 (explicit): Prevent all-debit or all-credit transactions"""

    def test_reject_all_debit_lines(self):
        """Should reject transaction with only debit lines"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("100"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.debit,
                amount=Decimal("100"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "only debit" in exc.value.detail.lower()

    def test_reject_all_credit_lines(self):
        """Should reject transaction with only credit lines"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.credit,
                amount=Decimal("100"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("100"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "only credit" in exc.value.detail.lower()


class TestExistingDebitCreditBalance:
    """Existing validation: Debit-credit balance check"""

    def test_accept_balanced_transaction(self):
        """Should accept perfectly balanced transaction"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("1000.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("1000.00"),
            ),
        ]
        # Should not raise
        validate_double_entry(lines)

    def test_reject_unbalanced_transaction(self):
        """Should reject transaction with unbalanced debits and credits"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("1000.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("900.00"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "balanced" in exc.value.detail.lower()

    def test_accept_multiple_debits_credits_balanced(self):
        """Should accept multiple debit/credit lines that balance"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("600.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.debit,
                amount=Decimal("400.00"),
            ),
            MockTransactionLineIn(
                account_id=3,
                entry_type=EntryType.credit,
                amount=Decimal("500.00"),
            ),
            MockTransactionLineIn(
                account_id=4,
                entry_type=EntryType.credit,
                amount=Decimal("500.00"),
            ),
        ]
        # Should not raise
        validate_double_entry(lines)

    def test_reject_multiple_debits_credits_unbalanced(self):
        """Should reject multiple debit/credit lines that don't balance"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("1000.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.debit,
                amount=Decimal("500.00"),
            ),
            MockTransactionLineIn(
                account_id=3,
                entry_type=EntryType.credit,
                amount=Decimal("1000.00"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
        assert "balanced" in exc.value.detail.lower()


class TestEdgeCases:
    """Edge cases and precision tests"""

    def test_reject_zero_in_multiple_lines(self):
        """Should reject even if only one line is zero among valid lines"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("100.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("0"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400

    def test_decimal_precision_preserved(self):
        """Should handle high-precision decimals correctly"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("123.45"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("123.45"),
            ),
        ]
        # Should not raise
        validate_double_entry(lines)

    def test_reject_tiny_imbalance(self):
        """Should reject even tiny imbalances (penny errors)"""
        lines = [
            MockTransactionLineIn(
                account_id=1,
                entry_type=EntryType.debit,
                amount=Decimal("1000.00"),
            ),
            MockTransactionLineIn(
                account_id=2,
                entry_type=EntryType.credit,
                amount=Decimal("999.99"),
            ),
        ]
        with pytest.raises(HTTPException) as exc:
            validate_double_entry(lines)
        assert exc.value.status_code == 400
