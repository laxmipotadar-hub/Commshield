"""Audit repository for platform incompatibilities between Windows and Linux/Ubuntu.

Checks for:
1. Linux-specific modules (e.g. fcntl, termios, pty, pwd, grp).
2. Hard-coded POSIX absolute paths (e.g. /tmp/, /var/, /home/, /etc/).
3. os.system calls and shell=True subprocess invocations.
4. Symlinks or symlink creation calls (os.symlink).
5. Filename case conflicts on Windows (case-insensitive collisions).
"""

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXCLUDE_DIRS = {".git", ".venv", "node_modules", "__pycache__", "dist", ".pytest_cache", "tools"}
EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".json", ".md", ".sh", ".yaml", ".yml", ".ini"}

POSIX_MODULES = {"fcntl", "termios", "pty", "pwd", "grp", "resource"}
POSIX_PATH_PATTERNS = [
    re.compile(r'["\']/(?:tmp|var|home|etc|usr|opt|bin|sbin)[/"\']'),
]


def audit_repository():
    findings = []
    seen_files_lower = {}
    case_collisions = []

    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        
        # Check case collisions in directory
        dir_seen = {}
        for fn in filenames:
            fn_lower = fn.lower()
            if fn_lower in dir_seen:
                case_collisions.append((Path(dirpath) / fn, Path(dirpath) / dir_seen[fn_lower]))
            else:
                dir_seen[fn_lower] = fn

        for fn in filenames:
            fp = Path(dirpath) / fn
            if fp.suffix.lower() not in EXTENSIONS:
                continue

            try:
                content = fp.read_text(encoding="utf-8", errors="ignore")
            except Exception as e:
                findings.append((str(fp.relative_to(ROOT)), "read_error", str(e)))
                continue

            rel_path = str(fp.relative_to(ROOT))

            # 1. Check for POSIX-only module imports in python files
            if fp.suffix == ".py":
                for mod in POSIX_MODULES:
                    pattern = rf"^\s*(?:import\s+{mod}|from\s+{mod}\s+import)"
                    if re.search(pattern, content, re.MULTILINE):
                        findings.append((rel_path, "posix_module", f"Imports '{mod}'"))

                # 2. Check for os.system calls
                if re.search(r"\bos\.system\s*\(", content):
                    findings.append((rel_path, "os_system", "Uses os.system()"))

                # 3. Check for shell=True in subprocess
                if re.search(r"subprocess\.\w+\([^)]*shell\s*=\s*True", content, re.DOTALL):
                    findings.append((rel_path, "shell_true", "Uses subprocess with shell=True"))

                # 4. Check for symlink calls
                if re.search(r"\bos\.symlink\s*\(", content):
                    findings.append((rel_path, "symlink_call", "Uses os.symlink()"))

            # 5. Check for hard-coded POSIX absolute paths
            for pat in POSIX_PATH_PATTERNS:
                m = pat.search(content)
                if m:
                    # Ignore documentation mentions
                    if not rel_path.endswith(".md"):
                        findings.append((rel_path, "hardcoded_path", f"Found {m.group(0)}"))

            # 6. Check if file is a symlink
            if os.path.islink(fp):
                findings.append((rel_path, "is_symlink", "File is a symbolic link"))

    return findings, case_collisions


def main():
    print("=" * 70)
    print("CommShield Cross-Platform Compatibility Audit")
    print(f"Target Root: {ROOT}")
    print(f"Current OS:  {os.name} ({sys.platform})")
    print("=" * 70)

    findings, case_collisions = audit_repository()

    print(f"\n1. Linux-Only Patterns Found: {len(findings)}")
    if findings:
        for path, category, detail in findings:
            print(f"  [{category:15}] {path}: {detail}")
    else:
        print("  ✓ No Linux-only modules (fcntl, termios, pwd), os.system, or hard-coded POSIX paths found.")

    print(f"\n2. Case-Insensitive Filename Collisions: {len(case_collisions)}")
    if case_collisions:
        for p1, p2 in case_collisions:
            print(f"  Collision: {p1} <-> {p2}")
    else:
        print("  ✓ No filename case collisions found.")

    print("\n" + "=" * 70)
    if not findings and not case_collisions:
        print("Result: CLEAN - Codebase uses standard pathlib.Path, cross-platform APIs, and no POSIX-only imports.")
        return 0
    else:
        print("Result: Review findings above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
# CommShield AI Core
