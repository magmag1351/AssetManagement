import unittest
import json
import os
from app import load_profiles_config, save_profiles_config, get_active_profile_id
from src.models.transaction import Transaction, TransactionType
from src.services.storage import StorageService

class TestMultiProfileSystem(unittest.TestCase):

    def test_profile_config_loading(self):
        cfg = load_profiles_config()
        self.assertIn("active_profile_id", cfg)
        self.assertIn("profiles", cfg)
        self.assertGreater(len(cfg["profiles"]), 0)
        self.assertIn("accounts", cfg["profiles"][0])

    def test_transaction_profile_id(self):
        tx = Transaction(
            date="2026/05/01",
            description="テスト買い物",
            amount=1000,
            transaction_type=TransactionType.EXPENSE,
            profile_id="profile_test"
        )
        self.assertEqual(tx.profile_id, "profile_test")

    def test_profile_edit_config(self):
        cfg = load_profiles_config()
        profile = cfg["profiles"][0]
        original_name = profile["name"]
        profile["name"] = "テスト変更名"
        save_profiles_config(cfg)

        reloaded = load_profiles_config()
        self.assertEqual(reloaded["profiles"][0]["name"], "テスト変更名")

        # リセット
        reloaded["profiles"][0]["name"] = original_name
        save_profiles_config(reloaded)

    def test_multi_account_per_profile(self):
        cfg = load_profiles_config()
        profile = cfg["profiles"][0]
        accounts = profile.get("accounts", [])
        self.assertIsInstance(accounts, list)

if __name__ == "__main__":
    unittest.main()
