import os
import unittest
from src.parsers.vpass_parser import VpassCardParser
from src.parsers.bank_parser import NetBankParser
from src.services.classifier import GenreClassifier
from src.services.storage import StorageService
from src.services.aggregator import BalanceAggregator
from main import read_file_lines

class TestAssetManagement(unittest.TestCase):

    def test_vpass_parser(self):
        lines = read_file_lines("resources/202605.csv")
        parser = VpassCardParser()
        self.assertTrue(parser.can_parse("resources/202605.csv", lines))
        txs = parser.parse("resources/202605.csv", lines)
        self.assertEqual(len(txs), 8)
        total_amount = sum(t.amount for t in txs)
        self.assertEqual(total_amount, 23868)

    def test_bank_parser(self):
        lines = read_file_lines("resources/NBG230614p9s00N2me2Zrq0I1je47Q2jby0pIgXF.csv")
        parser = NetBankParser()
        self.assertTrue(parser.can_parse("resources/NBG230614p9s00N2me2Zrq0I1je47Q2jby0pIgXF.csv", lines))
        txs = parser.parse("resources/NBG230614p9s00N2me2Zrq0I1je47Q2jby0pIgXF.csv", lines)
        self.assertGreater(len(txs), 0)
        
        # Check internal transfer detection for card withdrawal
        smbc_txs = [t for t in txs if "ミツイスミトモカ－ド" in t.description]
        self.assertEqual(len(smbc_txs), 1)
        self.assertTrue(smbc_txs[0].is_internal_transfer)
        self.assertEqual(smbc_txs[0].amount, 23868)

    def test_genre_classifier(self):
        classifier = GenreClassifier("config/genre_rules.json")
        self.assertEqual(classifier.classify("ＡＭＡＺＯＮ．ＣＯ．ＪＰ"), "ネットショッピング")
        self.assertEqual(classifier.classify("Ａｍａｚｏｎプライム会費"), "サブスク")
        self.assertEqual(classifier.classify("モバイルＩＣＯＣＡチャージ"), "交通費")
        self.assertEqual(classifier.classify("給与振込 ガク）キンキダイガク"), "給与収入")
        self.assertEqual(classifier.classify("山岡家東広島店／ｉＤ"), "外食")
        self.assertEqual(classifier.classify("未知の購入品"), "未分類")

if __name__ == "__main__":
    unittest.main()
