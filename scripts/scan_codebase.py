#!/usr/bin/env python3
"""Scan a repository and produce a current-state inventory for PRD grounding.

Dependency-free: uses only the Python 3 standard library.

The inventory is a *map*, not a conclusion. It lists languages, manifests,
entry points, routes, data models/migrations, tests, docs and TODO markers so
the agent can then do targeted reading (see references/code-scan-checklist.md).

Examples:
    python3 scan_codebase.py --root /path/to/repo
    python3 scan_codebase.py --root . --out 04-code-baseline.raw.md
    python3 scan_codebase.py --root . --focus "order,refund" --format json
"""

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone

IGNORE_DIRS = {
    ".git", ".hg", ".svn", ".idea", ".vscode", ".DS_Store",
    "node_modules", "vendor", "dist", "build", "out", "target",
    "bin", "obj", "coverage", ".next", ".nuxt", ".cache", ".turbo",
    "__pycache__", ".pytest_cache", ".mypy_cache", ".ruff_cache",
    ".venv", "venv", "env", "site-packages", "Pods", "DerivedData",
}

BINARY_EXTS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".bmp", ".ico", ".pdf",
    ".zip", ".gz", ".tar", ".tgz", ".7z", ".rar", ".jar", ".war", ".class",
    ".woff", ".woff2", ".ttf", ".otf", ".eot", ".mp3", ".mp4", ".mov",
    ".avi", ".sqlite", ".db", ".lockb", ".wasm", ".so", ".dylib", ".dll",
    ".exe", ".o", ".a", ".pyc", ".pyo",
}

EXT_TO_LANG = {
    ".py": "Python", ".pyi": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript", ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go", ".rs": "Rust", ".java": "Java", ".kt": "Kotlin", ".kts": "Kotlin",
    ".scala": "Scala", ".rb": "Ruby", ".php": "PHP", ".cs": "C#", ".swift": "Swift",
    ".c": "C", ".h": "C", ".cc": "C++", ".cpp": "C++", ".hpp": "C++",
    ".m": "Objective-C", ".mm": "Objective-C",
    ".vue": "Vue", ".svelte": "Svelte", ".html": "HTML", ".css": "CSS",
    ".scss": "SCSS", ".less": "LESS", ".sql": "SQL", ".sh": "Shell", ".bash": "Shell",
    ".dart": "Dart", ".ex": "Elixir", ".exs": "Elixir", ".erl": "Erlang",
    ".clj": "Clojure", ".hs": "Haskell", ".lua": "Lua", ".r": "R", ".R": "R",
    ".yaml": "YAML", ".yml": "YAML", ".json": "JSON", ".toml": "TOML",
    ".md": "Markdown", ".mdx": "Markdown", ".xml": "XML",
}

MANIFEST_NAMES = {
    "package.json", "pnpm-workspace.yaml", "pnpm-lock.yaml", "yarn.lock",
    "package-lock.json", "lerna.json", "nx.json", "turbo.json",
    "pyproject.toml", "setup.py", "setup.cfg", "requirements.txt", "Pipfile",
    "poetry.lock", "go.mod", "go.sum", "Cargo.toml", "Cargo.lock",
    "pom.xml", "build.gradle", "build.gradle.kts", "settings.gradle",
    "composer.json", "Gemfile", "mix.exs", "pubspec.yaml", "CMakeLists.txt",
    "Dockerfile", "docker-compose.yml", "docker-compose.yaml", "Makefile",
    "tsconfig.json", "vite.config.ts", "webpack.config.js", "next.config.js",
    "next.config.ts", "astro.config.mjs",
}

ENTRY_FILENAMES = {
    "main.py", "app.py", "manage.py", "__main__.py", "wsgi.py", "asgi.py",
    "main.go", "main.rs", "Main.java", "index.js", "index.ts", "index.jsx",
    "index.tsx", "server.js", "server.ts", "app.js", "app.ts", "cli.py",
    "main.dart", "Program.cs", "Application.java",
}

DOC_DIRS = {"docs", "doc", "documentation", "adr", "adrs", "rfcs", "wiki"}
TEST_DIRS = {"test", "tests", "__tests__", "spec", "specs", "e2e", "integration-tests"}
MODEL_DIRS = {"models", "model", "entities", "entity", "schema", "schemas", "migrations", "migration"}
ROUTE_HINT_DIRS = {"routes", "routers", "controllers", "handlers", "api", "apis", "endpoints", "views"}

SOURCE_EXTS = {ext for ext, lang in EXT_TO_LANG.items()
               if lang not in {"JSON", "YAML", "XML", "Markdown", "TOML", "HTML", "CSS", "SCSS", "LESS"}}

