import csv
import os
from typing import List
from ..models.transaction import Transaction, TransactionType

class StorageService:
    """
    収支データベース (db/BalanceMaster.csv) への読み書きを管理するストレージクラス。
    プロファイルID (profile_id) に対応しています。
    """

    def __init__(self, db_path: str = "db/BalanceMaster.csv"):
        self.db_path = db_path

    def save_transactions(self, transactions: List[Transaction]) -> int:
        """
        取引データをCSV DBへ保存（重複を排除して統合）します。
        保存された新規件数を返します。
        """
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        existing = self.load_transactions()
        
        # 重複キー生成セット (日付, 摘要, 金額, ソース名, プロファイルID)
        seen_keys = {
            (t.date, t.description, t.amount, t.source_name, t.transaction_type.value, getattr(t, 'profile_id', 'profile_default'))
            for t in existing
        }

        new_added = 0
        all_txs = list(existing)

        for tx in transactions:
            prof_id = getattr(tx, 'profile_id', 'profile_default') or 'profile_default'
            key = (tx.date, tx.description, tx.amount, tx.source_name, tx.transaction_type.value, prof_id)
            if key not in seen_keys:
                seen_keys.add(key)
                all_txs.append(tx)
                new_added += 1

        # 日付昇順でソート
        all_txs.sort(key=lambda x: (x.date, x.source_name, x.description))

        header = [
            "日付", "摘要", "金額", "収支区分", "ジャンル",
            "支払・収入元", "カード番号", "請求先口座", "備考", "内部振替フラグ", "プロファイルID"
        ]

        with open(self.db_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for tx in all_txs:
                writer.writerow([
                    tx.date,
                    tx.description,
                    tx.amount,
                    tx.transaction_type.value,
                    tx.genre,
                    tx.source_name,
                    tx.card_number,
                    tx.billing_account,
                    tx.notes,
                    "1" if tx.is_internal_transfer else "0",
                    getattr(tx, 'profile_id', 'profile_default') or 'profile_default'
                ])

        return new_added

    def load_transactions(self) -> List[Transaction]:
        """CSV DBから取引データを読み込みます。"""
        if not os.path.exists(self.db_path):
            return []

        transactions = []
        with open(self.db_path, "r", encoding="utf-8") as f:
            reader = csv.reader(f)
            header = next(reader, None)
            if not header:
                return []

            for row in reader:
                if not row or len(row) < 10:
                    continue
                prof_id = row[10] if len(row) > 10 and row[10] else "profile_default"
                transactions.append(Transaction(
                    date=row[0],
                    description=row[1],
                    amount=int(row[2]),
                    transaction_type=TransactionType(row[3]),
                    genre=row[4],
                    source_name=row[5],
                    card_number=row[6],
                    billing_account=row[7],
                    notes=row[8],
                    is_internal_transfer=(row[9] == "1"),
                    profile_id=prof_id
                ))
        return transactions

    def overwrite_all(self, transactions: List[Transaction]):
        """全取引データを直接上書き保存します。"""
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        transactions.sort(key=lambda x: (x.date, x.source_name, x.description))
        header = [
            "日付", "摘要", "金額", "収支区分", "ジャンル",
            "支払・収入元", "カード番号", "請求先口座", "備考", "内部振替フラグ", "プロファイルID"
        ]

        with open(self.db_path, "w", encoding="utf-8", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            for tx in transactions:
                writer.writerow([
                    tx.date,
                    tx.description,
                    tx.amount,
                    tx.transaction_type.value,
                    tx.genre,
                    tx.source_name,
                    tx.card_number,
                    tx.billing_account,
                    tx.notes,
                    "1" if tx.is_internal_transfer else "0",
                    getattr(tx, 'profile_id', 'profile_default') or 'profile_default'
                ])
