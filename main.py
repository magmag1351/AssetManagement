import sys
import os
import glob
from src.parsers import get_parser_for_file
from src.services.classifier import GenreClassifier
from src.services.storage import StorageService
from src.services.aggregator import BalanceAggregator
from src.models.transaction import Transaction

def read_file_lines(file_path: str) -> list[str]:
    """文字コードを自動判別してファイル行を読み込みます。"""
    with open(file_path, 'rb') as f:
        raw_data = f.read()

    for enc in ['cp932', 'utf-8', 'shift_jis', 'euc-jp']:
        try:
            text = raw_data.decode(enc)
            return text.splitlines()
        except UnicodeDecodeError:
            continue
    raise ValueError(f"文字コードの判別に失敗しました: {file_path}")

def import_resources(resources_dir: str = "resources") -> int:
    classifier = GenreClassifier()
    storage = StorageService()
    all_parsed_txs: list[Transaction] = []

    csv_files = sorted(glob.glob(os.path.join(resources_dir, "*.csv")))
    if not csv_files:
        print(f"[{resources_dir}] 内にCSVファイルが見つかりません。")
        return 0

    print(f"=== {len(csv_files)} 件の明細ファイルをインポート中 ===")
    for file_path in csv_files:
        try:
            lines = read_file_lines(file_path)
            parser = get_parser_for_file(file_path, lines)
            txs = parser.parse(file_path, lines)

            # ジャンルの自動分類
            for tx in txs:
                if tx.genre == "未分類":
                    tx.genre = classifier.classify(tx.description)

            all_parsed_txs.extend(txs)
            print(f"  [成功] {os.path.basename(file_path)} -> {len(txs)} 件の取引をパース ({parser.__class__.__name__})")
        except Exception as e:
            print(f"  [エラー] {os.path.basename(file_path)} の読み込み失敗: {e}")

    added_count = storage.save_transactions(all_parsed_txs)
    print(f"新規に {added_count} 件の取引をデータベース (db/BalanceMaster.csv) に保存しました。\n")
    return added_count

def generate_report():
    storage = StorageService()
    transactions = storage.load_transactions()

    if not transactions:
        print("データベースに取引データが登録されていません。'python3 main.py import' を実行してください。")
        return

    monthly_summary = BalanceAggregator.aggregate_monthly(transactions)

    print("==================================================")
    print("                月次収支レポート                 ")
    print("==================================================")

    for month in sorted(monthly_summary.keys()):
        data = monthly_summary[month]
        income = data["income"]
        expense = data["expense"]
        balance = income - expense
        transfers = data["internal_transfer"]

        print(f"\n--- 【 {month} 】 ---")
        print(f"  総収入  :  {income:>10,} 円")
        print(f"  総支出  :  {expense:>10,} 円 (※カード口座引落 {transfers:,} 円は二重計上防止のため除外)")
        print(f"  収支差額:  {balance:>10,} 円")

        print("  [カード・決済元別 支出内訳]")
        for source, amount in sorted(data["by_source"].items(), key=lambda x: x[1], reverse=True):
            print(f"    - {source:<25}: {amount:>8,} 円")

        print("  [ジャンル別 支出内訳]")
        for genre, amount in sorted(data["by_genre"].items(), key=lambda x: x[1], reverse=True):
            print(f"    - {genre:<25}: {amount:>8,} 円")

    print("\n==================================================")

def main():
    if len(sys.argv) > 1:
        cmd = sys.argv[1].lower()
        if cmd == "import":
            import_resources()
        elif cmd == "report":
            generate_report()
        elif cmd in ["gui", "server"]:
            from app import run_server
            port = int(sys.argv[2]) if len(sys.argv) > 2 and sys.argv[2].isdigit() else 8000
            run_server(port)
        else:
            print(f"未知のコマンド: {cmd}")
            print("使用方法: python3 main.py [import | report | gui]")
    else:
        import_resources()
        generate_report()

if __name__ == "__main__":
    main()

