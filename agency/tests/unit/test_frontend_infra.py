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


# ---------------------------------------------------------------------------
# frontend-feature-views-real-data — structure gates (REQ-FEAT-02 / FEAT-N1/N2)
# ---------------------------------------------------------------------------


def _feature_views_and_dashboard():
    """Los 6 archivos objetivo del gate: las 5 vistas de features + page.js.

    NOTA: Sidebar.jsx NO está en esta lista (navegación). Desde el fix de
    producción, su prop `tenantId` es requerida y ya no existe default
    `tenant-demo-001`; el grep de anclas demo cubre todo src/.
    """
    base = os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src")
    return [
        os.path.join(base, "features", "Ideation", "views", "IdeaApprovalView.jsx"),
        os.path.join(base, "features", "Scriptwriting", "views", "ScriptInspectorView.jsx"),
        os.path.join(base, "features", "RAGBrain", "views", "BrainManagementView.jsx"),
        os.path.join(base, "features", "VideoPreview", "views", "PublishApprovalView.jsx"),
        os.path.join(base, "features", "Metrics72h", "views", "MetricsDashboardView.jsx"),
        os.path.join(base, "app", "page.js"),
    ]


def test_frontend_views_use_tenant_resource_hook():
    """REQ-FEAT-4: las 5 vistas + dashboard consumen el hook compartido."""
    for path in _feature_views_and_dashboard():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "useTenantResource" in content, f"{path} no usa useTenantResource"


def test_frontend_use_tenant_resource_hook_exists():
    """T9: el hook compartido existe y envuelve fetchWithTenant con abort guard."""
    hook_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "frontend", "src", "hooks", "useTenantResource.js"
    )
    assert os.path.exists(hook_path), "missing hooks/useTenantResource.js"
    with open(hook_path, encoding="utf-8") as f:
        content = f.read()
    assert "fetchWithTenant" in content
    assert "AbortController" in content


def test_frontend_no_mock_literals():
    """FEAT-N1: zero 'mock' matches in the 5 views + dashboard."""
    for path in _feature_views_and_dashboard():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "mock" not in content.lower(), f"mock literal still present in {path}"


def test_frontend_no_demo_anchor_literals():
    """FEAT-N2: zero demo anchors (idea-101, 1,240, 3 Errores, edited_output,
    tenant-demo-001, s3://) in the 5 views + dashboard."""
    anchors = ("idea-101", "1,240", "3 errores", "edited_output.mp4", "tenant-demo-001", "s3://")
    for path in _feature_views_and_dashboard():
        with open(path, encoding="utf-8") as f:
            content = f.read().lower()
        for anchor in anchors:
            assert anchor not in content, f"{anchor!r} still present in {path}"


def test_frontend_views_issue_exact_fetch_paths():
    """REQ-FEAT-1/FEAT-V3: each view/dashboard wires the guarded resource."""
    expectations = {
        "IdeaApprovalView.jsx": "useTenantResource(\"ideas\", tenantId)",
        "ScriptInspectorView.jsx": "useTenantResource(\"scripts\", tenantId)",
        "BrainManagementView.jsx": "useTenantResource(\"brain\", tenantId)",
        "PublishApprovalView.jsx": "useTenantResource(\"scripts\", tenantId)",
        "MetricsDashboardView.jsx": "useTenantResource(\"metrics\", tenantId)",
        # page.js pasa el tenant a través de scopedTenantId; debe referenciar los 3 recursos
        "page.js": 'useTenantResource("ideas", scopedTenantId)',
    }
    for path in _feature_views_and_dashboard():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        fname = os.path.basename(path)
        assert expectations[fname] in content, (
            f"{fname} no reference the guarded endpoint via the shared hook"
        )


def test_frontend_metrics_flat_shape_no_legacy_deref():
    """REQ-FEAT-4 FEAT-D2: flat views_72h/ratio_relativo without the legacy
    nested metrics_72h deref (crash-proof on the DDL-002 shape)."""
    # Sólo la vista de métricas y el dashboard consumen /metrics; las otras
    # vistas no deben contener ningún rastro del contrato anidado legacy.
    for path in _feature_views_and_dashboard():
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "metrics_72h" not in content, f"legacy metrics_72h deref still in {path}"

    metrics_consumers = [
        os.path.join(os.path.dirname(__file__), "..", "..", "frontend", "src", "app", "page.js"),
        os.path.join(
            os.path.dirname(__file__), "..", "..", "frontend", "src",
            "features", "Metrics72h", "components", "MetricClassificationCard.jsx",
        ),
    ]
    for path in metrics_consumers:
        with open(path, encoding="utf-8") as f:
            content = f.read()
        assert "views_72h" in content, f"flat views_72h missing in {path}"
        assert "ratio_relativo" in content, f"flat ratio_relativo missing in {path}"
