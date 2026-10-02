#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MONOPOLY GO! (v1.77.1 / 98077) — ARM64 & Tekil APK Statik Yama Aracı (Android 11/12)
====================================================================================
Bu betik, hedef ikili dosyalardaki (libil2cpp.so, libanort.so, libanogs.so,
libtoolChecker.so, libbugsnag-root-detection.so, res/xml/network_security_config.xml,
AndroidManifest.xml ve assets/EnvironmentConfig.json) gerçek dosya ofsetlerini
ve orijinal bayt dizilerini doğrulayarak güvenli statik yama uygular.
"""

import argparse
import json
import os
import shutil
import sys
from dataclasses import dataclass
from typing import List


@dataclass
class BinaryPatch:
    id: str
    group: str
    description: str
    rel_path: str
    vaddr: int
    file_offset: int
    orig_bytes: bytes
    patch_bytes: bytes
    asm_comment: str


# ============================================================================
# DOĞRULANMIŞ STATİK YAMA TABLOSU (v1.77.1 / build 98077 / arm64-v8a)
# ============================================================================
PATCH_TABLE: List[BinaryPatch] = [
    # ------------------------------------------------------------------------
    # GRUP 1: İstemci Durum Hash Doğrulaması & Anti-Desync (libil2cpp.so)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="skip_state_hash_validation",
        group="validation",
        description="TophatClientActionService.ShouldSkipValidation -> return true (89 ValidatedUserStateType hash kontrolünü atlar)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x04023894,
        file_offset=0x0401F894,
        orig_bytes=bytes.fromhex("fe0f1df8f65701a9"),
        patch_bytes=bytes.fromhex("20008052c0035fd6"),
        asm_comment="mov w0, #1; ret",
    ),

    # ------------------------------------------------------------------------
    # GRUP 2: Cihaz ve Uygulama Bütünlük Doğrulaması (libil2cpp.so)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="integrity_app_trusted",
        group="integrity",
        description="WithBuddies.Common.IntegrityReportResponse.get_IsAppTrusted -> return true",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x06FD4354,
        file_offset=0x06FD0354,
        orig_bytes=bytes.fromhex("00c04039c0035fd6"),
        patch_bytes=bytes.fromhex("20008052c0035fd6"),
        asm_comment="mov w0, #1; ret",
    ),
    BinaryPatch(
        id="integrity_device_trusted",
        group="integrity",
        description="WithBuddies.Common.IntegrityReportResponse.get_IsDeviceTrusted -> return true",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x06FD4364,
        file_offset=0x06FD0364,
        orig_bytes=bytes.fromhex("00c44039c0035fd6"),
        patch_bytes=bytes.fromhex("20008052c0035fd6"),
        asm_comment="mov w0, #1; ret",
    ),

    # ------------------------------------------------------------------------
    # GRUP 3: Oyun İçi Mekanikler (Bank Heist, Dig/Hazinedar, Community Chest)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="bank_heist_win_size_mega",
        group="gameplay",
        description="Tophat.Common.PickGame.PickMiniGame.SelectWinSize -> return PickGameWinSize.Mega (3)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x059F13F0,
        file_offset=0x059ED3F0,
        orig_bytes=bytes.fromhex("ff4301d1fe0b00f9"),
        patch_bytes=bytes.fromhex("60008052c0035fd6"),
        asm_comment="mov w0, #3; ret  (PickGameWinSize: Small=0, Medium=1, Big=2, Mega=3)",
    ),
    BinaryPatch(
        id="dig_always_key_item_hit",
        group="gameplay",
        description="Tophat.Common.MinigameDig.MinigameDigLogic.GetDigDesiredResult -> return HitDesiredType.KeyItemHit (0)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x05C8EBC4,
        file_offset=0x05C8ABC4,
        orig_bytes=bytes.fromhex("e80f1cfcfe0700f9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret  (HitDesiredType: KeyItemHit=0, ExplosiveHit=1, Miss=2)",
    ),
    BinaryPatch(
        id="community_chest_max_friends",
        group="gameplay",
        description="Tophat.Common.CommunityChestV2.CommunityChestStarting.CalculateNumberOfFriendsSelected -> return 9",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libil2cpp.so",
        vaddr=0x0603AE88,
        file_offset=0x06036E88,
        orig_bytes=bytes.fromhex("fe0f1cf8f85f01a9"),
        patch_bytes=bytes.fromhex("20018052c0035fd6"),
        asm_comment="mov w0, #9; ret  (TOTAL_GAME_SLOTS = 9)",
    ),

    # ------------------------------------------------------------------------
    # GRUP 4: Yerel Root Tespiti Kütüphaneleri (Quago & Bugsnag)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="quago_root_check_disable",
        group="root",
        description="QuagoRootDetectionNative.checkForRoot (libtoolChecker.so) -> return 0 (false)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libtoolChecker.so",
        vaddr=0x00000988,
        file_offset=0x00000988,
        orig_bytes=bytes.fromhex("ffc301d1fd7b01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="bugsnag_root_check_disable",
        group="root",
        description="RootDetector.performNativeRootChecks (libbugsnag-root-detection.so) -> return 0 (false)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libbugsnag-root-detection.so",
        vaddr=0x00000800,
        file_offset=0x00000800,
        orig_bytes=bytes.fromhex("ffc302d1fd7b09a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),

    # ------------------------------------------------------------------------
    # GRUP 5: Tencent ACE / AnoApplication CRC32, Sertifika & Çökertme Koruması
    #         (libanort.so & libanogs.so — Başlangıçta Kapanma / Crash Çözümü)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="anort_tsb_file_crc_bypass",
        group="ace_bypass",
        description="libanort.so: assets/__acinfo.tsb CRC32 doğrulaması -> her zaman eşleşti (w8 = w9)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x00063918,
        file_offset=0x00063918,
        orig_bytes=bytes.fromhex("2801881a"),
        patch_bytes=bytes.fromhex("e803092a"),
        asm_comment="csel w8, w9, w8, eq -> mov w8, w9",
    ),
    BinaryPatch(
        id="anort_so_section_crc_bypass",
        group="ace_bypass",
        description="libanort.so: SOBASE_libil2cpp.so .text CRC32 doğrulaması -> her zaman eşleşti (w8 = w9)",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x00092D7C,
        file_offset=0x00092D7C,
        orig_bytes=bytes.fromhex("4801891a"),
        patch_bytes=bytes.fromhex("e803092a"),
        asm_comment="csel w8, w9, w10, eq -> mov w8, w9",
    ),
    BinaryPatch(
        id="anort_crash_corrupt_state_disable",
        group="ace_bypass",
        description="libanort.so: crash_44690 ([x5,#0x498]=0 SIGSEGV tetikleyicisi) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x00044690,
        file_offset=0x00044690,
        orig_bytes=bytes.fromhex("fd7bbea9f44f01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anort_kill_process_disable",
        group="ace_bypass",
        description="libanort.so: kill_bb8e0 (süreç sonlandırıcı) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x000BB8E0,
        file_offset=0x000BB8E0,
        orig_bytes=bytes.fromhex("fd7bbaa9fb0b00f9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anort_kill_dispatcher_disable",
        group="ace_bypass",
        description="libanort.so: kill_fd4c8 (bütünlük hatası sonlandırıcısı) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x000FD4C8,
        file_offset=0x000FD4C8,
        orig_bytes=bytes.fromhex("fd7bbaa9fc6f01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anort_crash_corrupt_bss_disable",
        group="ace_bypass",
        description="libanort.so: crash_fdc84 (.bss 0x1d3720 tablo bozucusu) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x000FDC84,
        file_offset=0x000FDC84,
        orig_bytes=bytes.fromhex("ff8300d1fd7b01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anort_crash_corrupt_stack_disable",
        group="ace_bypass",
        description="libanort.so: crash_febbc (yığın/stack bozucusu) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanort.so",
        vaddr=0x000FEBBC,
        file_offset=0x000FEBBC,
        orig_bytes=bytes.fromhex("fd7bbca9fc5f01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anogs_kill_self_sigkill_nop",
        group="ace_bypass",
        description="libanogs.so: 0x1c82b8 bl kill(getpid(), 9) -> nop",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x001C82B8,
        file_offset=0x001C82B8,
        orig_bytes=bytes.fromhex("f6280d94"),
        patch_bytes=bytes.fromhex("1f2003d5"),
        asm_comment="nop",
    ),
    BinaryPatch(
        id="anogs_crash_corrupt_mem_disable",
        group="ace_bypass",
        description="libanogs.so: crash_2130cc (bellek bozucu) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x002130CC,
        file_offset=0x002130CC,
        orig_bytes=bytes.fromhex("fd7bbea9f44f01a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anogs_cert_verify_crash_disable",
        group="ace_bypass",
        description="libanogs.so: cert_check_2b51cc (official_cert_md5 / cert_crash kontrolü) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x002B51CC,
        file_offset=0x002B51CC,
        orig_bytes=bytes.fromhex("ff8306d1fd7b14a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anogs_crash_manager_trigger_disable",
        group="ace_bypass",
        description="libanogs.so: CrashManager::TriggerCrash (0x2e6b54, 43 bütünlük/anti-cheat çağrısı) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x002E6B54,
        file_offset=0x002E6B54,
        orig_bytes=bytes.fromhex("fd7bbda9f65701a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anogs_crash_manager_docrash_disable",
        group="ace_bypass",
        description="libanogs.so: CrashManager::DoCrash (0x2e6c64, kasıtlı SIGSEGV/bellek sıfırlama) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x002E6C64,
        file_offset=0x002E6C64,
        orig_bytes=bytes.fromhex("fd7bbba9fc6701a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),
    BinaryPatch(
        id="anogs_crash_manager_invoke_disable",
        group="ace_bypass",
        description="libanogs.so: CrashManager::InvokeCrash (0x2ea660, gecikmeli çökertme tetikleyicisi) -> return 0",
        rel_path="config.arm64_v8a/lib/arm64-v8a/libanogs.so",
        vaddr=0x002EA660,
        file_offset=0x002EA660,
        orig_bytes=bytes.fromhex("ff4301d1fd7b02a9"),
        patch_bytes=bytes.fromhex("00008052c0035fd6"),
        asm_comment="mov w0, #0; ret",
    ),

    # ------------------------------------------------------------------------
    # GRUP 6: Android AXML SSL Sertifika Sabitleme (network_security_config.xml)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="axml_unpin_api_dev",
        group="ssl_pinning",
        description="network_security_config.xml: 'api.dev.tophat.withbuddies.com' -> 'off.dev.tophat.withbuddies.com'",
        rel_path="com.scopely.monopolygo/res/xml/network_security_config.xml",
        vaddr=0x00000130,
        file_offset=0x00000130,
        orig_bytes=b"api.dev.tophat.withbuddies.com",
        patch_bytes=b"off.dev.tophat.withbuddies.com",
        asm_comment="AXML string pool in-place domain unpin (30 bytes)",
    ),
    BinaryPatch(
        id="axml_unpin_api_prod",
        group="ssl_pinning",
        description="network_security_config.xml: 'api.prod.tophat.withbuddies.com' -> 'off.prod.tophat.withbuddies.com'",
        rel_path="com.scopely.monopolygo/res/xml/network_security_config.xml",
        vaddr=0x00000151,
        file_offset=0x00000151,
        orig_bytes=b"api.prod.tophat.withbuddies.com",
        patch_bytes=b"off.prod.tophat.withbuddies.com",
        asm_comment="AXML string pool in-place domain unpin (31 bytes)",
    ),
    BinaryPatch(
        id="axml_unpin_api_stage",
        group="ssl_pinning",
        description="network_security_config.xml: 'api.stage.tophat.withbuddies.com' -> 'off.stage.tophat.withbuddies.com'",
        rel_path="com.scopely.monopolygo/res/xml/network_security_config.xml",
        vaddr=0x00000173,
        file_offset=0x00000173,
        orig_bytes=b"api.stage.tophat.withbuddies.com",
        patch_bytes=b"off.stage.tophat.withbuddies.com",
        asm_comment="AXML string pool in-place domain unpin (32 bytes)",
    ),

    # ------------------------------------------------------------------------
    # GRUP 7: Android 11/12 (API 29+) & Tekil APK Uyumluluğu (AndroidManifest.xml)
    # ------------------------------------------------------------------------
    BinaryPatch(
        id="manifest_base_min_sdk_29",
        group="manifest",
        description="com.scopely.monopolygo/AndroidManifest.xml: minSdkVersion 32 -> 29 (Android 10/11/12 uyumluluğu)",
        rel_path="com.scopely.monopolygo/AndroidManifest.xml",
        vaddr=0x000062A8,
        file_offset=0x000062A8,
        orig_bytes=bytes.fromhex("20000000"),
        patch_bytes=bytes.fromhex("1d000000"),
        asm_comment="AXML ResID 0x0101020c (minSdkVersion): 32 (0x20) -> 29 (0x1d)",
    ),
    BinaryPatch(
        id="manifest_arm64_min_sdk_29",
        group="manifest",
        description="config.arm64_v8a/AndroidManifest.xml: minSdkVersion 32 -> 29 (Android 10/11/12 uyumluluğu)",
        rel_path="config.arm64_v8a/AndroidManifest.xml",
        vaddr=0x00000454,
        file_offset=0x00000454,
        orig_bytes=bytes.fromhex("20000000"),
        patch_bytes=bytes.fromhex("1d000000"),
        asm_comment="AXML ResID 0x0101020c (minSdkVersion): 32 (0x20) -> 29 (0x1d)",
    ),
    BinaryPatch(
        id="manifest_disable_required_split_types_resid",
        group="manifest",
        description="com.scopely.monopolygo/AndroidManifest.xml: requiredSplitTypes & splitTypes ResID sıfırlama (Tekil APK desteği)",
        rel_path="com.scopely.monopolygo/AndroidManifest.xml",
        vaddr=0x0000614C,
        file_offset=0x0000614C,
        orig_bytes=bytes.fromhex("4e0601014f060101"),
        patch_bytes=bytes.fromhex("0000000000000000"),
        asm_comment="AXML ResID 0x0101064e & 0x0101064f -> 0x00000000",
    ),
    BinaryPatch(
        id="manifest_clear_required_split_types_attr",
        group="manifest",
        description="com.scopely.monopolygo/AndroidManifest.xml: requiredSplitTypes='base__abi' -> '' (Tekil APK desteği)",
        rel_path="com.scopely.monopolygo/AndroidManifest.xml",
        vaddr=0x00006210,
        file_offset=0x00006210,
        orig_bytes=bytes.fromhex("2501000039000000a000000008000003a0000000"),
        patch_bytes=bytes.fromhex("250100003a0000003c000000080000033c000000"),
        asm_comment="AXML attr requiredSplitTypes string index 0xa0 ('base__abi') -> 0x3c ('')",
    ),
    BinaryPatch(
        id="manifest_disable_vending_splits_required",
        group="manifest",
        description="com.scopely.monopolygo/AndroidManifest.xml: com.android.vending.splits.required -> false (Tekil APK desteği)",
        rel_path="com.scopely.monopolygo/AndroidManifest.xml",
        vaddr=0x0000CBB8,
        file_offset=0x0000CBB8,
        orig_bytes=bytes.fromhex("ffffffff"),
        patch_bytes=bytes.fromhex("00000000"),
        asm_comment="AXML meta-data com.android.vending.splits.required: true (0xffffffff) -> false (0x0)",
    ),
]


def verify_patches(root_dir: str, selected_groups: set) -> bool:
    print("=" * 88)
    print(f" STATİK YAMA HEDEF OFSET VE ORİJİNAL BAYT DOĞRULAMASI")
    print(f" Kök Dizin: {os.path.abspath(root_dir)}")
    print("=" * 88)
    all_ok = True

    for p in PATCH_TABLE:
        if "all" not in selected_groups and p.group not in selected_groups:
            continue
        full_path = os.path.join(root_dir, p.rel_path)
        if not os.path.exists(full_path):
            print(f"[HATA] Dosya bulunamadı: {full_path}")
            all_ok = False
            continue

        with open(full_path, "rb") as f:
            f.seek(p.file_offset)
            actual = f.read(len(p.orig_bytes))

        if actual == p.orig_bytes:
            state_str = "ORİJİNAL (Yamaya Hazır)"
        elif actual == p.patch_bytes:
            state_str = "ZATEN YAMALANMIŞ"
        else:
            state_str = "UYUŞMAZLIK (HATA!)"
            all_ok = False

        print(f"[*] [{p.group:11s}] {p.id}")
        print(f"    Açıklama   : {p.description}")
        print(f"    Dosya      : {p.rel_path}")
        print(f"    Adresler   : vaddr=0x{p.vaddr:08x} | file_offset=0x{p.file_offset:08x}")
        print(f"    Beklenen   : {p.orig_bytes.hex()}")
        print(f"    Okunan     : {actual.hex()} -> [{state_str}]")
        print(f"    Yama Kodu  : {p.patch_bytes.hex()} ({p.asm_comment})\n")

    print("=" * 88)
    print(f" Doğrulama Sonucu: {'BAŞARILI (Tüm ofset ve baytlar birebir eşleşti)' if all_ok else 'HATALI'}")
    print("=" * 88)
    return all_ok


def apply_patches(root_dir: str, selected_groups: set, api_url: str = None, no_backup: bool = False) -> bool:
    if not verify_patches(root_dir, selected_groups):
        print("[!] Ön doğrulama başarısız olduğu için yama işlemi iptal edildi.")
        return False

    applied_count = 0
    for p in PATCH_TABLE:
        if "all" not in selected_groups and p.group not in selected_groups:
            continue
        full_path = os.path.join(root_dir, p.rel_path)
        bak_path = full_path + ".bak"
        if not no_backup and not os.path.exists(bak_path):
            shutil.copy2(full_path, bak_path)

        with open(full_path, "r+b") as f:
            f.seek(p.file_offset)
            actual = f.read(len(p.orig_bytes))
            if actual == p.orig_bytes:
                f.seek(p.file_offset)
                f.write(p.patch_bytes)
                applied_count += 1
                print(f"[+] Yamalandı: {p.id} @ 0x{p.file_offset:08x} ({p.asm_comment})")
            elif actual == p.patch_bytes:
                print(f"[=] Zaten yamalı: {p.id} @ 0x{p.file_offset:08x}")

    if "all" in selected_groups or "manifest" in selected_groups:
        xapk_manifest = os.path.join(root_dir, "manifest.json")
        if os.path.exists(xapk_manifest):
            if not no_backup and not os.path.exists(xapk_manifest + ".bak"):
                shutil.copy2(xapk_manifest, xapk_manifest + ".bak")
            with open(xapk_manifest, "r", encoding="utf-8") as f:
                mdata = json.load(f)
            mdata["min_sdk_version"] = "29"
            with open(xapk_manifest, "w", encoding="utf-8") as f:
                json.dump(mdata, f, ensure_ascii=False)
            print("[+] manifest.json güncellendi (min_sdk_version=29)")

    if "all" in selected_groups or "env_config" in selected_groups:
        env_path = os.path.join(root_dir, "com.scopely.monopolygo/assets/EnvironmentConfig.json")
        if os.path.exists(env_path):
            bak_env = env_path + ".bak"
            if not no_backup and not os.path.exists(bak_env):
                shutil.copy2(env_path, bak_env)
            with open(env_path, "r", encoding="utf-8") as f:
                env_data = json.load(f)
            env_data["_buildType"] = 1          # BuildType.Debug = 1
            env_data["_mockPurchases"] = True
            env_data["_logLevel"] = 1
            if api_url:
                env_data["_apiUrl"] = api_url
            with open(env_path, "w", encoding="utf-8") as f:
                json.dump(env_data, f, indent=2)
            print(f"[+] EnvironmentConfig.json güncellendi (_buildType=1, _mockPurchases=True, _apiUrl={env_data['_apiUrl']})")

    print(f"\n[OK] Toplam {applied_count} ikili yama başarıyla uygulandı.")
    return True


def restore_patches(root_dir: str):
    restored = 0
    seen_files = set(p.rel_path for p in PATCH_TABLE)
    seen_files.add("com.scopely.monopolygo/assets/EnvironmentConfig.json")
    seen_files.add("manifest.json")
    for rel in sorted(seen_files):
        full_path = os.path.join(root_dir, rel)
        bak_path = full_path + ".bak"
        if os.path.exists(bak_path):
            shutil.move(bak_path, full_path)
            restored += 1
            print(f"[+] Orijinale döndürüldü: {rel}")
    print(f"[OK] Toplam {restored} dosya `.bak` yedeğinden geri yüklendi.")


def main():
    parser = argparse.ArgumentParser(description="MONOPOLY GO! (v1.77.1) Statik Yama Aracı")
    parser.add_argument("action", choices=["verify", "apply", "restore"], help="İşlem: verify | apply | restore")
    parser.add_argument("--root", default="/home/user/mono/out/monopoly_go", help="Çıkarılmış XAPK kök dizini")
    parser.add_argument(
        "--groups",
        default="all",
        help="Uygulanacak yama grupları (virgülle ayrılmış: all,validation,integrity,gameplay,root,ace_bypass,ssl_pinning,manifest,env_config)",
    )
    parser.add_argument("--api-url", default=None, help="EnvironmentConfig.json için özel _apiUrl (ör. http://127.0.0.1:8080)")
    parser.add_argument("--no-backup", action="store_true", help=".bak yedek dosyası oluşturma (CI/XAPK paketleme için)")
    args = parser.parse_args()

    groups = set(g.strip() for g in args.groups.split(",") if g.strip())
    if args.action == "verify":
        ok = verify_patches(args.root, groups)
        sys.exit(0 if ok else 1)
    elif args.action == "apply":
        ok = apply_patches(args.root, groups, args.api_url, args.no_backup)
        sys.exit(0 if ok else 1)
    elif args.action == "restore":
        restore_patches(args.root)


if __name__ == "__main__":
    main()
