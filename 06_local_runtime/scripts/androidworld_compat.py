"""Narrow compatibility hooks for the pinned local AndroidWorld runtime."""

from __future__ import annotations

import dataclasses
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import tempfile
import time


def apply() -> None:
    """Apply compatibility hooks without modifying the checked-out source."""
    import requests
    from android_env.wrappers import a11y_grpc_wrapper
    from android_world.env import adb_utils
    from android_world.env.setup_device import apps
    from android_world.task_evals.utils import sqlite_utils
    from android_world.utils import file_utils

    if not getattr(apps.download_app_data, "_raven_m_compat", False):
        app_cache = (
            Path(__file__).resolve().parent.parent
            / "cache"
            / "android_world"
            / "app_data"
        )
        legacy_cache = Path(tempfile.gettempdir()) / "android_world" / "app_data"

        def download_app_data_resumable(file_name: str) -> str:
            app_cache.mkdir(parents=True, exist_ok=True)
            target = app_cache / file_name
            if target.is_file() and target.stat().st_size > 0:
                return target.as_posix()
            legacy = legacy_cache / file_name
            if legacy.is_file() and legacy.stat().st_size > 0:
                shutil.copy2(legacy, target)
                return target.as_posix()

            partial = target.with_suffix(target.suffix + ".partial")
            url = (
                "https://storage.googleapis.com/gresearch/android_world/"
                + file_name
            )
            result = subprocess.run(
                [
                    "curl.exe",
                    "--ssl-no-revoke",
                    "--location",
                    "--fail",
                    "--retry",
                    "10",
                    "--retry-all-errors",
                    "--continue-at",
                    "-",
                    "--output",
                    str(partial),
                    url,
                ],
                check=False,
            )
            if result.returncode != 0 or not partial.is_file():
                raise RuntimeError(f"Failed to download AndroidWorld asset: {url}")
            os.replace(partial, target)
            return target.as_posix()

        download_app_data_resumable._raven_m_compat = True
        apps.download_app_data = download_app_data_resumable

    if not getattr(
        a11y_grpc_wrapper._get_accessibility_forwarder_apk,
        "_raven_m_compat",
        False,
    ):
        url = (
            "https://storage.googleapis.com/android_env-tasks/"
            "2024.05.13-accessibility_forwarder.apk"
        )
        cache = (
            Path(__file__).resolve().parent.parent
            / "cache"
            / "android_env"
            / "2024.05.13-accessibility_forwarder.apk"
        )
        expected_bytes = 4_490_495

        def get_cached_accessibility_forwarder_apk() -> bytes:
            cache.parent.mkdir(parents=True, exist_ok=True)
            if cache.is_file() and cache.stat().st_size == expected_bytes:
                return cache.read_bytes()
            last_error = None
            for attempt in range(5):
                try:
                    response = requests.get(url, timeout=120)
                    response.raise_for_status()
                    if len(response.content) != expected_bytes:
                        raise IOError(
                            "Incomplete accessibility APK: "
                            f"{len(response.content)} of {expected_bytes} bytes"
                        )
                    partial = cache.with_suffix(".apk.partial")
                    partial.write_bytes(response.content)
                    os.replace(partial, cache)
                    return response.content
                except (OSError, requests.RequestException) as exc:
                    last_error = exc
                    if attempt < 4:
                        time.sleep(2**attempt)
            raise RuntimeError(
                "Could not download the AndroidEnv accessibility APK after "
                "five attempts."
            ) from last_error

        get_cached_accessibility_forwarder_apk._raven_m_compat = True
        a11y_grpc_wrapper._get_accessibility_forwarder_apk = (
            get_cached_accessibility_forwarder_apk
        )

    if getattr(sqlite_utils.insert_rows_to_remote_db, "_raven_m_compat", False):
        return

    original = sqlite_utils.insert_rows_to_remote_db

    def insert_rows_compatible(
        rows,
        exclude_key,
        table_name,
        remote_db_file_path,
        app_name,
        env,
        timeout_sec=None,
    ):
        if app_name != "joplin":
            return original(
                rows,
                exclude_key,
                table_name,
                remote_db_file_path,
                app_name,
                env,
                timeout_sec,
            )

        with env.controller.pull_file(
            remote_db_file_path, timeout_sec
        ) as local_db_directory:
            local_db_path = file_utils.convert_to_posix_path(
                local_db_directory, os.path.split(remote_db_file_path)[1]
            )
            conn = sqlite3.connect(local_db_path)
            try:
                cursor = conn.cursor()
                columns = {
                    row[1]
                    for row in cursor.execute(
                        f"PRAGMA table_info({table_name})"
                    ).fetchall()
                }
                for row in rows:
                    fields = [
                        field
                        for field in dataclasses.fields(row)
                        if field.name in columns and field.name != exclude_key
                    ]
                    names = ", ".join(f'"{field.name}"' for field in fields)
                    placeholders = ", ".join("?" for _ in fields)
                    values = tuple(getattr(row, field.name) for field in fields)
                    cursor.execute(
                        f"INSERT INTO {table_name} ({names}) VALUES ({placeholders})",
                        values,
                    )
                conn.commit()
            finally:
                conn.close()

            env.controller.push_file(
                local_db_path, remote_db_file_path, timeout_sec
            )
            adb_utils.close_app(app_name, env.controller)

    insert_rows_compatible._raven_m_compat = True
    sqlite_utils.insert_rows_to_remote_db = insert_rows_compatible


apply()
