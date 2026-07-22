from typing import List, Type
from .base import BaseStatementParser
from .vpass_parser import VpassCardParser
from .bank_parser import NetBankParser

# 利用可能なパーサークラスのレジストリ。新しいカード対応時はここにクラスを追加します。
PARSER_REGISTRY: List[Type[BaseStatementParser]] = [
    VpassCardParser,
    NetBankParser,
]

def get_parser_for_file(file_path: str, lines: List[str]) -> BaseStatementParser:
    """ファイル内容に対応する適切なパーサーインスタンスを返します。"""
    for cls in PARSER_REGISTRY:
        parser = cls()
        if parser.can_parse(file_path, lines):
            return parser
    raise ValueError(f"対応するパーサーが見つかりません: {file_path}")
