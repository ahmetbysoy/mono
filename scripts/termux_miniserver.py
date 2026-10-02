#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MONOPOLY GO! (v1.77.1 / 98077) — Termux (Ubuntu) Mini-Server & Oyun İçi Değer Özelleştirici
==========================================================================================
Bu betik, IL2CPP tersine mühendislik bulgularına dayanarak:
  1. Yerel Mini-Server (Standalone Sandbox veya Hibrit Proxy/Yamalayıcı) başlatır.
  2. Web Arayüzü (http://127.0.0.1:8080/_admin) üzerinden oyun içi değerleri canlı değiştirir:
     - Zorunlu Zar Dizisi (BoardState.ScriptedRolls)
     - Zar Çarpanı & Başlangıç Zar/Nakit Bakiyesi
     - Bank Heist Mega/Big Ödül Ağırlıkları & Çevrimdışı Bot Soygunu Kapatma (BotSteal_Enabled)
     - Dig (Hazinedar) MissChanceModifier (0.0) & PlacementBehavior (BestCase = 0)
     - Peg-E (Plinko) WinZone & Bumper Ağırlıkları
     - İstemci Durum Hash Doğrulaması Kapatma (user-state-hash-validation-v1/v2-config)
  3. Şifreli Dil Paketlerini (Localization/*/blob.unity3d) ve SuperTokenManifest dosyalarını
     gömülü AES-256-CBC anahtarlarıyla çözer (decrypt) ve yeniden paketler (encrypt).
  4. Tophat.Common.Utility.X7 (SplitMix64 + SipRound) doğrulama özetleyicisini içerir.
"""

import argparse
import copy
import gzip
import html
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

# ============================================================================
# 1. GÖMÜLÜ ŞİFRELEME ANAHTARLARI VE SABİTLER (Tophat.Common.dll'den çıkarıldı)
# ============================================================================
LOCALIZATION_AES_KEY = b"9b2f0d1a8e673c45e1f2b9c0ad3e4f6b"  # LocalizedStringsSerializer.ENCRYPTION_KEY
SUPERTOKEN_AES_KEY   = b"sT0k3n5014xEncryptSecureKey32Byt"  # SuperTokenManifestSerializer.ENCRYPTION_KEY
PROD_API_BASE_URL    = "https://api.prod.tophat.withbuddies.com"


# ============================================================================
# 2. TOPHAT.COMMON.UTILITY.X7 (ARM64 makine kodundan çözülen SplitMix64 + SipRound)
# ============================================================================
class TophatX7:
    """
    libil2cpp.so (vaddr 0x06193384..0x0619520c) içindeki gizlenmiş Tophat.Common.Utility.X7
    sınıfının birebir Python karşılığı.
    """
    F = 184       # 0xB8
    N = 32        # 0x20
    HEADER = 21   # 0x15

    @staticmethod
    def rol64(x: int, n: int) -> int:
        x &= 0xFFFFFFFFFFFFFFFF
        n &= 63
        return ((x << n) | (x >> (64 - n))) & 0xFFFFFFFFFFFFFFFF

    @staticmethod
    def splitmix64_c(x: int) -> int:
        """X7.C(ulong x) @ vaddr 0x0619469c — Stafford Mix13 (SplitMix64)"""
        x &= 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 30)
        x = (x * 0xBF58476D1CE4E5B9) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 27)
        x = (x * 0x94D049BB133111EB) & 0xFFFFFFFFFFFFFFFF
        x ^= (x >> 31)
        return x

    @classmethod
    def sipround_q(cls, v0: int, v1: int, v2: int, v3: int):
        """X7.Q(ref ulong v0, ref ulong v1, ref ulong v2, ref ulong v3) @ vaddr 0x06195114"""
        mask = 0xFFFFFFFFFFFFFFFF
        v0 = (v0 + v1) & mask
        v1 = cls.rol64(v1, 13) ^ v0
        v0 = cls.rol64(v0, 32)
        v2 = (v2 + v3) & mask
        v3 = cls.rol64(v3, 16) ^ v2
        v0 = (v0 + v3) & mask
        v3 = cls.rol64(v3, 21) ^ v0
        v2 = (v2 + v1) & mask
        v1 = cls.rol64(v1, 17) ^ v2
        v2 = cls.rol64(v2, 32)
        return v0, v1, v2, v3


# ============================================================================
# 3. DİL PAKETİ (blob.unity3d) & MANIFEST AES-256-CBC ÇÖZÜCÜ / ŞİFRELEYİCİ
# ============================================================================
def decrypt_localization_blob(input_path: str, output_json_path: str, key: bytes = LOCALIZATION_AES_KEY):
    """
    Localization/<locale>/blob.unity3d dosyasını çözer:
      İlk 16 bayt = AES-CBC IV
      Kalan baytlar = AES-256-CBC ile şifrelenmiş GZip akışı
    """
    with open(input_path, "rb") as f:
        data = f.read()
    if len(data) <= 16 or len(data) % 16 != 0:
        raise ValueError(f"Geçersiz şifreli dosya boyutu: {len(data)}")

    iv_hex = data[:16].hex()
    key_hex = key.hex()
    ciphertext = data[16:]

    proc = subprocess.run(
        ["openssl", "enc", "-d", "-aes-256-cbc", "-K", key_hex, "-iv", iv_hex],
        input=ciphertext,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"OpenSSL AES çözme hatası: {proc.stderr.decode('utf-8', errors='replace')}")

    plaintext = gzip.decompress(proc.stdout)
    with open(output_json_path, "wb") as out:
        out.write(plaintext)
    return len(plaintext)


def encrypt_localization_blob(input_json_path: str, output_blob_path: str, key: bytes = LOCALIZATION_AES_KEY):
    """
    Özelleştirilmiş JSON dil dosyasını GZip ile sıkıştırıp AES-256-CBC ile tekrar blob.unity3d formatına şifreler.
    """
    with open(input_json_path, "rb") as f:
        plaintext = f.read()

    compressed = gzip.compress(plaintext, compresslevel=9)
    iv = os.urandom(16)
    iv_hex = iv.hex()
    key_hex = key.hex()

    proc = subprocess.run(
        ["openssl", "enc", "-e", "-aes-256-cbc", "-K", key_hex, "-iv", iv_hex],
        input=compressed,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"OpenSSL AES şifreleme hatası: {proc.stderr.decode('utf-8', errors='replace')}")

    with open(output_blob_path, "wb") as out:
        out.write(iv + proc.stdout)
    return len(iv) + len(proc.stdout)


# ============================================================================
# 4. CANLI OYUN İÇİ DEĞER ÖZELLEŞTİRME PROFİLİ (RUNTIME OVERRIDES)
# ============================================================================
DEFAULT_CUSTOM_CONFIG = {
    "mode": "standalone",  # "standalone" veya "proxy"
    "disable_client_hash_validation": True,
    "player": {
        "user_id": "10000001",
        "user_name": "TermuxTycoon",
        "rolls_balance": 50000,
        "cash_balance": 999999999999,
        "net_worth_level": 15000,
        "board_config_key": "board_tutorial_newyork",
        "board_economy_key": "economy_001",
        "token_position": 0,
        "roll_multiplier": 100,
        "is_roll_multiplier_locked": False,
    },
    "dice_control": {
        "enable_scripted_rolls": False,
        "scripted_rolls": [
            {"Distance": 7, "Doubles": False},
            {"Distance": 10, "Doubles": True},
            {"Distance": 12, "Doubles": True},
        ],
        "roll_doubles_ev_multiplier": 5.0,
    },
    "bank_heist_and_shutdown": {
        "bot_steal_enabled": False,
        "friend_loss_max": 0,
        "force_mega_heist_weights": True,
        "win_size_weights": {"Small": 0, "Medium": 0, "Big": 10, "Mega": 90},
        "tries_to_force_jackpot": 1,
        "blocked_pity_increment_percent": 100,
    },
    "minigames": {
        "dig_miss_chance_modifier": 0.0,     # 0.0 = Boş çıkma/hazine kaydırma kapalı
        "dig_placement_behavior": 0,         # 0 = BestCase, 1 = FairAndBalanced, 2 = Evil
        "plinko_force_center_winzone": True,
        "community_chest_friends_selected": 9,  # 9/9 arkadaş seçimi -> Jackpot paket
        "coop_mega_spin_chance_override": 1.0,  # %100 Mega Spin şansı
    },
}


class CustomizerState:
    def __init__(self, config_path: str, record_dir: str):
        self.config_path = config_path
        self.record_dir = record_dir
        self.request_log = []
        self.action_seq_id = 1
        os.makedirs(self.record_dir, exist_ok=True)
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                self.cfg = json.load(f)
        else:
            self.cfg = copy.deepcopy(DEFAULT_CUSTOM_CONFIG)
            self.save()

    def save(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.cfg, f, indent=2, ensure_ascii=False)

    def log_request(self, method: str, path: str, status: int, note: str = ""):
        entry = {
            "time": time.strftime("%H:%M:%S"),
            "method": method,
            "path": path,
            "status": status,
            "note": note,
        }
        self.request_log.insert(0, entry)
        if len(self.request_log) > 100:
            self.request_log.pop()

    # ------------------------------------------------------------------------
    # Oyun İçi Değer Yamalayıcılar (BoardDataResponse & UserStateGroup)
    # ------------------------------------------------------------------------
    def patch_board_data_response(self, data: dict) -> dict:
        """
        boards/datav2 (Tophat.Common.Board.BoardDataResponse) yanıtındaki oyun içi
        konfigürasyonları (AutoConfig, BankHeist, Dig, Plinko, HashValidation) özelleştirir.
        """
        if not isinstance(data, dict):
            data = {}

        bh = self.cfg["bank_heist_and_shutdown"]
        mg = self.cfg["minigames"]
        dc = self.cfg["dice_control"]

        # 1. GameAutoConfigurationDataV2 yaması
        auto_cfg = data.setdefault("GameAutoConfigurationDataV2", {})

        # İstemci durum hash doğrulamasını (UserStateHashValidationV1/V2Config) devre dışı bırak
        if self.cfg.get("disable_client_hash_validation", True):
            for key in ("user-state-hash-validation-v1-config", "user-state-hash-validation-v2-config"):
                auto_cfg[key] = {
                    "Key": key,
                    "Value": {"EnabledList": [], "DisabledList": []},
                    "OriginalStringValue": '{"EnabledList":[],"DisabledList":[]}',
                    "Signature": "termux-local-override",
                }

        # PvP Steal & Çevrimdışı Bot Soygunu (pvp-steal-v2)
        pvp_val = {
            "BotSteal_Enabled": bh["bot_steal_enabled"],
            "FriendLoss_Max": bh["friend_loss_max"],
            "PvPSteal_LossToBot": 0.0 if not bh["bot_steal_enabled"] else 0.1,
            "BotTimer_Min": 9999999,
            "BotTimer_Max": 9999999,
        }
        auto_cfg["pvp-steal-v2"] = {
            "Key": "pvp-steal-v2",
            "Value": pvp_val,
            "OriginalStringValue": json.dumps(pvp_val),
            "Signature": "termux-local-override",
        }

        # Bank Heist Ödül Ağırlıkları (bank-heist-v2)
        if bh.get("force_mega_heist_weights"):
            bh_val = {
                "WinSizeWeights": bh["win_size_weights"],
                "PicksToWin": 3,
            }
            auto_cfg["bank-heist-v2"] = {
                "Key": "bank-heist-v2",
                "Value": bh_val,
                "OriginalStringValue": json.dumps(bh_val),
                "Signature": "termux-local-override",
            }

        # Çift Zar Beklenen Değer Çarpanı (doubles-roll-ev-multiplier-v2)
        doubles_val = {"Multiplier": dc["roll_doubles_ev_multiplier"]}
        auto_cfg["doubles-roll-ev-multiplier-v2"] = {
            "Key": "doubles-roll-ev-multiplier-v2",
            "Value": doubles_val,
            "OriginalStringValue": json.dumps(doubles_val),
            "Signature": "termux-local-override",
        }

        # 2. MinigameDigConfigs (Hazinedar / Dig) yaması
        dig_configs = data.get("MinigameDigConfigs")
        if isinstance(dig_configs, dict):
            for _, dcfg in dig_configs.items():
                if isinstance(dcfg, dict) and isinstance(dcfg.get("Levels"), list):
                    for lvl in dcfg["Levels"]:
                        if isinstance(lvl, dict):
                            lvl["MissChanceModifier"] = mg["dig_miss_chance_modifier"]
                            lvl["PlacementBehavior"] = mg["dig_placement_behavior"]

        # 3. BankHeistSeasonalConfigs & HostileTakeoverSeasonalConfigs Pity yaması
        for sec_key in ("BankHeistSeasonalConfigs", "HostileTakeoverSeasonalConfigs"):
            sec = data.get(sec_key)
            if isinstance(sec, dict):
                for _, scfg in sec.items():
                    if isinstance(scfg, dict):
                        scfg["TriesToForceJackpot"] = bh["tries_to_force_jackpot"]
                        scfg["BlockedPityIncrementPercent"] = bh["blocked_pity_increment_percent"]

        return data

    def patch_user_state_response(self, data: dict) -> dict:
        """
        user-state/get-state (Tophat.Common.Board.UserStateGroup) ve boards/state
        yanıtlarındaki oyuncu bakiyesini, tahta durumunu ve zorunlu zarları (ScriptedRolls) özelleştirir.
        """
        if not isinstance(data, dict):
            data = {}

        p = self.cfg["player"]
        dc = self.cfg["dice_control"]

        board_state = data.setdefault("BoardState", {})
        board_state.setdefault("BoardConfigKey", p["board_config_key"])
        board_state.setdefault("BoardEconomyKey", p["board_economy_key"])
        board_state["TokenPosition"] = p["token_position"]
        board_state["RollMultiplier"] = p["roll_multiplier"]
        board_state["IsRollMultiplierLocked"] = p["is_roll_multiplier_locked"]

        if dc.get("enable_scripted_rolls"):
            board_state["ScriptedRolls"] = dc["scripted_rolls"]
        else:
            board_state.setdefault("ScriptedRolls", [])

        # Net Worth & Envanter özet bilgileri
        networth = data.setdefault("NetWorthState", {})
        networth["NetWorthLevel"] = p["net_worth_level"]

        return data

    def build_standalone_inventory(self) -> dict:
        p = self.cfg["player"]
        return {
            "Commodities": {
                "currency_rolls": {"CommodityId": "currency_rolls", "Quantity": p["rolls_balance"]},
                "currency_cash": {"CommodityId": "currency_cash", "Quantity": p["cash_balance"]},
                "shields": {"CommodityId": "shields", "Quantity": 5},
            }
        }


# ============================================================================
# 5. HTTP MINI-SERVER & ADMIN KONTROL PANELİ
# ============================================================================
def create_handler(state: CustomizerState):
    class TophatMiniServerHandler(BaseHTTPRequestHandler):
        server_version = "TophatTermuxMiniServer/1.77.1"

        def log_message(self, fmt, *args):
            sys.stdout.write(f"[{time.strftime('%H:%M:%S')}] {self.address_string()} - {fmt % args}\n")

        def _read_body(self) -> bytes:
            length = int(self.headers.get("Content-Length", "0") or "0")
            return self.rfile.read(length) if length > 0 else b""

        def _send_json(self, obj: dict, status: int = 200):
            body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self, html_text: str, status: int = 200):
            body = html_text.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        # --------------------------------------------------------------------
        # Web Kontrol Paneli (/_admin)
        # --------------------------------------------------------------------
        def _render_admin_page(self, msg: str = ""):
            cfg_json = html.escape(json.dumps(state.cfg, indent=2, ensure_ascii=False))
            rows = "".join(
                f"<tr><td>{e['time']}</td><td><b>{e['method']}</b></td>"
                f"<td><code>{html.escape(e['path'])}</code></td>"
                f"<td>{e['status']}</td><td>{html.escape(e['note'])}</td></tr>"
                for e in state.request_log[:25]
            )
            if not rows:
                rows = "<tr><td colspan='5'>Henüz istek kaydedilmedi.</td></tr>"

            alert_html = f"<div class='alert'>{html.escape(msg)}</div>" if msg else ""
            page = f"""<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>MONOPOLY GO! Termux Mini-Server Kontrol Paneli</title>
  <style>
    body {{ font-family: system-ui, -apple-system, sans-serif; background: #0f172a; color: #e2e8f0; margin: 0; padding: 20px; }}
    .container {{ max-width: 1080px; margin: 0 auto; }}
    h1 {{ color: #38bdf8; margin-top: 0; }}
    .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
    @media (max-width: 800px) {{ .grid {{ grid-template-columns: 1fr; }} }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px; }}
    textarea {{ width: 100%; height: 440px; background: #090d16; color: #a7f3d0; border: 1px solid #475569; border-radius: 6px; padding: 10px; font-family: monospace; font-size: 13px; box-sizing: border-box; }}
    button {{ background: #0284c7; color: white; border: none; padding: 10px 18px; border-radius: 6px; font-weight: 600; cursor: pointer; margin-top: 10px; }}
    button:hover {{ background: #0369a1; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 13px; }}
    th, td {{ border-bottom: 1px solid #334155; padding: 8px; text-align: left; }}
    th {{ color: #94a3b8; }}
    .alert {{ background: #065f46; color: #d1fae5; padding: 10px 14px; border-radius: 6px; margin-bottom: 16px; }}
    code {{ color: #f472b6; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>MONOPOLY GO! (v1.77.1) — Termux Mini-Server</h1>
    {alert_html}
    <div class="grid">
      <div class="card">
        <h3>Canlı Oyun İçi Değerler & Özelleştirme (JSON)</h3>
        <form method="POST" action="/_admin/save">
          <textarea name="config_json">{cfg_json}</textarea>
          <button type="submit">Değerleri Kaydet ve Anında Uygula</button>
        </form>
      </div>
      <div class="card">
        <h3>Son Yakalanan Oyun İstekleri (API Log)</h3>
        <form method="POST" action="/_admin/simulate" style="margin-bottom: 12px;">
          <button type="submit" style="margin-top:0; background:#059669;">Örnek Oyun İsteklerini Simüle Et (Test)</button>
        </form>
        <table>
          <thead><tr><th>Saat</th><th>Metot</th><th>Uç Nokta</th><th>Kod</th><th>Not</th></tr></thead>
          <tbody>{rows}</tbody>
        </table>
      </div>
    </div>
  </div>
</body>
</html>"""
            self._send_html(page)

        # --------------------------------------------------------------------
        # Hibrit Proxy Yardımcı Metodu
        # --------------------------------------------------------------------
        def _forward_to_prod(self, method: str, path: str, body: bytes):
            url = PROD_API_BASE_URL + path
            headers = {
                k: v for k, v in self.headers.items()
                if k.lower() not in ("host", "content-length", "connection")
            }
            req = urllib.request.Request(url, data=body if method in ("POST", "PUT", "PATCH") else None, headers=headers, method=method)
            try:
                with urllib.request.urlopen(req, timeout=15) as resp:
                    raw = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip" or raw[:2] == b"\x1f\x8b":
                        raw = gzip.decompress(raw)
                    return resp.status, json.loads(raw.decode("utf-8"))
            except Exception as e:
                return 502, {"error": str(e)}

        # --------------------------------------------------------------------
        # Ana İstek Yönlendirici (GET / POST / PUT)
        # --------------------------------------------------------------------
        def _handle_api(self, method: str):
            parsed = urllib.parse.urlparse(self.path)
            route = parsed.path.lstrip("/")
            body = self._read_body()

            # 1. Admin arayüzü (/ veya /_admin)
            if route in ("", "_admin") and method == "GET":
                return self._render_admin_page()
            if route == "_admin/simulate" and method == "POST":
                state.log_request("POST", "/device/open", 200, "DeviceOpen (Simülasyon)")
                state.log_request("GET", "/boards/datav2", 200, "BoardDataResponse yamalandı (Simülasyon)")
                state.log_request("GET", "/user-state/get-state", 200, "UserState / ScriptedRolls yamalandı (Simülasyon)")
                state.log_request("POST", "/clientactions", 200, "ClientActions onaylandı (Simülasyon)")
                return self._render_admin_page("4 temel oyun başlatma isteği (device/open, boards/datav2, user-state/get-state, clientactions) başarıyla simüle edildi!")
            if route == "_admin/save" and method == "POST":
                form = urllib.parse.parse_qs(body.decode("utf-8", errors="replace"))
                raw_json = form.get("config_json", ["{}"])[0]
                try:
                    state.cfg = json.loads(raw_json)
                    state.save()
                    return self._render_admin_page("Yeni oyun içi değerler kaydedildi ve etkinleştirildi!")
                except Exception as e:
                    return self._render_admin_page(f"JSON Hatası: {e}")

            # 2. Hibrit Proxy modundaysa önce gerçek sunucudan yanıtı al veya önbellekten oku
            base_data = {}
            note = f"mode={state.cfg.get('mode', 'standalone')}"
            if state.cfg.get("mode") == "proxy":
                status, prod_data = self._forward_to_prod(method, self.path, body)
                if status == 200 and isinstance(prod_data, dict):
                    base_data = prod_data
                    # Yanıtı diske kaydet (ResponseRecorder benzeri)
                    safe_name = route.replace("/", "_").replace("$", "batch_") or "root"
                    baked_file = os.path.join(state.record_dir, f"{safe_name}.json")
                    with open(baked_file, "w", encoding="utf-8") as bf:
                        json.dump(base_data, bf, indent=2, ensure_ascii=False)

            # 3. Uç Noktaya Göre Özelleştirme (NetworkingRoutes)
            p = state.cfg["player"]

            if route == "device/open":
                resp = base_data or {
                    "User": {"Id": p["user_id"], "Name": p["user_name"]},
                    "SessionToken": "termux-local-session-token",
                    "NewSessionToken": "termux-local-session-token",
                    "PlaygamiNamespace": "monopolygo",
                    "IsGdprEligible": False,
                }
                state.log_request(method, self.path, 200, "DeviceOpen (Oturum Açıldı)")
                return self._send_json(resp)

            if route in ("me/sessions", "me/sessions/autologin"):
                resp = base_data or {
                    "User": {"Id": p["user_id"], "Name": p["user_name"]},
                    "SessionToken": "termux-local-session-token",
                }
                state.log_request(method, self.path, 200, "AutoLogin / Session")
                return self._send_json(resp)

            if route == "boards/datav2":
                patched = state.patch_board_data_response(base_data)
                state.log_request(method, self.path, 200, "BoardDataResponse yamalandı")
                return self._send_json(patched)

            if route in ("user-state/get-state", "boards/state"):
                patched = state.patch_user_state_response(base_data)
                state.log_request(method, self.path, 200, "UserState / ScriptedRolls yamalandı")
                return self._send_json(patched)

            if route in ("inventory/me/inventory", "inventory/adjust"):
                inv = base_data or state.build_standalone_inventory()
                if "Commodities" in inv:
                    inv["Commodities"]["currency_rolls"] = {"CommodityId": "currency_rolls", "Quantity": p["rolls_balance"]}
                    inv["Commodities"]["currency_cash"] = {"CommodityId": "currency_cash", "Quantity": p["cash_balance"]}
                state.log_request(method, self.path, 200, f"Envanter (Zar={p['rolls_balance']})")
                return self._send_json(inv)

            if route == "clientactions":
                # İstemciden gelen ClientActionsRequest paketini çözümle ve tüm aksiyonları 'Processed' olarak onayla
                processed_ids = []
                try:
                    req_json = json.loads(body.decode("utf-8")) if body else {}
                    actions = req_json.get("ClientActions") or req_json.get("clientActions") or []
                    for act in actions:
                        aid = act.get("Id") or act.get("id")
                        if aid is not None:
                            processed_ids.append(aid)
                            state.action_seq_id = max(state.action_seq_id, int(aid))
                except Exception:
                    pass
                resp = {
                    "Processed": processed_ids,
                    "Unprocessed": [],
                    "Failed": [],
                    "FailedDetails": {},
                    "RetryAfter": 0,
                    "IsBlockedAction": False,
                }
                state.log_request(method, self.path, 200, f"ClientActions onaylandı ({len(processed_ids)} aksiyon)")
                return self._send_json(resp)

            if route == "clientactionsequences/last":
                resp = {"LastProcessedClientActionId": state.action_seq_id}
                state.log_request(method, self.path, 200, f"LastSeqId={state.action_seq_id}")
                return self._send_json(resp)

            if route in ("int/n", "int/r"):
                # Google Play Integrity / App Attest doğrulamasını her zaman güvenilir (Trusted) döndür
                resp = {
                    "Nonce": "dGVybXV4LWxvY2FsLW5vbmNl",
                    "IsAppTrusted": True,
                    "IsDeviceTrusted": True,
                }
                state.log_request(method, self.path, 200, "Integrity Trusted=True")
                return self._send_json(resp)

            if route == "bankheist/bot_heist_me":
                # Çevrimdışı bot soygunu isteğini engelle
                state.log_request(method, self.path, 200, "Bot soygunu engellendi!")
                return self._send_json({"BlockedByMiniServer": True})

            # Varsayılan yanıt
            state.log_request(method, self.path, 200, note)
            return self._send_json(base_data or {"status": "ok", "route": route})

        def do_GET(self):
            self._handle_api("GET")

        def do_POST(self):
            self._handle_api("POST")

        def do_PUT(self):
            self._handle_api("PUT")

    return TophatMiniServerHandler


# ============================================================================
# 6. KOMUT SATIRI ARAYÜZÜ (CLI)
# ============================================================================
def main():
    parser = argparse.ArgumentParser(description="MONOPOLY GO! Termux (Ubuntu) Mini-Server & Özelleştirme Aracı")
    sub = parser.add_subparsers(dest="cmd")

    # Komut 1: serve
    p_serve = sub.add_parser("serve", help="Yerel Mini-Server ve Web Kontrol Panelini başlatır")
    p_serve.add_argument("--host", default="0.0.0.0", help="Dinlenecek IP adresi (varsayılan: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8080, help="Port numarası (varsayılan: 8080)")
    p_serve.add_argument("--config", default="custom_values.json", help="Özelleştirme JSON dosyası yolu")
    p_serve.add_argument("--record-dir", default="baked_responses", help="Kaydedilen sunucu yanıtları klasörü")

    # Komut 2: decrypt-loc
    p_dec = sub.add_parser("decrypt-loc", help="Şifreli Localization blob.unity3d dosyasını JSON'a çözer")
    p_dec.add_argument("input_blob", help="Girdi blob.unity3d dosyası")
    p_dec.add_argument("output_json", help="Çıktı JSON dosyası")

    # Komut 3: encrypt-loc
    p_enc = sub.add_parser("encrypt-loc", help="Düzenlenmiş JSON dil dosyasını tekrar blob.unity3d olarak şifreler")
    p_enc.add_argument("input_json", help="Girdi JSON dosyası")
    p_enc.add_argument("output_blob", help="Çıktı blob.unity3d dosyası")

    # Komut 4: selftest
    sub.add_parser("selftest", help="X7 algoritmasını ve şifreleme/yama fonksiyonlarını test eder")

    args = parser.parse_args()

    if args.cmd == "decrypt-loc":
        sz = decrypt_localization_blob(args.input_blob, args.output_json)
        print(f"[+] Başarıyla çözüldü: {args.output_json} ({sz:,} bayt)")
        return

    if args.cmd == "encrypt-loc":
        sz = encrypt_localization_blob(args.input_json, args.output_blob)
        print(f"[+] Başarıyla şifrelendi: {args.output_blob} ({sz:,} bayt)")
        return

    if args.cmd == "selftest":
        print("[*] 1. Tophat.Common.Utility.X7 (SplitMix64 + SipRound) testi...")
        h = TophatX7.splitmix64_c(0x123456789ABCDEF0)
        v0, v1, v2, v3 = TophatX7.sipround_q(h, h ^ 1, h ^ 2, h ^ 3)
        print(f"    X7.C(0x123456789ABCDEF0) = 0x{h:016x}")
        print(f"    X7.Q(...)                = (0x{v0:016x}, 0x{v1:016x}, 0x{v2:016x}, 0x{v3:016x})")

        print("[*] 2. BoardDataResponse & UserState yamalama testi...")
        st = CustomizerState("/tmp/test_custom_values.json", "/tmp/test_baked")
        bd = st.patch_board_data_response({"MinigameDigConfigs": {"dig_1": {"Levels": [{"MissChanceModifier": 0.5, "PlacementBehavior": 2}]}}})
        us = st.patch_user_state_response({})
        assert bd["GameAutoConfigurationDataV2"]["pvp-steal-v2"]["Value"]["BotSteal_Enabled"] is False
        assert bd["MinigameDigConfigs"]["dig_1"]["Levels"][0]["MissChanceModifier"] == 0.0
        assert us["BoardState"]["RollMultiplier"] == 100
        print("    [+] Tüm özelleştirme yamaları doğrulandı!")
        return

    # Varsayılan: serve
    host = getattr(args, "host", "0.0.0.0")
    port = getattr(args, "port", 8080)
    cfg_path = getattr(args, "config", "custom_values.json")
    rec_dir = getattr(args, "record_dir", "baked_responses")

    state = CustomizerState(cfg_path, rec_dir)
    srv = ThreadingHTTPServer((host, port), create_handler(state))
    print(f"==================================================================")
    print(f" MONOPOLY GO! Termux Mini-Server Aktif: http://{host}:{port}")
    print(f" Web Kontrol Paneli                   : http://127.0.0.1:{port}/_admin")
    print(f" Yapılandırma Dosyası                 : {os.path.abspath(cfg_path)}")
    print(f"==================================================================")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Sunucu kapatılıyor...")
        srv.server_close()


if __name__ == "__main__":
    main()
