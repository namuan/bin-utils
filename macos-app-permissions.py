#!/usr/bin/env -S uv run --quiet --script
# /// script
# dependencies = []
# ///
"""
Audit macOS app privacy permissions recorded by the Transparency, Consent, and
Control (TCC) service.

The script reads TCC databases only; it does not grant, revoke, or reset any
permission. The user database is scanned by default along with the system
database when it is readable.

Usage:
./macos-app-permissions.py                 # Prints a generated dashboard path
./macos-app-permissions.py --open          # Opens the generated dashboard
./macos-app-permissions.py --format json > permissions.json
./macos-app-permissions.py --format table --app Zoom --status allowed
sudo ./macos-app-permissions.py --scope system

macOS protects these databases. Grant the calling terminal Full Disk Access in
System Settings > Privacy & Security > Full Disk Access if the user database
cannot be read. Use sudo for system-wide records when necessary.
"""

import csv
import json
import logging
import os
import platform
import sqlite3
import subprocess
import sys
import tempfile
import unicodedata
from argparse import ArgumentParser, RawDescriptionHelpFormatter
from datetime import datetime
from pathlib import Path

USER_TCC_DATABASE = Path.home() / "Library/Application Support/com.apple.TCC/TCC.db"
SYSTEM_TCC_DATABASE = Path("/Library/Application Support/com.apple.TCC/TCC.db")
DASHBOARD_TEMPLATE = Path(__file__).with_name("macos-permissions-dashboard.html")
DASHBOARD_DATA_MARKER = (
    "<!-- EMBEDDED_AUDIT_DATA_PLACEHOLDER: The Python generator replaces this comment with a JSON array. -->"
)

SERVICE_NAMES = {
    "kTCCServiceAccessibility": "Accessibility",
    "kTCCServiceAddressBook": "Contacts",
    "kTCCServiceAppleEvents": "Automation",
    "kTCCServiceBluetoothAlways": "Bluetooth",
    "kTCCServiceCalendar": "Calendars",
    "kTCCServiceCamera": "Camera",
    "kTCCServiceFileProviderDomain": "File Provider Domains",
    "kTCCServiceFocusStatus": "Focus Status",
    "kTCCServiceLiverpool": "Local Network",
    "kTCCServiceListenEvent": "Input Monitoring",
    "kTCCServiceLocation": "Location Services",
    "kTCCServiceMediaLibrary": "Media & Apple Music",
    "kTCCServiceMicrophone": "Microphone",
    "kTCCServicePhotos": "Photos",
    "kTCCServicePostEvent": "Accessibility",
    "kTCCServiceReminders": "Reminders",
    "kTCCServiceScreenCapture": "Screen & System Audio Recording",
    "kTCCServiceShareKit": "ShareKit",
    "kTCCServiceSiri": "Siri",
    "kTCCServiceSystemPolicyAllFiles": "Full Disk Access",
    "kTCCServiceSystemPolicyDesktopFolder": "Desktop Folder",
    "kTCCServiceSystemPolicyDocumentsFolder": "Documents Folder",
    "kTCCServiceSystemPolicyDownloadsFolder": "Downloads Folder",
    "kTCCServiceSystemPolicyNetworkVolumes": "Network Volumes",
    "kTCCServiceSystemPolicyRemovableVolumes": "Removable Volumes",
    "kTCCServiceUbiquity": "iCloud Drive",
    "kTCCServiceUserTracking": "App Tracking",
    "kTCCServiceWillow": "Nearby Interactions",
}

AUTH_VALUES = {
    0: "Denied",
    1: "Unknown",
    2: "Allowed",
    3: "Limited",
}

AUTH_REASONS = {
    1: "Error",
    2: "User consent",
    3: "User setting",
    4: "System setting",
    5: "Service policy",
    6: "MDM policy",
    7: "Override policy",
    8: "Missing usage description",
    9: "Prompt timed out",
    10: "Preflight unknown",
    11: "Entitlement policy",
    12: "App type policy",
}


def setup_logging(verbosity):
    logging_level = logging.WARNING
    if verbosity == 1:
        logging_level = logging.INFO
    elif verbosity >= 2:
        logging_level = logging.DEBUG

    logging.basicConfig(
        handlers=[logging.StreamHandler()],
        format="%(asctime)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        level=logging_level,
    )
    logging.captureWarnings(capture=True)


