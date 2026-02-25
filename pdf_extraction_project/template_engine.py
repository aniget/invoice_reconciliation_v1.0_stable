import re
from decimal import Decimal


class TemplateExtractor:

    def __init__(self, template: dict):
        self.template = template

    def extract(self, pdf_text: str) -> dict:
        result = {}

        for field, config in self.template["fields"].items():
            if config["type"] == "regex":

                match = re.search(config["pattern"], pdf_text)

                if match:
                    # Always take last capturing group
                    value = match.groups()[-1]

                    if config.get("post_process") == "to_decimal":
                        value = Decimal(value.replace(
                            ",", ".").replace(" ", ""))

                    result[field] = value
                else:
                    result[field] = None

        return result
