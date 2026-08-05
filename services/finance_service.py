from database.db import insert, select
from core.state import state


class FinanceService:

    # =========================================================
    # GET LAST BALANCE
    # =========================================================
    @staticmethod
    def get_last_balance(party_id):
        rows = select("ledger_entries", {
            "company_id": state.company_id,
            "party_id": party_id
        })

        if not rows:
            return 0

        # Calculate balance: sum(debit) - sum(credit)
        total_debit = sum(r.get("debit", 0) for r in rows)
        total_credit = sum(r.get("credit", 0) for r in rows)
        
        return total_debit - total_credit

    # =========================================================
    # ADD LEDGER ENTRY (CORE FUNCTION)
    # =========================================================
    @staticmethod
    def add_entry(party_id, debit=0, credit=0):
        last_balance = FinanceService.get_last_balance(party_id)

        new_balance = last_balance + debit - credit

        insert("ledger_entries", {
            "company_id": state.company_id,
            "party_id": party_id,
            "debit": debit,
            "credit": credit
        })

        return new_balance

    # =========================================================
    # RECORD SALE (FROM SALES MODULE)
    # =========================================================
    @staticmethod
    def record_sale(party_id, amount):
        """
        Sale increases receivable → DEBIT
        """
        return FinanceService.add_entry(
            party_id=party_id,
            debit=amount,
            credit=0
        )

    # =========================================================
    # CREATE RECEIPT
    # =========================================================
    @staticmethod
    def create_receipt(data: dict):
        """
        data = {
            "party_id": 1,
            "amount": 1000,
            "mode": "cash"
        }
        """

        data["company_id"] = state.company_id

        # Save receipt
        insert("receipt_vouchers", data)

        # Update ledger (credit)
        balance = FinanceService.add_entry(
            party_id=data["party_id"],
            debit=0,
            credit=float(data["amount"])
        )

        return balance

    # =========================================================
    # CREATE PAYMENT
    # =========================================================
    @staticmethod
    def create_payment(data: dict):
        data["company_id"] = state.company_id

        insert("payment_vouchers", data)

        # Payment reduces payable → credit
        balance = FinanceService.add_entry(
            party_id=data["party_id"],
            debit=0,
            credit=float(data["amount"])
        )

        return balance

    # =========================================================
    # GET LEDGER
    # =========================================================
    @staticmethod
    def get_ledger(party_id):
        return select("ledger_entries", {
            "company_id": state.company_id,
            "party_id": party_id
        })

    # =========================================================
    # GET OUTSTANDING
    # =========================================================
    @staticmethod
    def get_outstanding(party_id):
        rows = FinanceService.get_ledger(party_id)

        if not rows:
            return 0

        return rows[-1]["balance"]

    # =========================================================
    # ALL OUTSTANDING
    # =========================================================
    @staticmethod
    def get_all_outstanding():
        rows = select("ledger_entries", {
            "company_id": state.company_id
        })

        party_balance = {}

        for r in rows:
            party_id = r["party_id"]
            party_balance[party_id] = r["balance"]

        return [
            {"party_id": k, "balance": v}
            for k, v in party_balance.items()
        ]
