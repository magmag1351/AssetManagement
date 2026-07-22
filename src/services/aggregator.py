from collections import defaultdict
from typing import List, Dict, Any
from ..models.transaction import Transaction, TransactionType

class BalanceAggregator:
    """
    取引データから月ごとの収支、カード別集計、決済手段別集計、ジャンル別集計を算出するクラス。
    """

    @staticmethod
    def aggregate_monthly(transactions: List[Transaction]) -> Dict[str, Dict[str, Any]]:
        """
        YYYY/MM ごとに集計結果を返します。
        内部振替 (is_internal_transfer=True) は二重計上防止のため総支出からは除外されます。
        """
        monthly: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "income": 0,
            "expense": 0,
            "internal_transfer": 0,
            "by_genre": defaultdict(int),
            "by_card": defaultdict(int),
            "by_payment_method": defaultdict(int),
            "by_source": defaultdict(int),
            "transactions": []
        })

        for tx in transactions:
            month_key = tx.date[:7]
            monthly[month_key]["transactions"].append(tx)

            if tx.is_internal_transfer:
                monthly[month_key]["internal_transfer"] += tx.amount
                continue

            if tx.transaction_type == TransactionType.INCOME:
                monthly[month_key]["income"] += tx.amount
            elif tx.transaction_type == TransactionType.EXPENSE:
                monthly[month_key]["expense"] += tx.amount
                monthly[month_key]["by_genre"][tx.genre] += tx.amount
                monthly[month_key]["by_source"][tx.source_name] += tx.amount

                # カード別と決済手段別を明確に分離
                if tx.source_name != "メイン口座":
                    # クレジットカード別
                    monthly[month_key]["by_card"][tx.source_name] += tx.amount
                    monthly[month_key]["by_payment_method"]["クレジットカード決済"] += tx.amount
                else:
                    # 銀行口座・直接決済別 (PayPayチャージ / ATM出金等)
                    monthly[month_key]["by_payment_method"]["口座直振・PayPayチャージ"] += tx.amount

        return dict(monthly)
