import unittest
import json
from app import AssetManagementAPIHandler
from io import BytesIO

class MockRequest:
    def __init__(self, path, method="GET", body=b""):
        self.path = path
        self.method = method
        self.body = body

class TestAPIEndpoints(unittest.TestCase):

    def test_summary_data(self):
        from src.services.storage import StorageService
        from src.services.aggregator import BalanceAggregator
        storage = StorageService()
        transactions = storage.load_transactions()
        summary = BalanceAggregator.aggregate_monthly(transactions)
        self.assertIn("2026/05", summary)
        self.assertGreater(summary["2026/05"]["expense"], 0)

if __name__ == "__main__":
    unittest.main()
