from abc import ABC, abstractmethod
from typing import List
from ..models.transaction import Transaction

class BaseStatementParser(ABC):
    """
    クレジットカードや銀行明細ファイルをパースするための抽象基底クラス。
    新しいカード会社や銀行フォーマットを追加する場合は、このクラスを継承して作成します。
    """

    @abstractmethod
    def can_parse(self, file_path: str, lines: List[str]) -> bool:
        """指定されたファイル内容をこのパーサーで処理できるかを判定します。"""
        pass

    @abstractmethod
    def parse(self, file_path: str, lines: List[str]) -> List[Transaction]:
        """ファイル内容をパースして Transaction のリストを返します。"""
        pass