ROUTE_PATTERNS = [
    ("Express/Koa/NestJS", re.compile(r"""\b(?:app|router|server|api)\s*\.\s*(get|post|put|patch|delete|all)\s*\(\s*['"`]([^'"`]{1,200})['"`]""", re.I)),
    ("FastAPI/Flask", re.compile(r"""@\s*(?:app|router|bp|blueprint)\s*\.\s*(get|post|put|patch|delete|route)\s*\(\s*['"]([^'"]{1,200})['"]""", re.I)),
    ("Spring", re.compile(r"""@(RequestMapping|GetMapping|PostMapping|PutMapping|DeleteMapping|PatchMapping)\s*\(\s*(?:value\s*=\s*)?\{?\s*["']([^"']{1,200})["']""", re.I)),
    ("Go net/http", re.compile(r"""\b(?:r|router|mux|e|g)\s*\.\s*(GET|POST|PUT|PATCH|DELETE)\s*\(\s*["']([^"']{1,200})["']""")),
    ("Gin/Gorilla", re.compile(r"""\b(?:r|router|api)\s*\.\s*(HandleFunc|Handle)\s*\(\s*["']([^"']{1,200})["']""")),
    ("Rails", re.compile(r"""^\s*(get|post|put|patch|delete)\s+['"]([^'"]{1,200})['"]""", re.M)),
    ("Django", re.compile(r"""\b(path|re_path)\s*\(\s*['"]([^'"]{1,200})['"]""")),
]

TODO_RE = re.compile(r"\b(TODO|FIXME|HACK|XXX|DEPRECATED)\b", re.I)


def is_probably_text(path, max_bytes=2_000_000):
    ext = os.path.splitext(path)[1].lower()
    if ext in BINARY_EXTS:
        return False
    try:
        if os.path.getsize(path) > max_bytes:
            return False
    except OSError:
        return False
    return True


def walk_files(root, max_files):
    """Yield file paths, pruning ignored directories, up to max_files."""
    count = 0
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d not in IGNORE_DIRS and not d.startswith(".DS_Store"))
        for name in sorted(filenames):
            if name == ".DS_Store":
                continue
            yield os.path.join(dirpath, name)
            count += 1
            if count >= max_files:
                return


def rel(path, root):
    try:
        return os.path.relpath(path, root)
    except ValueError:
        return path


def read_text(path, limit=400_000):
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return handle.read(limit)
    except OSError:
        return ""


def collect(root, max_files, focus):
    files = []
    languages = Counter()
    manifests = []
    entry_points = []
    tests = []
    docs = []
    models = []
    route_hits = []
    todo_count = 0
    todo_samples = []
    focus_terms = [term.strip().lower() for term in focus.split(",") if term.strip()] if focus else []
    focus_files = []

    for path in walk_files(root, max_files):
        relpath = rel(path, root)
        files.append(relpath)
        ext = os.path.splitext(path)[1].lower()
        base = os.path.basename(path)
        if ext in EXT_TO_LANG:
            languages[EXT_TO_LANG[ext]] += 1

        lower_parts = [part.lower() for part in relpath.split(os.sep)]
        if base in MANIFEST_NAMES:
            manifests.append(relpath)
        if base in ENTRY_FILENAMES:
            entry_points.append(relpath)
        if any(part in TEST_DIRS for part in lower_parts) or re.search(r"(\.test\.|\.spec\.|_test\.|^test_)", base, re.I):
            if ext in SOURCE_EXTS:
                tests.append(relpath)
        if any(part in DOC_DIRS for part in lower_parts[:-1]) or re.match(r"(readme|changelog|contributing|architecture)", base, re.I) and ext in {".md", ".mdx", ".txt"}:
            docs.append(relpath)
        if any(part in MODEL_DIRS for part in lower_parts[:-1]) or base in {"schema.prisma", "models.py", "schema.sql"} or ext == ".sql":
            models.append(relpath)

        if focus_terms and any(term in relpath.lower() for term in focus_terms):
            focus_files.append(relpath)

        if ext in SOURCE_EXTS and is_probably_text(path):
            text = read_text(path)
            if not text:
                continue
            for match in TODO_RE.finditer(text):
                todo_count += 1
                if len(todo_samples) < 20:
                    line_no = text.count("\n", 0, match.start()) + 1
                    todo_samples.append("%s:%d %s" % (relpath, line_no, match.group(0)))
            if len(route_hits) < 200:
                lowered = text.lower()
                if any(token in lowered for token in ("route", "router", "app.", "@get", "@post", "mapping", "handlefunc", "path(")):
                    for framework, pattern in ROUTE_PATTERNS:
                        for match in pattern.finditer(text):
                            if len(route_hits) >= 200:
                                break
                            line_no = text.count("\n", 0, match.start()) + 1
                            route_hits.append({
                                "framework": framework,
                                "method": match.group(1).upper(),
                                "path": match.group(2),
                                "file": relpath,
                                "line": line_no,
                            })

    return {
        "root": os.path.abspath(root),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_files": len(files),
        "languages": dict(languages.most_common(20)),
        "manifests": manifests,
        "entry_points": sorted(set(entry_points))[:50],
        "routes": route_hits[:200],
        "models": sorted(set(models))[:200],
        "tests": sorted(set(tests))[:200],
        "test_count": len(set(tests)),
        "docs": sorted(set(docs))[:200],
        "todo_count": todo_count,
        "todo_samples": todo_samples,
        "focus_terms": focus_terms,
        "focus_files": sorted(set(focus_files))[:300],
        "top_dirs": top_dirs(files),
    }


