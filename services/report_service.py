from database.db import select
from core.state import state


class ReportService:

    # =========================================================
    # SALES REPORT
    # =========================================================
    @staticmethod
    def get_sales_report(filters: dict = None):
        filters = filters or {}
        filters["company_id"] = state.company_id

        data = select("orders", filters)

        return [
            {
                "order_id": r["id"],
                "party_id": r["party_id"],
                "amount": r.get("total_amount", 0)
            }
            for r in data
        ]

    # =========================================================
    # ITEM-WISE SALES
    # =========================================================
    @staticmethod
    def get_item_sales():
        items = select("order_items") # Global select, filtered by RLS or manually if needed
        # In SaaS, RLS handles this, but we should pass company_id if needed
        
        summary = {}

        for r in items:
            item_id = r["item_id"]

            if item_id not in summary:
                summary[item_id] = {
                    "item_id": item_id,
                    "total_qty": 0,
                    "total_amount": 0
                }

            summary[item_id]["total_qty"] += r.get("qty_pcs", 0)
            summary[item_id]["total_amount"] += r.get("amount", 0)

        return list(summary.values())

    # =========================================================
    # OUTSTANDING REPORT
    # =========================================================
    @staticmethod
    def get_outstanding():
        ledger = select("ledger_entries", {
            "company_id": state.company_id
        })

        party_balance = {}

        for r in ledger:
            p_id = r["party_id"]
            if p_id not in party_balance:
                party_balance[p_id] = 0
            party_balance[p_id] += float(r.get("debit", 0)) - float(r.get("credit", 0))

        return [
            {"party_id": k, "balance": v}
            for k, v in party_balance.items()
        ]

    # =========================================================
    # PARTY LEDGER
    # =========================================================
    @staticmethod
    def get_party_ledger(party_id):
        return select("ledger_entries", {
            "company_id": state.company_id,
            "party_id": party_id
        })

    # =========================================================
    # ANALYTICS SUMMARY
    # =========================================================
    @staticmethod
    def get_analytics():
        orders = select("orders", {
            "company_id": state.company_id
        })

        ledger = select("ledger_entries", {
            "company_id": state.company_id
        })

        total_sales = sum(o.get("total_amount", 0) for o in orders)
        total_orders = len(orders)

        # latest balance per party
        party_balance = {}
        for r in ledger:
            p_id = r["party_id"]
            if p_id not in party_balance:
                party_balance[p_id] = 0
            party_balance[p_id] += float(r.get("debit", 0)) - float(r.get("credit", 0))

        total_outstanding = sum(party_balance.values())

        return {
            "total_sales": total_sales,
            "total_orders": total_orders,
            "total_outstanding": total_outstanding
        }

    # =========================================================
    # FILTERED SALES (ADVANCED)
    # =========================================================
    @staticmethod
    def get_filtered_sales(filters: dict):
        query = {"company_id": state.company_id}

        if filters.get("party_id"):
            query["party_id"] = filters["party_id"]

        data = select("orders", query)

        # optional date filtering later if column exists

        return data
