"""Apply the AndroidEnv 1.2.3 Python 3.11 Windows tempfile fix."""

from __future__ import annotations

from pathlib import Path

import android_env


target = Path(android_env.__file__).parent / "components" / "adb_call_parser.py"
text = target.read_text(encoding="utf-8")

original = """        if sys.version_info >= (3, 12):
          kwargs = {'suffix': '.apk', 'delete_on_close': False}
        else:
          kwargs = {'suffix': '.apk'}

        with tempfile.NamedTemporaryFile(**kwargs) as f:
          fpath = f.name
          f.write(install_apk.blob.contents)

          response, _ = self._execute_command(
              ['install', '-r', '-t', '-g', fpath], timeout=timeout
          )
"""

replacement = """        if os.name == 'nt' and sys.version_info < (3, 12):
          # On Windows, another process cannot open a NamedTemporaryFile while
          # it is held with delete=True. Close it before invoking adb, then
          # remove it explicitly.
          with tempfile.NamedTemporaryFile(suffix='.apk', delete=False) as f:
            fpath = f.name
            f.write(install_apk.blob.contents)
            f.flush()
          try:
            response, _ = self._execute_command(
                ['install', '-r', '-t', '-g', fpath], timeout=timeout
            )
          finally:
            os.unlink(fpath)
        elif sys.version_info >= (3, 12):
          kwargs = {'suffix': '.apk', 'delete_on_close': False}
          with tempfile.NamedTemporaryFile(**kwargs) as f:
            fpath = f.name
            f.write(install_apk.blob.contents)
            f.flush()
            response, _ = self._execute_command(
                ['install', '-r', '-t', '-g', fpath], timeout=timeout
            )
        else:
          with tempfile.NamedTemporaryFile(suffix='.apk') as f:
            fpath = f.name
            f.write(install_apk.blob.contents)
            f.flush()
            response, _ = self._execute_command(
                ['install', '-r', '-t', '-g', fpath], timeout=timeout
            )
"""

if replacement in text:
    print("AndroidEnv Windows tempfile fix: already applied")
elif original in text:
    target.write_text(text.replace(original, replacement, 1), encoding="utf-8")
    print(f"AndroidEnv Windows tempfile fix: applied to {target}")
else:
    raise RuntimeError(
        "AndroidEnv adb_call_parser.py did not match version 1.2.3; refusing "
        "to apply an unverified patch."
    )
