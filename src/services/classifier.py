import json
import os
from typing import Dict, Any

class GenreClassifier:
    """
    設定ファイル (config/genre_rules.json) に基づき、明細の摘要からジャンルを自動決定する分類クラス。
    前方一致ルール (prefix_rules) と部分一致ルール (keyword_rules) を評価します。
    """

    def __init__(self, config_path: str = "config/genre_rules.json"):
        self.config_path = config_path
        self.prefix_rules: Dict[str, str] = {}
        self.keyword_rules: Dict[str, str] = {}
        self.default_genre: str = "未分類"
        self.load_rules()

    def load_rules(self):
        if not os.path.exists(self.config_path):
            return

        with open(self.config_path, "r", encoding="utf-8") as f:
            data: Dict[str, Any] = json.load(f)
            self.prefix_rules = data.get("prefix_rules", {})
            self.keyword_rules = data.get("keyword_rules", {})
            self.default_genre = data.get("default_genre", "未分類")

    def classify(self, description: str) -> str:
        if not description:
            return self.default_genre

        # 1. 前方一致ルールのチェック
        for prefix, genre in self.prefix_rules.items():
            if description.startswith(prefix):
                return genre

        # 2. 部分一致ルールのチェック
        for keyword, genre in self.keyword_rules.items():
            if keyword in description:
                return genre

        return self.default_genre
