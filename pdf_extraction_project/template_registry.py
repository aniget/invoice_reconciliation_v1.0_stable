import json
from pathlib import Path


class TemplateRegistry:
    def __init__(self, template_dir: Path):
        self.template_dir = template_dir
        self.templates = {}

    def load(self):
        for file in self.template_dir.glob("*.json"):
            with open(file, "r", encoding="utf-8") as f:
                template = json.load(f)
                self.templates[template["vendor"]] = template

    def get(self, vendor: str):
        return self.templates.get(vendor)

    def save(self, template: dict):
        filename = f"{template['vendor'].lower().replace(' ', '_')}.json"
        path = self.template_dir / filename
        with open(path, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4)
