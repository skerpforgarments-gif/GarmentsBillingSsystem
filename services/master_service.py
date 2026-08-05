from database.db import select, insert, update, delete
from core.state import state


class MasterService:

    # =========================================================
    # ITEMS
    # =========================================================
    @staticmethod
    def get_items():
        return select("items", {
            "company_id": state.company_id
        })

    @staticmethod
    def create_item(data: dict):
        data["company_id"] = state.company_id
        return insert("items", data)

    @staticmethod
    def update_item(item_id, data: dict):
        return update("items", data, {
            "id": item_id,
            "company_id": state.company_id
        })

    @staticmethod
    def delete_item(item_id):
        return delete("items", {
            "id": item_id,
            "company_id": state.company_id
        })

    # =========================================================
    # PARTIES
    # =========================================================
    @staticmethod
    def get_parties():
        return select("parties", {
            "company_id": state.company_id
        })

    @staticmethod
    def create_party(data: dict):
        data["company_id"] = state.company_id
        return insert("parties", data)

    @staticmethod
    def update_party(party_id, data: dict):
        return update("parties", data, {
            "id": party_id,
            "company_id": state.company_id
        })

    @staticmethod
    def delete_party(party_id):
        return delete("parties", {
            "id": party_id,
            "company_id": state.company_id
        })

    # =========================================================
    # AGENTS
    # =========================================================
    @staticmethod
    def get_agents():
        return select("agents", {
            "company_id": state.company_id
        })

    @staticmethod
    def create_agent(data: dict):
        data["company_id"] = state.company_id
        return insert("agents", data)

    @staticmethod
    def update_agent(agent_id, data: dict):
        return update("agents", data, {
            "id": agent_id,
            "company_id": state.company_id
        })

    @staticmethod
    def delete_agent(agent_id):
        return delete("agents", {
            "id": agent_id,
            "company_id": state.company_id
        })

    # =========================================================
    # GENERIC SEARCH (OPTIONAL BUT USEFUL)
    # =========================================================
    @staticmethod
    def search(table, filters: dict):
        filters["company_id"] = state.company_id
        return select(table, filters)
