from decimal import Decimal

from fastapi import HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models import BudgetHead, EntryType, Transaction, TransactionLine


def validate_double_entry(lines) -> None:
    # Guardrail 1: Reject zero or negative amounts
    for line in lines:
        if Decimal(line.amount) <= 0:
            raise HTTPException(status_code=400, detail=f"Transaction line amounts must be positive (got {line.amount})")
    
    debits = sum(Decimal(line.amount) for line in lines if line.entry_type == EntryType.debit)
    credits = sum(Decimal(line.amount) for line in lines if line.entry_type == EntryType.credit)
    
    # Guardrail 2: Prevent all-debit or all-credit transactions
    debit_lines = [line for line in lines if line.entry_type == EntryType.debit]
    credit_lines = [line for line in lines if line.entry_type == EntryType.credit]
    
    if len(debit_lines) > 0 and len(credit_lines) == 0:
        raise HTTPException(status_code=400, detail="Transaction cannot have only debit entries. Add at least one credit entry.")
    if len(credit_lines) > 0 and len(debit_lines) == 0:
        raise HTTPException(status_code=400, detail="Transaction cannot have only credit entries. Add at least one debit entry.")
    
    # Check debit-credit balance
    if debits <= 0 or credits <= 0 or debits != credits:
        raise HTTPException(status_code=400, detail="Transaction is not balanced")


def centre_budget_summary(db: Session, from_date=None, to_date=None, project_id: int | None = None):
    spent_expr = func.coalesce(
        func.sum(
            case((TransactionLine.entry_type == EntryType.debit, TransactionLine.amount), else_=0)
        ),
        0,
    )
    stmt = (
        select(BudgetHead.id, BudgetHead.name, BudgetHead.sanctioned_amount, spent_expr)
        .outerjoin(TransactionLine, TransactionLine.budget_head_id == BudgetHead.id)
        .outerjoin(Transaction, Transaction.id == TransactionLine.transaction_id)
        .group_by(BudgetHead.id)
    )
    if project_id:
        stmt = stmt.where(TransactionLine.project_id == project_id)
    if from_date:
        stmt = stmt.where(Transaction.txn_date >= from_date)
    if to_date:
        stmt = stmt.where(Transaction.txn_date <= to_date)

    rows = db.execute(stmt).all()
    output = []
    for row in rows:
        sanctioned = Decimal(row.sanctioned_amount or 0)
        spent = Decimal(row[3] or 0)
        remaining = sanctioned - spent
        pct = float((spent / sanctioned) * 100) if sanctioned else 0
        output.append(
            {
                "budget_head_id": row.id,
                "budget_head_name": row.name,
                "sanctioned": sanctioned,
                "spent": spent,
                "remaining": remaining,
                "utilized_pct": round(pct, 2),
            }
        )
    return output