def parse_args():
    parser = ArgumentParser(description=__doc__, formatter_class=RawDescriptionHelpFormatter)
    parser.add_argument(
        "-v",
        "--verbose",
        action="count",
        default=0,
        dest="verbose",
        help="Increase verbosity of logging output",
    )
    parser.add_argument(
        "--scope",
        choices=("all", "user", "system"),
        default="all",
        help="TCC database to audit (default: all)",
    )
    parser.add_argument(
        "--app",
        metavar="TEXT",
        help="Only show apps whose bundle identifier or path contains TEXT",
    )
    parser.add_argument(
        "--service",
        metavar="TEXT",
        help="Only show permissions whose macOS service or display name contains TEXT",
    )
    parser.add_argument(
        "--status",
        choices=("allowed", "denied", "limited", "unknown"),
        help="Only show records with this permission status",
    )
    parser.add_argument(
        "--format",
        choices=("html", "table", "json", "csv"),
        default="html",
        help="Output format (default: html)",
    )
    parser.add_argument(
        "--open",
        action="store_true",
        help="Open the generated HTML dashboard in the default application",
    )
    return parser.parse_args()


def database_paths(scope):
    databases = []
    if scope in ("all", "user"):
        databases.append(("user", USER_TCC_DATABASE))
    if scope in ("all", "system"):
        databases.append(("system", SYSTEM_TCC_DATABASE))
    return databases


def readable_columns(connection):
    return {row[1] for row in connection.execute("PRAGMA table_info(access)")}


def describe_service(service):
    if service.startswith("kTCCService"):
        fallback_name = service[len("kTCCService") :]
    else:
        fallback_name = service
    return SERVICE_NAMES.get(service, fallback_name)


def describe_timestamp(value):
    if not value:
        return ""
    try:
        return datetime.fromtimestamp(int(value)).astimezone().isoformat(timespec="seconds")
    except (OverflowError, OSError, TypeError, ValueError):
        return str(value)


def normalise_record(scope, database, row, columns):
    if "auth_value" in columns:
        auth_value = row["auth_value"]
        status = AUTH_VALUES.get(auth_value, f"Unknown ({auth_value})")
    else:
        auth_value = row["allowed"]
        status = "Allowed" if auth_value else "Denied"

    reason_value = row["auth_reason"] if "auth_reason" in columns else None
    reason = AUTH_REASONS.get(reason_value, "")
    if reason_value is not None and not reason:
        reason = f"Unknown ({reason_value})"

    indirect_object = row["indirect_object_identifier"] if "indirect_object_identifier" in columns else ""
    return {
        "scope": scope,
        "database": str(database),
        "app": row["client"],
        "app_type": row["client_type"] if "client_type" in columns else None,
        "service": row["service"],
        "permission": describe_service(row["service"]),
        "status": status,
        "reason": reason,
        "last_modified": describe_timestamp(row["last_modified"]) if "last_modified" in columns else "",
        "indirect_object": indirect_object or "",
        "flags": row["flags"] if "flags" in columns else None,
        "policy_id": row["policy_id"] if "policy_id" in columns else None,
    }


def read_database(scope, database):
    if not database.is_file():
        logging.warning("The %s TCC database does not exist: %s", scope, database)
        return [], False

    try:
        connection = sqlite3.connect(f"{database.as_uri()}?mode=ro", uri=True)
        connection.row_factory = sqlite3.Row
        with connection:
            columns = readable_columns(connection)
            required_columns = {"client", "service"}
            if not required_columns.issubset(columns) or not ({"auth_value", "allowed"} & columns):
                raise sqlite3.DatabaseError("unrecognised TCC access table schema")
            records = [
                normalise_record(scope, database, row, columns) for row in connection.execute("SELECT * FROM access")
            ]
        connection.close()
    except (OSError, sqlite3.Error) as error:
        logging.warning("Could not read %s TCC database (%s): %s", scope, database, error)
        return [], False

    logging.debug("Read %d records from %s", len(records), database)
    return records, True


def matches_filters(record, args):
    if args.app and args.app.casefold() not in record["app"].casefold():
        return False
    if args.service:
        needle = args.service.casefold()
        if needle not in record["service"].casefold() and needle not in record["permission"].casefold():
            return False
    return not args.status or record["status"].casefold().startswith(args.status)


