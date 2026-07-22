import http.server
import socketserver
import json
import os
import sys
import glob
import time
import urllib.parse
from pathlib import Path

# システムモジュールのパス追加
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.models.transaction import Transaction, TransactionType
from src.services.storage import StorageService
from src.services.classifier import GenreClassifier
from src.services.aggregator import BalanceAggregator
from src.parsers import get_parser_for_file
from main import read_file_lines

PORT = 8000
WEB_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "web")
PROFILES_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "profiles.json")

def load_profiles_config():
    if not os.path.exists(PROFILES_CONFIG_PATH):
        os.makedirs(os.path.dirname(PROFILES_CONFIG_PATH), exist_ok=True)
        default_config = {
            "active_profile_id": "profile_default",
            "profiles": [
                {
                    "id": "profile_default",
                    "name": "個人用プロファイル",
                    "account_info": "メイン口座・サブ口座・カード連携",
                    "avatar": "個人",
                    "color": "#10b981",
                    "accounts": [
                        { "id": "acc_default_1", "name": "メイン口座", "type": "BANK", "is_primary": True },
                        { "id": "acc_default_2", "name": "Ａｍａｚｏｎマスター", "type": "CARD", "is_primary": False },
                        { "id": "acc_default_3", "name": "Apple Pay", "type": "CARD", "is_primary": False }
                    ]
                }
            ]
        }
        with open(PROFILES_CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(default_config, f, ensure_ascii=False, indent=2)
        return default_config

    with open(PROFILES_CONFIG_PATH, "r", encoding="utf-8") as f:
        cfg = json.load(f)
        modified = False
        for p in cfg.get("profiles", []):
            if "accounts" not in p:
                p["accounts"] = [
                    { "id": f"acc_{int(time.time()*1000)}_1", "name": "メイン口座", "type": "BANK", "is_primary": True }
                ]
                modified = True
        if modified:
            save_profiles_config(cfg)
        return cfg


def save_profiles_config(data):
    os.makedirs(os.path.dirname(PROFILES_CONFIG_PATH), exist_ok=True)
    with open(PROFILES_CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_active_profile_id():
    cfg = load_profiles_config()
    return cfg.get("active_profile_id", "profile_default")

class AssetManagementAPIHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, format, *args):
        print(f"[API] {self.command} {self.path} -> {args[0] if args else ''}")

    def send_json_response(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        if path == "/api/summary":
            self.handle_get_summary(query)
        elif path == "/api/transactions":
            self.handle_get_transactions(query)
        elif path == "/api/rules":
            self.handle_get_rules()
        elif path == "/api/profiles":
            self.handle_get_profiles()
        else:
            if path == "/" or path == "":
                self.path = "/index.html"
            super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get('Content-Length', 0))
        post_body = self.rfile.read(content_length) if content_length > 0 else b""

        if path == "/api/import":
            self.handle_post_import(post_body)
        elif path == "/api/rules":
            self.handle_post_rules(post_body)
        elif path == "/api/transactions/update":
            self.handle_post_update_transaction(post_body)
        elif path == "/api/profiles/switch":
            self.handle_post_switch_profile(post_body)
        elif path == "/api/profiles/add":
            self.handle_post_add_profile(post_body)
        elif path == "/api/profiles/delete":
            self.handle_post_delete_profile(post_body)
        elif path == "/api/profiles/edit":
            self.handle_post_edit_profile(post_body)
        elif path == "/api/profiles/accounts/add":
            self.handle_post_add_account(post_body)
        elif path == "/api/profiles/accounts/delete":
            self.handle_post_delete_account(post_body)
        else:
            self.send_json_response({"error": "Endpoint not found"}, 404)



    # --- API Handlers ---

    def handle_get_profiles(self):
        cfg = load_profiles_config()
        self.send_json_response(cfg)

    def handle_post_switch_profile(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            target_id = data.get("profile_id")
            cfg = load_profiles_config()

            if any(p["id"] == target_id for p in cfg["profiles"]):
                cfg["active_profile_id"] = target_id
                save_profiles_config(cfg)
                self.send_json_response({"status": "success", "active_profile_id": target_id})
            else:
                self.send_json_response({"error": "指定されたプロファイルが見つかりません。"}, 404)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_add_profile(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            name = data.get("name", "").strip()
            account_info = data.get("account_info", "サブ口座").strip()
            avatar = data.get("avatar", name[:2]).strip() or "新規"
            color = data.get("color", "#6366f1")

            if not name:
                self.send_json_response({"error": "プロファイル名を入力してください。"}, 400)
                return

            cfg = load_profiles_config()
            new_id = f"profile_{int(time.time() * 1000)}"
            new_profile = {
                "id": new_id,
                "name": name,
                "account_info": account_info,
                "avatar": avatar,
                "color": color
            }

            cfg["profiles"].append(new_profile)
            cfg["active_profile_id"] = new_id
            save_profiles_config(cfg)

            self.send_json_response({
                "status": "success",
                "message": f"プロファイル『{name}』を追加しました。",
                "new_profile": new_profile,
                "active_profile_id": new_id
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_delete_profile(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            target_id = data.get("profile_id")

            if target_id == "profile_default":
                self.send_json_response({"error": "デフォルトプロファイルは削除できません。"}, 400)
                return

            cfg = load_profiles_config()
            cfg["profiles"] = [p for p in cfg["profiles"] if p["id"] != target_id]

            if cfg["active_profile_id"] == target_id:
                cfg["active_profile_id"] = "profile_default"

            save_profiles_config(cfg)

            # DBから対象プロファイルの取引レコードを削除
            storage = StorageService()
            all_txs = storage.load_transactions()
            remaining_txs = [t for t in all_txs if getattr(t, 'profile_id', 'profile_default') != target_id]
            storage.overwrite_all(remaining_txs)

            self.send_json_response({
                "status": "success",
                "message": "プロファイルを削除しました。",
                "active_profile_id": cfg["active_profile_id"]
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_edit_profile(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            target_id = data.get("profile_id")
            name = data.get("name", "").strip()
            account_info = data.get("account_info", "").strip()
            avatar = data.get("avatar", "").strip()
            color = data.get("color", "#6366f1")

            if not target_id or not name:
                self.send_json_response({"error": "プロファイル名を入力してください。"}, 400)
                return

            cfg = load_profiles_config()
            profile = next((p for p in cfg["profiles"] if p["id"] == target_id), None)
            if not profile:
                self.send_json_response({"error": "プロファイルが見つかりません。"}, 404)
                return

            profile["name"] = name
            if account_info:
                profile["account_info"] = account_info
            if avatar:
                profile["avatar"] = avatar
            if color:
                profile["color"] = color

            save_profiles_config(cfg)
            self.send_json_response({
                "status": "success",
                "message": f"プロファイル『{name}』を更新しました。",
                "updated_profile": profile
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_add_account(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            profile_id = data.get("profile_id")
            account_name = data.get("name", "").strip()
            account_type = data.get("type", "BANK").strip()

            if not profile_id or not account_name:
                self.send_json_response({"error": "口座・カード名を入力してください。"}, 400)
                return

            cfg = load_profiles_config()
            profile = next((p for p in cfg["profiles"] if p["id"] == profile_id), None)
            if not profile:
                self.send_json_response({"error": "プロファイルが見つかりません。"}, 404)
                return

            if "accounts" not in profile:
                profile["accounts"] = []

            new_acc_id = f"acc_{int(time.time()*1000)}"
            new_acc = {
                "id": new_acc_id,
                "name": account_name,
                "type": account_type,
                "is_primary": len(profile["accounts"]) == 0
            }
            profile["accounts"].append(new_acc)

            acc_names = [a["name"] for a in profile["accounts"]]
            profile["account_info"] = " / ".join(acc_names[:2]) + (" 等" if len(acc_names) > 2 else "")

            save_profiles_config(cfg)
            self.send_json_response({
                "status": "success",
                "message": f"口座/カード『{account_name}』を追加しました。",
                "new_account": new_acc,
                "profile": profile
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_delete_account(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            profile_id = data.get("profile_id")
            account_id = data.get("account_id")

            cfg = load_profiles_config()
            profile = next((p for p in cfg["profiles"] if p["id"] == profile_id), None)
            if not profile or "accounts" not in profile:
                self.send_json_response({"error": "プロファイルまたは口座が見つかりません。"}, 404)
                return

            profile["accounts"] = [a for a in profile["accounts"] if a["id"] != account_id]
            acc_names = [a["name"] for a in profile["accounts"]]
            profile["account_info"] = " / ".join(acc_names[:2]) + (" 等" if len(acc_names) > 2 else "") if acc_names else "口座未登録"

            save_profiles_config(cfg)
            self.send_json_response({
                "status": "success",
                "message": "口座/カードを削除しました。",
                "profile": profile
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_get_summary(self, query=None):
        storage = StorageService()
        active_prof_id = get_active_profile_id()
        all_txs = storage.load_transactions()
        
        # アクティブプロファイルの取引のみを抽出
        transactions = [t for t in all_txs if getattr(t, 'profile_id', 'profile_default') == active_prof_id]

        account_filter = query.get("account", [None])[0] if query else None
        if account_filter and account_filter != "all":
            transactions = [
                t for t in transactions
                if account_filter in t.billing_account or account_filter in t.source_name
            ]

        monthly_summary = BalanceAggregator.aggregate_monthly(transactions)

        total_income = sum(m["income"] for m in monthly_summary.values())
        total_expense = sum(m["expense"] for m in monthly_summary.values())
        total_transfers = sum(m["internal_transfer"] for m in monthly_summary.values())

        formatted_monthly = {}
        for m, data in monthly_summary.items():
            formatted_monthly[m] = {
                "income": data["income"],
                "expense": data["expense"],
                "internal_transfer": data["internal_transfer"],
                "by_genre": dict(data["by_genre"]),
                "by_card": dict(data["by_card"]),
                "by_payment_method": dict(data["by_payment_method"]),
                "by_source": dict(data["by_source"]),
                "count": len(data["transactions"])
            }

        response_data = {
            "kpis": {
                "net_balance": total_income - total_expense,
                "total_income": total_income,
                "total_expense": total_expense,
                "total_transfers": total_transfers,
                "total_transactions": len(transactions)
            },
            "monthly_summary": formatted_monthly,
            "months": sorted(list(formatted_monthly.keys()))
        }
        self.send_json_response(response_data)

    def handle_get_transactions(self, query):
        storage = StorageService()
        active_prof_id = get_active_profile_id()
        all_txs = storage.load_transactions()

        # アクティブプロファイルの取引のみを抽出
        filtered = [t for t in all_txs if getattr(t, 'profile_id', 'profile_default') == active_prof_id]

        month = query.get("month", [None])[0]
        genre = query.get("genre", [None])[0]
        search = query.get("search", [None])[0]
        account_filter = query.get("account", [None])[0]

        if month:
            filtered = [t for t in filtered if t.date.startswith(month)]
        if genre and genre != "all":
            filtered = [t for t in filtered if t.genre == genre]
        if account_filter and account_filter != "all":
            filtered = [t for t in filtered if account_filter in t.billing_account or account_filter in t.source_name]
        if search:
            search_lower = search.lower()
            filtered = [t for t in filtered if search_lower in t.description.lower() or search_lower in t.source_name.lower()]

            filtered = [t for t in filtered if t.date.startswith(month)]
        if genre and genre != "all":
            filtered = [t for t in filtered if t.genre == genre]
        if search:
            search_lower = search.lower()
            filtered = [t for t in filtered if search_lower in t.description.lower() or search_lower in t.source_name.lower()]

        result = []
        for t in filtered:
            result.append({
                "date": t.date,
                "description": t.description,
                "amount": t.amount,
                "type": t.transaction_type.value,
                "genre": t.genre,
                "source_name": t.source_name,
                "card_number": t.card_number,
                "billing_account": t.billing_account,
                "notes": t.notes,
                "is_internal_transfer": t.is_internal_transfer,
                "profile_id": getattr(t, 'profile_id', 'profile_default')
            })

        self.send_json_response({"transactions": result, "total": len(result)})

    def handle_get_rules(self):
        classifier = GenreClassifier()
        self.send_json_response({
            "prefix_rules": classifier.prefix_rules,
            "keyword_rules": classifier.keyword_rules,
            "default_genre": classifier.default_genre
        })

    def handle_post_rules(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            config_path = "config/genre_rules.json"
            os.makedirs(os.path.dirname(config_path), exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)

            classifier = GenreClassifier()
            storage = StorageService()
            transactions = storage.load_transactions()

            reclassified_count = 0
            for tx in transactions:
                new_genre = classifier.classify(tx.description)
                if new_genre != tx.genre:
                    tx.genre = new_genre
                    reclassified_count += 1

            if reclassified_count > 0:
                storage.overwrite_all(transactions)

            self.send_json_response({
                "status": "success",
                "message": f"ルールを更新し、{reclassified_count} 件の明細を再分類しました。"
            })
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_update_transaction(self, body):
        try:
            data = json.loads(body.decode('utf-8'))
            storage = StorageService()
            transactions = storage.load_transactions()
            active_prof_id = get_active_profile_id()

            updated = False
            for t in transactions:
                if (getattr(t, 'profile_id', 'profile_default') == active_prof_id and
                    t.date == data.get("date") and 
                    t.description == data.get("description") and 
                    t.amount == data.get("amount") and 
                    t.source_name == data.get("source_name")):
                    t.genre = data.get("new_genre", t.genre)
                    updated = True
                    break

            if updated:
                storage.overwrite_all(transactions)
                self.send_json_response({"status": "success", "message": "ジャンルを更新しました。"})
            else:
                self.send_json_response({"error": "対象の取引が見つかりませんでした。"}, 404)
        except Exception as e:
            self.send_json_response({"error": str(e)}, 400)

    def handle_post_import(self, body):
        classifier = GenreClassifier()
        storage = StorageService()
        active_prof_id = get_active_profile_id()
        all_parsed_txs = []

        resources_dir = "resources"
        csv_files = sorted(glob.glob(os.path.join(resources_dir, "*.csv")))
        logs = []

        for file_path in csv_files:
            try:
                lines = read_file_lines(file_path)
                parser = get_parser_for_file(file_path, lines)
                txs = parser.parse(file_path, lines)

                for tx in txs:
                    if tx.genre == "未分類":
                        tx.genre = classifier.classify(tx.description)
                    tx.profile_id = active_prof_id

                all_parsed_txs.extend(txs)
                logs.append(f"{os.path.basename(file_path)}: {len(txs)} 件解析")
            except Exception as e:
                logs.append(f"{os.path.basename(file_path)}: エラー ({e})")

        added_count = storage.save_transactions(all_parsed_txs)
        self.send_json_response({
            "status": "success",
            "added_count": added_count,
            "logs": logs
        })

def run_server(port=PORT):
    os.makedirs(WEB_DIR, exist_ok=True)
    socketserver.TCPServer.allow_reuse_address = True
    server_address = ('', port)
    httpd = socketserver.TCPServer(server_address, AssetManagementAPIHandler)
    print(f"==================================================")
    print(f"  資産管理 Web Dashboard サーバーを起動しました")
    print(f"  URL: http://localhost:{port}")
    print(f"  停止方法: ターミナルで Control + C を押してください")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nサーバーを停止します。")
        httpd.server_close()

if __name__ == "__main__":
    port_to_use = PORT
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port_to_use = int(sys.argv[1])
    run_server(port_to_use)
