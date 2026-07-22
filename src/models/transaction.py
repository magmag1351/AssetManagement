from dataclasses import dataclass
from enum import Enum
from typing import Optional

class TransactionType(Enum):
    EXPENSE = "EXPENSE"
    INCOME = "INCOME"

@dataclass
class Transaction:
    date: str                  # YYYY/MM/DD or YYYY-MM-DD
    description: str           # 明細内容 / 摘要
    amount: int                # 金額
    transaction_type: TransactionType
    genre: str = "未分類"        # ジャンル
    source_name: str = ""       # カード名・口座名 (例: Ａｍａｚｏｎマスター)
    card_number: str = ""       # カード番号 (例: 5334-91**-****-****)
    billing_account: str = "メイン口座" # 請求先口座
    notes: str = ""             # 備考
    is_internal_transfer: bool = False # クレジットカード引き落とし等の内部振り替えフラグ
    profile_id: str = "profile_default" # プロファイルID
