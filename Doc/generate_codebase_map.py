#!/usr/bin/env python3
"""
generate_codebase_map.py

Script automatizado de documentación del código fuente completo de ViralSync.
Escanea de manera exhaustiva todos los paquetes, microservicios, entidades ORM,
routers API, agentes CrewAI, workers Celery y componentes Frontend.

Genera el archivo de arquitectura `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`
INCLUYENDO EL CÓDIGO FUENTE COMPLETO de cada archivo y la salida real de pytest.
"""

import os
import re
import ast
import subprocess
from pathlib import Path
from typing import List, Dict, Any

REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_MD_PATH = REPO_ROOT / "Doc" / "FULL_PROJECT_ARCHITECTURE_MAP.md"

IGNORE_DIRS = {
    "node_modules",
    ".git",
    "venv",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".next",
    "dist",
    "build",
    ".coverage",
    ".idea",
    ".vscode",
    ".gemini",
    ".atl",
}

IGNORE_EXTENSIONS = {
    ".pyc",
    ".pyo",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".ico",
    ".svg",
    ".zip",
    ".tar",
    ".gz",
    ".db",
    ".sqlite",
    ".log",
    ".lock",
}

# No embeber el propio mapa generado de 500k+ líneas para evitar bucles infintos
IGNORE_FILES = {
    "FULL_PROJECT_ARCHITECTURE_MAP.md",
}


def get_language_for_codeblock(ext: str, filename: str) -> str:
    """Devuelve el identificador de lenguaje para el bloque de código markdown."""
    ext_lower = ext.lower()
    if ext_lower == ".py":
        return "python"
    elif ext_lower in [".js", ".jsx"]:
        return "javascript"
    elif ext_lower in [".ts", ".tsx"]:
        return "typescript"
    elif ext_lower in [".yaml", ".yml"]:
        return "yaml"
    elif ext_lower == ".json":
        return "json"
    elif ext_lower == ".md":
        return "markdown"
    elif ext_lower == ".sh":
        return "bash"
    elif filename.lower() == "dockerfile":
        return "dockerfile"
    return "text"


def parse_python_symbols(content: str, file_path: Path) -> Dict[str, Any]:
    """Extrae clases, funciones, docstring e imports de un archivo Python usando AST."""
    classes = []
    functions = []
    docstring = ""

    try:
        tree = ast.parse(content, filename=str(file_path))
        docstring = ast.get_docstring(tree) or ""

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                functions.append(node.name)
    except Exception:
        pass

    return {
        "docstring": docstring.strip().split("\n")[0] if docstring else "",
        "classes": list(dict.fromkeys(classes)),
        "functions": list(dict.fromkeys(functions)),
    }


def parse_js_symbols(content: str) -> Dict[str, Any]:
    """Extrae exports y componentes principales de un archivo Javascript / JSX."""
    components = []
    try:
        matches = re.findall(r"export\s+(?:default\s+)?(?:function|const)\s+([A-Za-z0-9_]+)", content)
        components = list(dict.fromkeys(matches))
    except Exception:
        pass
    return {"components": components}


def run_pytest_and_get_output() -> str:
    """Ejecuta la suite de pruebas unitarias y captura la salida formateada completa."""
    try:
        venv_pytest = REPO_ROOT / "venv" / "bin" / "pytest"
        cmd = [str(venv_pytest), "agency/tests/unit/", "-v"] if venv_pytest.exists() else ["pytest", "agency/tests/unit/", "-v"]
        res = subprocess.run(cmd, cwd=REPO_ROOT, capture_output=True, text=True, timeout=60)
        return res.stdout if res.stdout else res.stderr
    except Exception as exc:
        return f"Error ejecutando pytest: {exc}"


def scan_codebase() -> List[Dict[str, Any]]:
    """Recorre recursivamente el proyecto y recopila metadatos y contenido completo."""
    file_records = []

    for root, dirs, files in os.walk(REPO_ROOT):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in sorted(files):
            if file in IGNORE_FILES:
                continue

            file_path = Path(root) / file
            rel_path = file_path.relative_to(REPO_ROOT)

            if file_path.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            content = ""
            line_count = 0
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                line_count = len(content.splitlines())
            except Exception:
                pass

            symbols = {}
            if file_path.suffix == ".py":
                symbols = parse_python_symbols(content, file_path)
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                symbols = parse_js_symbols(content)

            file_records.append({
                "rel_path": str(rel_path),
                "filename": file,
                "extension": file_path.suffix,
                "lines": line_count,
                "content": content,
                "symbols": symbols,
            })

    return file_records


