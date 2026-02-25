#!/usr/bin/env python3
"""
check_geodata.py — Скачивает geosite.dat / geoip.dat и проверяет
наличие всех требуемых категорий (country_code / tags).

Конфигурация: required_rules.json рядом со скриптом (или путь через --config).
Выход: 0 если всё ок, 1 если есть отсутствующие теги.
"""

import argparse
import json
import os
import sys
import urllib.request
import tempfile
from pathlib import Path

# ─── Protobuf runtime descriptors (no protoc needed) ────────────────────────
from google.protobuf import descriptor_pb2 as _dpb
from google.protobuf import descriptor_pool as _pool
from google.protobuf import message_factory as _mf


def _build_protobuf_classes():
    """Build GeoSiteList and GeoIPList message classes at runtime."""
    fp = _dpb.FileDescriptorProto()
    fp.name = "geodata.proto"
    fp.package = "geodata"
    fp.syntax = "proto3"

    # GeoSite  (we only need country_code — field 1)
    m = fp.message_type.add()
    m.name = "GeoSite"
    f = m.field.add()
    f.name, f.number = "country_code", 1
    f.type = _dpb.FieldDescriptorProto.TYPE_STRING
    f.label = _dpb.FieldDescriptorProto.LABEL_OPTIONAL

    # GeoSiteList
    m = fp.message_type.add()
    m.name = "GeoSiteList"
    f = m.field.add()
    f.name, f.number = "entry", 1
    f.type = _dpb.FieldDescriptorProto.TYPE_MESSAGE
    f.label = _dpb.FieldDescriptorProto.LABEL_REPEATED
    f.type_name = ".geodata.GeoSite"

    # GeoIP  (we only need country_code — field 1)
    m = fp.message_type.add()
    m.name = "GeoIP"
    f = m.field.add()
    f.name, f.number = "country_code", 1
    f.type = _dpb.FieldDescriptorProto.TYPE_STRING
    f.label = _dpb.FieldDescriptorProto.LABEL_OPTIONAL

    # GeoIPList
    m = fp.message_type.add()
    m.name = "GeoIPList"
    f = m.field.add()
    f.name, f.number = "entry", 1
    f.type = _dpb.FieldDescriptorProto.TYPE_MESSAGE
    f.label = _dpb.FieldDescriptorProto.LABEL_REPEATED
    f.type_name = ".geodata.GeoIP"

    pool = _pool.DescriptorPool()
    pool.Add(fp)

    GeoSiteList = _mf.GetMessageClass(
        pool.FindMessageTypeByName("geodata.GeoSiteList")
    )
    GeoIPList = _mf.GetMessageClass(
        pool.FindMessageTypeByName("geodata.GeoIPList")
    )
    return GeoSiteList, GeoIPList


GeoSiteList, GeoIPList = _build_protobuf_classes()


# ─── Helpers ─────────────────────────────────────────────────────────────────

def download_file(url: str, dest: str) -> None:
    """Download a file following redirects."""
    print(f"  ⬇  Downloading {url}")
    req = urllib.request.Request(url, headers={"User-Agent": "geodata-checker/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp, open(dest, "wb") as out:
        while chunk := resp.read(1 << 16):
            out.write(chunk)
    size_mb = os.path.getsize(dest) / (1024 * 1024)
    print(f"     Saved {dest} ({size_mb:.1f} MB)")


def extract_tags_geosite(path: str) -> set[str]:
    """Parse geosite.dat and return the set of country_code values (lowercased)."""
    data = Path(path).read_bytes()
    msg = GeoSiteList()
    msg.ParseFromString(data)
    return {entry.country_code.lower() for entry in msg.entry}


def extract_tags_geoip(path: str) -> set[str]:
    """Parse geoip.dat and return the set of country_code values (lowercased)."""
    data = Path(path).read_bytes()
    msg = GeoIPList()
    msg.ParseFromString(data)
    return {entry.country_code.lower() for entry in msg.entry}


# ─── Main ────────────────────────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Check geosite/geoip .dat files for required tags")
    parser.add_argument(
        "--config",
        default=os.path.join(os.path.dirname(__file__), "required_rules.json"),
        help="Path to required_rules.json",
    )
    args = parser.parse_args()

    with open(args.config) as f:
        config = json.load(f)

    all_ok = True
    missing_report: list[str] = []

    with tempfile.TemporaryDirectory(prefix="geodata_check_") as tmpdir:

        # ── Check geosite files ──────────────────────────────────────────
        for filename, spec in config.get("geosite_files", {}).items():
            url = spec["url"]
            required = {t.lower() for t in spec["required_tags"]}
            dest = os.path.join(tmpdir, filename)

            print(f"\n{'='*60}")
            print(f"📄 Checking geosite: {filename}")
            print(f"{'='*60}")

            try:
                download_file(url, dest)
                available = extract_tags_geosite(dest)
            except Exception as e:
                msg = f"❌ FAILED to download/parse {filename}: {e}"
                print(msg)
                missing_report.append(msg)
                all_ok = False
                continue

            print(f"  📊 Total tags in file: {len(available)}")
            missing = required - available
            found = required & available

            for tag in sorted(found):
                print(f"  ✅ {tag}")
            for tag in sorted(missing):
                print(f"  ❌ MISSING: {tag}")
                missing_report.append(f"{filename}: missing tag '{tag}'")

            if missing:
                all_ok = False

        # ── Check geoip files ────────────────────────────────────────────
        for filename, spec in config.get("geoip_files", {}).items():
            url = spec["url"]
            required = {t.lower() for t in spec["required_tags"]}
            dest = os.path.join(tmpdir, filename)

            print(f"\n{'='*60}")
            print(f"📄 Checking geoip: {filename}")
            print(f"{'='*60}")

            try:
                download_file(url, dest)
                available = extract_tags_geoip(dest)
            except Exception as e:
                msg = f"❌ FAILED to download/parse {filename}: {e}"
                print(msg)
                missing_report.append(msg)
                all_ok = False
                continue

            print(f"  📊 Total tags in file: {len(available)}")
            missing = required - available
            found = required & available

            for tag in sorted(found):
                print(f"  ✅ {tag}")
            for tag in sorted(missing):
                print(f"  ❌ MISSING: {tag}")
                missing_report.append(f"{filename}: missing tag '{tag}'")

            if missing:
                all_ok = False

    # ── Summary ──────────────────────────────────────────────────────────
    print(f"\n{'='*60}")
    if all_ok:
        print("🎉 ALL CHECKS PASSED — all required tags are present.")
    else:
        print("🚨 CHECKS FAILED — missing tags detected:")
        for line in missing_report:
            print(f"   • {line}")

        # Write GitHub Actions summary if available
        summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
        if summary_path:
            with open(summary_path, "a") as sf:
                sf.write("## 🚨 Geodata Check Failed\n\n")
                sf.write("The following required tags are missing:\n\n")
                for line in missing_report:
                    sf.write(f"- `{line}`\n")
                sf.write("\n")

    print(f"{'='*60}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
