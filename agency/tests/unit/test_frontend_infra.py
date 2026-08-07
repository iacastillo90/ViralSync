"""
test_frontend_infra.py

Pruebas unitarias para validar la existencia e integridad del middleware y componentes de infraestructura.
"""

import json
import os


def test_frontend_infra_files_exist():
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    
    middleware_file = os.path.join(base_dir, "middleware.js")
    tenant_store = os.path.join(base_dir, "stores", "useTenantStore.js")
    api_config = os.path.join(base_dir, "services", "apiConfig.js")
    header_file = os.path.join(base_dir, "components", "layout", "Header.jsx")
    sidebar_file = os.path.join(base_dir, "components", "layout", "Sidebar.jsx")
    
    assert os.path.exists(middleware_file)
    assert os.path.exists(tenant_store)
    assert os.path.exists(api_config)
    assert os.path.exists(header_file)
    assert os.path.exists(sidebar_file)


def test_frontend_boundary_files_exist():
    """Spec scenario 'Structure check': src/app must contain the 4 boundary files."""
    app_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "app")

    for fname in ("error.js", "loading.js", "not-found.js", "global-error.js"):
        assert os.path.exists(os.path.join(app_dir, fname)), f"missing boundary file {fname}"


def test_package_json_pins():
    """frontend-resilience requirement: next 15.5.23, react/react-dom 19, postcss 8.5.26; lint + lucide-react unchanged."""
    pkg_path = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "package.json")

    with open(pkg_path, encoding="utf-8") as f:
        pkg = json.load(f)

    assert pkg["dependencies"]["next"] == "^15.5.23"
    assert pkg["dependencies"]["react"] == "^19.1.0"
    assert pkg["dependencies"]["react-dom"] == "^19.1.0"
    assert pkg["devDependencies"]["postcss"] == "^8.5.26"
    # keep-as-is contract: lint script and lucide-react must not drift
    assert pkg["scripts"]["lint"] == "next lint"
    assert pkg["dependencies"]["lucide-react"] == "^0.424.0"
    # stores import zustand; it must be a declared (pinned) dependency for `npm ci && npm run build` to pass
    assert pkg["dependencies"]["zustand"].startswith("^")
    # npm audit must exit 0: next@15.5.23 exact-pins internal postcss 8.4.31 and sharp ^0.34.3
    # (both vulnerable); overrides lift them so the spec "npm audit (0 vulns)" gate holds
    assert pkg["overrides"]["postcss"] == "^8.5.26"
    assert pkg["overrides"]["sharp"] == "^0.35.0"


def test_jsconfig_alias_resolves():
    """Documented deviation contract: @/* alias must map to ./src/* so next build resolves imports."""
    base_dir = os.path.join(os.path.dirname(__file__), "..", "..", "frontend")
    jsconfig_path = os.path.join(base_dir, "jsconfig.json")

    assert os.path.exists(jsconfig_path), "missing jsconfig.json"

    with open(jsconfig_path, encoding="utf-8") as f:
        cfg = json.load(f)

    assert cfg["compilerOptions"]["baseUrl"] == "."
    assert cfg["compilerOptions"]["paths"]["@/*"] == ["./src/*"]