def generate_markdown(records: List[Dict[str, Any]], pytest_output: str) -> str:
    """Genera el contenido estructurado en formato Markdown incluyendo el código fuente completo."""
    total_files = len(records)
    total_lines = sum(r["lines"] for r in records)

    md = []
    md.append("# 🗺️ Mapa Completo de Arquitectura y Código Fuente Real — ViralSync\n")
    md.append("> **Documentación Exhaustiva con Código Fuente Fuente 100% Completo y Salida de Pytest para Auditoría.**")
    md.append(f"> **Métricas del Proyecto:** {total_files} Archivos | {total_lines:,} Líneas de Código Totales\n")
    md.append("---\n")

    md.append("## 🧪 Salida Real de Ejecución de Pytest (Pruebas Unitarias)\n")
    md.append("```text")
    md.append(pytest_output.strip())
    md.append("```\n")
    md.append("---\n")

    md.append("## 📁 Estructura General del Proyecto\n")
    md.append("```text")
    md.append("ViralSync/")
    md.append("├── agency/")
    md.append("│   ├── agents/          # Agentes CrewAI, MCP Servers y Grafo StateGraph")
    md.append("│   ├── backend/         # API REST FastAPI, DB Models, Routers, Auth y SSE")
    md.append("│   ├── microservices/   # Microservicios Independientes (Renderer & Publisher)")
    md.append("│   ├── workers/         # Tareas Asíncronas y Worker de Celery")
    md.append("│   ├── frontend/        # Dashboard Web Next.js 15 + React 19")
    md.append("│   └── tests/           # Suite de Pruebas Unitarias y E2E (pytest)")
    md.append("└── Doc/                 # Documentación Enterprise, Schemas y Roadmaps")
    md.append("```\n")
    md.append("---\n")

    # Agrupar archivos por categoría
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        parts = Path(r["rel_path"]).parts
        category = parts[0] if len(parts) > 1 else "Raíz"
        if len(parts) > 2 and category == "agency":
            category = f"agency/{parts[1]}"
        
        groups.setdefault(category, []).append(r)

    md.append("## 📦 Código Fuente Completo por Paquete\n")

    for cat_name in sorted(groups.keys()):
        cat_files = groups[cat_name]
        cat_lines = sum(f["lines"] for f in cat_files)
        md.append(f"### 📂 `{cat_name}/` ({len(cat_files)} archivos, {cat_lines:,} líneas)\n")

        for f in cat_files:
            file_link = f"[{f['filename']}](file://{REPO_ROOT / f['rel_path']})"
            md.append(f"#### 📄 {file_link}")
            md.append(f"- **Ruta Completa:** `{f['rel_path']}`")
            md.append(f"- **Líneas de Código:** {f['lines']}")

            symbols = f.get("symbols", {})
            if symbols.get("docstring"):
                md.append(f"- **Descripción:** _{symbols['docstring']}_")

            if symbols.get("classes"):
                md.append(f"- **Clases / Entidades:** `{', '.join(symbols['classes'])}`")

            if symbols.get("functions"):
                funcs = symbols["functions"]
                displayed_funcs = funcs[:10]
                more_suffix = f" ... (+{len(funcs) - 10} más)" if len(funcs) > 10 else ""
                md.append(f"- **Funciones Principales:** `{', '.join(displayed_funcs)}{more_suffix}`")

            # Embeber Código Fuente Completo
            lang = get_language_for_codeblock(f["extension"], f["filename"])
            md.append(f"\n```{lang}")
            md.append(f["content"].rstrip())
            md.append("```\n")
            md.append("---\n")

    return "\n".join(md)


def main():
    print(f"Escaneando el código fuente de ViralSync en '{REPO_ROOT}'...")
    records = scan_codebase()

    print("Ejecutando suite de pruebas unitarias pytest para incluir la salida real...")
    pytest_output = run_pytest_and_get_output()

    print("Generando archivo Markdown completo con código fuente embebido...")
    markdown_content = generate_markdown(records, pytest_output)

    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_PATH.write_text(markdown_content, encoding="utf-8")

    print(f"✅ Mapa de código fuente completo generado con éxito en '{OUTPUT_MD_PATH}'!")
    print(f"📊 Resumen: {len(records)} archivos analizados e integrados.")


if __name__ == "__main__":
    main()