def top_dirs(files, depth=2):
    counter = Counter()
    for relpath in files:
        parts = relpath.split(os.sep)
        key = "/".join(parts[:depth]) if len(parts) > 1 else "."
        counter[key] += 1
    return counter.most_common(40)


def render_markdown(data):
    lines = []
    push = lines.append
    push("# 代码现状盘点（scan_codebase.py）")
    push("")
    push("- 仓库根目录：`%s`" % data["root"])
    push("- 生成时间：%s" % data["generated_at"])
    push("- 扫描文件数：%d" % data["total_files"])
    if data["focus_terms"]:
        push("- 关注关键词：%s" % ", ".join(data["focus_terms"]))
    push("")

    push("## 1. 语言与规模")
    push("")
    if data["languages"]:
        push("| 语言 | 文件数 |")
        push("| --- | --- |")
        for lang, count in data["languages"].items():
            push("| %s | %d |" % (lang, count))
    else:
        push("（未识别到源码文件）")
    push("")

    push("## 2. 项目清单文件")
    push("")
    if data["manifests"]:
        for item in data["manifests"]:
            push("- `%s`" % item)
    else:
        push("（无）")
    push("")

    push("## 3. 目录结构（前两层，按文件数）")
    push("")
    if data["top_dirs"]:
        push("| 目录 | 文件数 |")
        push("| --- | --- |")
        for name, count in data["top_dirs"]:
            push("| `%s` | %d |" % (name, count))
    else:
        push("（无）")
    push("")

    push("## 4. 入口点")
    push("")
    if data["entry_points"]:
        for item in data["entry_points"]:
            push("- `%s`" % item)
    else:
        push("（未识别到常见入口文件，请查看 manifest 的 scripts/main/bin）")
    push("")

    push("## 5. 路由 / 接口（前 200 条）")
    push("")
    if data["routes"]:
        push("| 框架 | 方法 | 路径 | 位置 |")
        push("| --- | --- | --- | --- |")
        for route in data["routes"]:
            push("| %s | %s | `%s` | `%s:%d` |" % (
                route["framework"], route["method"], route["path"], route["file"], route["line"]))
    else:
        push("（未识别到路由；请按 code-scan-checklist 手工检索）")
    push("")

    push("## 6. 数据模型 / 迁移")
    push("")
    if data["models"]:
        for item in data["models"]:
            push("- `%s`" % item)
    else:
        push("（无）")
    push("")

    push("## 7. 测试")
    push("")
    push("- 测试文件数：%d" % data["test_count"])
    for item in data["tests"]:
        push("- `%s`" % item)
    push("")

    push("## 8. 文档")
    push("")
    if data["docs"]:
        for item in data["docs"]:
            push("- `%s`" % item)
    else:
        push("（无）")
    push("")

    push("## 9. TODO / FIXME / 废弃标记")
    push("")
    push("- 总数：%d" % data["todo_count"])
    for item in data["todo_samples"]:
        push("- `%s`" % item)
    push("")

    if data["focus_terms"]:
        push("## 10. 关键词命中文件")
        push("")
        if data["focus_files"]:
            for item in data["focus_files"]:
                push("- `%s`" % item)
        else:
            push("（无命中，换关键词再试）")
        push("")

    push("## 下一步")
    push("")
    push("这是地图不是结论。请按 `references/code-scan-checklist.md` 定向阅读：")
    push("功能追踪链 → 数据层 → 接口层 → 状态/任务 → 权限 → 测试，")
    push("并把结论写入 `04-code-baseline.md`（事实带 `path:line`）。")
    push("")
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="scan_codebase.py",
        description="Scan a repository and produce a current-state inventory for PRD grounding.",
        epilog="The inventory is a map, not a conclusion. Follow references/code-scan-checklist.md next.",
    )
    parser.add_argument("--root", default=".", help="Repository root to scan (default: current directory)")
    parser.add_argument("--out", default=None, help="Write output to this file instead of stdout")
    parser.add_argument("--format", choices=["md", "json"], default="md", help="Output format (default: md)")
    parser.add_argument("--focus", default=None, help="Comma-separated keywords to highlight relevant files")
    parser.add_argument("--max-files", type=int, default=5000, help="Maximum number of files to scan (default: 5000)")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.root):
        parser.error("--root is not a directory: %s" % args.root)

    data = collect(args.root, args.max_files, args.focus)
    output = json.dumps(data, ensure_ascii=False, indent=2) if args.format == "json" else render_markdown(data)

    if args.out:
        out_dir = os.path.dirname(os.path.abspath(args.out))
        if out_dir and not os.path.isdir(out_dir):
            os.makedirs(out_dir, exist_ok=True)
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(output)
            if not output.endswith("\n"):
                handle.write("\n")
        print("wrote %s (%d files scanned)" % (args.out, data["total_files"]))
    else:
        sys.stdout.write(output)
        if not output.endswith("\n"):
            sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
