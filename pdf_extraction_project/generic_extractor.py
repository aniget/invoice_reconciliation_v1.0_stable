from pathlib import Path
from pdf_extraction_project.template_registry import TemplateRegistry
from pdf_extraction_project.template_engine import TemplateExtractor

TEMPLATE_DIR = Path("pdf_extraction_project/templates")

registry = TemplateRegistry(TEMPLATE_DIR)
registry.load()


def extract_generic(pdf_text: str):

    template = registry.get("Generic")

    if not template:
        raise ValueError("Generic template missing")

    extractor = TemplateExtractor(template)
    return extractor.extract(pdf_text)
