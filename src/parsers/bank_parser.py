import csv
from typing import List
from .base import BaseStatementParser
from ..models.transaction import Transaction, TransactionType

class NetBankParser(BaseStatementParser):
    """
    ネット銀行 (NBG) の口座明細CSV用パーサー。
    利息や給与振込などの収入、PayPayチャージ等の支出をパースします。
    クレジットカード等の引き落としは二重計上を防ぐため is_internal_transfer=True と判定します。
    """

    def can_parse(self, file_path: str, lines: List[str]) -> bool:
        if not lines:
            return False
        first_line = lines[0].replace('"', '')
        return "操作日(年)" in first_line and "摘要" in first_line

    def parse(self, file_path: str, lines: List[str]) -> List[Transaction]:
        transactions: List[Transaction] = []
        reader = csv.reader(lines)
        header = next(reader, None)

        if not header:
            return transactions

        # ヘッダー列インデックスを取得
        header_clean = [h.strip().replace('"', '') for h in header]
        try:
            idx_year = header_clean.index("操作日(年)")
            idx_month = header_clean.index("操作日(月)")
            idx_day = header_clean.index("操作日(日)")
            idx_desc = header_clean.index("摘要")
            idx_payment = header_clean.index("お支払金額")
            idx_deposit = header_clean.index("お預り金額")
        except ValueError:
            return transactions

        idx_notes = header_clean.index("メモ") if "メモ" in header_clean else -1

        for row in reader:
            if not row or len(row) <= max(idx_year, idx_month, idx_day, idx_desc, idx_payment, idx_deposit):
                continue

            year = row[idx_year].strip().replace('"', '')
            month = row[idx_month].strip().replace('"', '').zfill(2)
            day = row[idx_day].strip().replace('"', '').zfill(2)
            date_str = f"{year}/{month}/{day}"

            desc = row[idx_desc].strip().replace('"', '')
            payment_str = row[idx_payment].strip().replace('"', '')
            deposit_str = row[idx_deposit].strip().replace('"', '')
            notes = row[idx_notes].strip().replace('"', '') if idx_notes != -1 and idx_notes < len(row) else ""

            if payment_str: # 支出
                try:
                    amount = int(payment_str)
                except ValueError:
                    continue

                # クレジットカード振替・引き落とし判定（二重計上防止）
                is_transfer = any(keyword in desc for keyword in ["ミツイスミトモカ－ド", "カード引落", "カード決済"])

                transactions.append(Transaction(
                    date=date_str,
                    description=desc,
                    amount=amount,
                    transaction_type=TransactionType.EXPENSE,
                    source_name="メイン口座",
                    billing_account="メイン口座",
                    notes=notes,
                    is_internal_transfer=is_transfer
                ))
            elif deposit_str: # 収入
                try:
                    amount = int(deposit_str)
                except ValueError:
                    continue

                transactions.append(Transaction(
                    date=date_str,
                    description=desc,
                    amount=amount,
                    transaction_type=TransactionType.INCOME,
                    source_name="メイン口座",
                    billing_account="メイン口座",
                    notes=notes
                ))

        return transactions
