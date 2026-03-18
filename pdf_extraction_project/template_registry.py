"""
pdf_extraction_project/template_registry.py

Changes from original:
  1. BUG FIX: pdf_processor.py called self.registry.list_templates() but
     the method was named get_all_templates().  Both names now exist:
     list_templates() is the canonical name; get_all_templates() is kept
     as an alias so nothing already using it breaks.

  2. Added list_template_files() which returns Path objects rather than
     stems — used by the fixed detect_vendor() in pdf_processor.py.

  3. No logic changes — storage is still filesystem JSON files.
     Phase 1 will swap the backend here while keeping the same interface.
"""

import json
from pathlib import Path


class TemplateRegistry:
    """
    Manages per-tenant vendor extraction templates stored as JSON files.

    Directory layout:
        <base_dir>/
            <tenant_id>/
                vivacom.json
                yettel.json
                generic.json
                ...

    The interface is designed so Phase 1 can replace the filesystem
    backend with a database query without changing any call sites:
        get(vendor, tenant_id)      → dict | None
        save(template, tenant_id)   → None
        list_templates(tenant_id)   → list[str]   (vendor stems)
    """

    def __init__(self, template_dir: Path):
        self.base_dir = Path(template_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)

    # ── Tenant directory helper ────────────────────────────────────────── #

    def _get_tenant_dir(self, tenant_id: str) -> Path:
        """Return (and create if needed) the directory for this tenant."""
        tenant_dir = self.base_dir / tenant_id
        tenant_dir.mkdir(parents=True, exist_ok=True)
        return tenant_dir

    # ── Public API ─────────────────────────────────────────────────────── #

    def list_templates(self, tenant_id: str = "default_tenant") -> list:
        """
        Return a list of vendor name stems for all templates in this tenant.

        Example return: ['vivacom', 'yettel', 'generic']

        This is the canonical method name.  get_all_templates() is an alias
        kept for backward compatibility.
        """
        path = self._get_tenant_dir(tenant_id)
        return [f.stem for f in sorted(path.glob("*.json"))]

    def list_template_files(self, tenant_id: str = "default_tenant") -> list:
        """
        Return a list of Path objects for all template JSON files.

        Used by detect_vendor() to iterate templates without loading them all.
        """
        path = self._get_tenant_dir(tenant_id)
        return sorted(path.glob("*.json"))

    def get(self, vendor: str, tenant_id: str = "default_tenant") -> dict | None:
        """
        Load and return the template dict for a given vendor + tenant.

        Returns None if no template file exists (never raises).
        """
        filename = f"{vendor.lower().replace(' ', '_')}.json"
        path = self._get_tenant_dir(tenant_id) / filename
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    def save(self, template: dict, tenant_id: str = "default_tenant") -> None:
        """
        Persist a template dict to disk.

        The file name is derived from template['vendor'].
        """
        vendor_name = template.get("vendor", "unknown")
        filename = f"{vendor_name.lower().replace(' ', '_')}.json"
        path = self._get_tenant_dir(tenant_id) / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)

    def delete(self, vendor: str, tenant_id: str = "default_tenant") -> bool:
        """
        Delete a template.  Returns True if deleted, False if it did not exist.
        """
        filename = f"{vendor.lower().replace(' ', '_')}.json"
        path = self._get_tenant_dir(tenant_id) / filename
        if path.exists():
            path.unlink()
            return True
        return False

    # ── Backward-compatibility alias ───────────────────────────────────── #

    def get_all_templates(self, tenant_id: str = "default_tenant") -> list:
        """Alias for list_templates().  Kept for backward compatibility."""
        return self.list_templates(tenant_id)
