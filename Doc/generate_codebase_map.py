#!/usr/bin/env python3
"""
generate_codebase_map.py

Script automatizado de documentación del código fuente de ViralSync.
Escanea de manera exhaustiva todos los paquetes, microservicios, entidades ORM,
routers API, agentes CrewAI, workers Celery y componentes Frontend.

Genera el archivo de arquitectura `Doc/FULL_PROJECT_ARCHITECTURE_MAP.md`
para ser consumido por desarrolladores y agentes de IA.
"""

import os
import re
import ast
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


def parse_python_symbols(file_path: Path) -> Dict[str, Any]:
    """Extrae clases, funciones, docstring e imports de un archivo Python usando AST."""
    classes = []
    functions = []
    docstring = ""

    try:
        content = file_path.read_text(encoding="utf-8")
        tree = ast.parse(content, filename=str(file_path))
        docstring = ast.get_docstring(tree) or ""

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                # Solo añadir funciones de nivel superior
                functions.append(node.name)
    except Exception:
        pass

    return {
        "docstring": docstring.strip().split("\n")[0] if docstring else "",
        "classes": list(dict.fromkeys(classes)),
        "functions": list(dict.fromkeys(functions)),
    }


def parse_js_symbols(file_path: Path) -> Dict[str, Any]:
    """Extrae exports y componentes principales de un archivo Javascript / JSX."""
    components = []
    try:
        content = file_path.read_text(encoding="utf-8")
        # Buscar funciones exportadas o componentes React
        matches = re.findall(r"export\s+(?:default\s+)?(?:function|const)\s+([A-Za-z0-9_]+)", content)
        components = list(dict.fromkeys(matches))
    except Exception:
        pass
    return {"components": components}


def scan_codebase() -> List[Dict[str, Any]]:
    """Recorre recursivamente el proyecto y recopila los metadatos de los archivos."""
    file_records = []

    for root, dirs, files in os.walk(REPO_ROOT):
        # Excluir directorios ignorados
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]

        for file in sorted(files):
            file_path = Path(root) / file
            rel_path = file_path.relative_to(REPO_ROOT)

            if file_path.suffix.lower() in IGNORE_EXTENSIONS:
                continue

            # Contar líneas
            line_count = 0
            try:
                with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                    line_count = sum(1 for _ in f)
            except Exception:
                pass

            symbols = {}
            if file_path.suffix == ".py":
                symbols = parse_python_symbols(file_path)
            elif file_path.suffix in [".js", ".jsx", ".ts", ".tsx"]:
                symbols = parse_js_symbols(file_path)

            file_records.append({
                "rel_path": str(rel_path),
                "filename": file,
                "extension": file_path.suffix,
                "lines": line_count,
                "symbols": symbols,
            })

    return file_records


def generate_markdown(records: List[Dict[str, Any]]) -> str:
    """Genera el contenido estructurado en formato Markdown."""
    total_files = len(records)
    total_lines = sum(r["lines"] for r in records)

    md = []
    md.append("# 🗺️ Mapa Completo de Arquitectura y Código Fuente — ViralSync\n")
    md.append("> **Documentación Generada Automáticamente para Agentes de IA y Desarrolladores.**")
    md.append(f"> **Métricas del Proyecto:** {total_files} Archivos | {total_lines:,} Líneas de Código Totales\n")
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

    # Agrupar archivos por directorio superior
    groups: Dict[str, List[Dict[str, Any]]] = {}
    for r in records:
        parts = Path(r["rel_path"]).parts
        category = parts[0] if len(parts) > 1 else "Raíz"
        if len(parts) > 2 and category == "agency":
            category = f"agency/{parts[1]}"
        
        groups.setdefault(category, []).append(r)

    md.append("## 📦 Módulos, Entidades y Código por Paquete\n")

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
                # Mostrar hasta 10 funciones principales
                funcs = symbols["functions"]
                displayed_funcs = funcs[:10]
                more_suffix = f" ... (+{len(funcs) - 10} más)" if len(funcs) > 10 else ""
                md.append(f"- **Funciones Principales:** `{', '.join(displayed_funcs)}{more_suffix}`")

            if symbols.get("components"):
                md.append(f"- **Componentes Exportados:** `{', '.join(symbols['components'])}`")

            md.append("")

    return "\n".join(md)


def main():
    print(f"Escaneando el código fuente de ViralSync en '{REPO_ROOT}'...")
    records = scan_codebase()
    markdown_content = generate_markdown(records)

    OUTPUT_MD_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_MD_PATH.write_text(markdown_content, encoding="utf-8")

    print(f"✅ Mapa de código fuente generado con éxito en '{OUTPUT_MD_PATH}'!")
    print(f"📊 Resumen: {len(records)} archivos analizados.")


if __name__ == "__main__":
    main()