def safe_display_value(value):
    value = str(value or "")
    return "".join(
        character if unicodedata.category(character) != "Cc" else rf"\x{ord(character):02x}" for character in value
    )


def truncate(value, width):
    value = safe_display_value(value)
    return value if len(value) <= width else f"{value[: width - 1]}…"


def write_table(records):
    columns = (
        ("Scope", "scope", 6),
        ("App", "app", 42),
        ("Permission", "permission", 34),
        ("Target", "indirect_object", 28),
        ("Status", "status", 9),
        ("Reason", "reason", 22),
        ("Last modified", "last_modified", 25),
    )
    widths = [
        max(len(title), min(width, max((len(safe_display_value(record[key])) for record in records), default=0)))
        for title, key, width in columns
    ]
    header = "  ".join(title.ljust(width) for (title, _, _), width in zip(columns, widths))
    print(header)
    print("  ".join("-" * width for width in widths))
    for record in records:
        values = (truncate(record[key], width).ljust(width) for (_, key, _), width in zip(columns, widths))
        print("  ".join(values))


def safe_csv_value(value):
    value = "" if value is None else str(value)
    if value.lstrip().startswith(("=", "+", "-", "@")):
        value = f"'{value}"
    return safe_display_value(value) if sys.stdout.isatty() else value


def write_output(records, output_format):
    if output_format == "json":
        print(json.dumps(records, indent=2, sort_keys=True))
    elif output_format == "csv":
        fieldnames = (
            list(records[0])
            if records
            else [
                "scope",
                "database",
                "app",
                "app_type",
                "service",
                "permission",
                "status",
                "reason",
                "last_modified",
                "indirect_object",
                "flags",
                "policy_id",
            ]
        )
        writer = csv.DictWriter(sys.stdout, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow({field: safe_csv_value(record.get(field)) for field in fieldnames})
    elif records:
        write_table(records)
    else:
        print("No matching TCC permission records found.")


def generate_dashboard(records):
    try:
        template = DASHBOARD_TEMPLATE.read_text(encoding="utf-8")
    except OSError as error:
        raise RuntimeError(f"could not read dashboard template {DASHBOARD_TEMPLATE}: {error}") from error

    if DASHBOARD_DATA_MARKER not in template:
        raise RuntimeError(f"dashboard template has no embedded-data marker: {DASHBOARD_TEMPLATE}")

    embedded_data = json.dumps(records, ensure_ascii=False, separators=(",", ":"))
    embedded_data = embedded_data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    dashboard = template.replace(DASHBOARD_DATA_MARKER, embedded_data, 1)

    file_descriptor, file_name = tempfile.mkstemp(prefix="macos-permissions-dashboard-", suffix=".html")
    dashboard_path = Path(file_name)
    try:
        with os.fdopen(file_descriptor, "w", encoding="utf-8") as dashboard_file:
            dashboard_file.write(dashboard)
    except OSError:
        try:
            dashboard_path.unlink()
        except FileNotFoundError:
            pass
        raise
    return dashboard_path


def write_dashboard(records, should_open):
    try:
        dashboard_path = generate_dashboard(records)
        if should_open:
            subprocess.run(["open", str(dashboard_path)], check=True)
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        logging.error("Could not generate the HTML dashboard: %s", error)
        return 2

    print(dashboard_path)
    return 0


def main(args):
    if args.open and args.format != "html":
        logging.error("--open can only be used with the default HTML output.")
        return 2

    if platform.system() != "Darwin":
        logging.warning("This script audits macOS TCC databases and is intended to run on macOS.")

    records = []
    audit_results = []
    for scope, database in database_paths(args.scope):
        database_records, was_read = read_database(scope, database)
        records.extend(database_records)
        audit_results.append(was_read)

    if not any(audit_results):
        logging.error("No requested TCC database could be audited.")
        return 2
    if args.scope != "all" and not all(audit_results):
        logging.error("The requested %s TCC database could not be audited.", args.scope)
        return 2

    records = [record for record in records if matches_filters(record, args)]
    records.sort(key=lambda record: (record["app"].casefold(), record["permission"], record["scope"]))
    logging.info("Reporting %d TCC permission records", len(records))
    if args.format == "html":
        return write_dashboard(records, args.open)
    write_output(records, args.format)
    return 0


if __name__ == "__main__":
    args = parse_args()
    setup_logging(args.verbose)
    raise SystemExit(main(args))
