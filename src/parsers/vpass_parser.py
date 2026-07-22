import csv
from typing import List
from .base import BaseStatementParser
from ..models.transaction import Transaction, TransactionType

class VpassCardParser(BaseStatementParser):
    """
    三井住友カード (Vpass) の利用明細CSV用パーサー。
    複数カード情報が1ファイルに含まれる場合も、それぞれのカード名称ごとに解析します。
    """

    def can_parse(self, file_path: str, lines: List[str]) -> bool:
        if not lines:
            return False
        # Vpassの特徴: 1行目にカード会員名・カード番号・カード名が含まれている、または日付/金額フォーマット
        first_line = lines[0]
        parts = first_line.split(',')
        if len(parts) >= 3 and ('様' in parts[0] or '*' in parts[1]):
            return True
        return False

    def parse(self, file_path: str, lines: List[str]) -> List[Transaction]:
        transactions: List[Transaction] = []
        current_card_name = "クレジットカード"
        current_card_number = ""
        default_billing_account = "メイン口座"

        for line_num, raw_line in enumerate(lines, 1):
            line = raw_line.strip()
            if not line:
                continue

            parts = [p.strip() for p in line.split(',')]

            # ヘッダー行判定 (例: 上杉　健太　様,5334-91**-****-****,Ａｍａｚｏｎマスター)
            if len(parts) >= 3 and ('様' in parts[0] or '*' in parts[1]):
                current_card_number = parts[1]
                current_card_name = parts[2] if len(parts) >= 3 and parts[2] else "クレジットカード"
                continue

            # 合計金額行の無視 (例: ,,,,,23868,)
            if line.startswith(',,,,,') or (len(parts) >= 6 and not parts[0] and not parts[1] and parts[5].replace('-', '').isdigit()):
                continue

            # 利用明細行判定 (例: 2026/04/08,Ａｍａｚｏｎプライム会費,600,１,１,600,)
            if len(parts) >= 3 and parts[0]:
                date_str = parts[0]
                # 日付フォーマットの検証 (YYYY/MM/DD)
                date_parts = date_str.split('/')
                if len(date_parts) == 3 and all(p.isdigit() for p in date_parts):
                    description = parts[1]
                    try:
                        # 当月支払金額（なければ利用金額）
                        amount_str = parts[5] if len(parts) > 5 and parts[5] else parts[2]
                        amount = int(amount_str)
                    except ValueError:
                        continue

                    notes = parts[6] if len(parts) > 6 else ""

                    # 返金処理（負の値）または通常の支出
                    tx_type = TransactionType.EXPENSE if amount >= 0 else TransactionType.INCOME

                    transactions.append(Transaction(
                        date=date_str,
                        description=description,
                        amount=abs(amount),
                        transaction_type=tx_type,
                        source_name=current_card_name,
                        card_number=current_card_number,
                        billing_account=default_billing_account,
                        notes=notes
                    ))

        return transactions
