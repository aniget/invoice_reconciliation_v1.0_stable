import re
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class TemplateExtractor:
    def __init__(self, template: dict):
        self.template = template

    # ------------------------------------------------------------------
    # Pre-processors — applied once to the full text before extraction
    # ------------------------------------------------------------------

    def _pre_process_text(self, text: str) -> str:
        """Apply any pre_process directives defined at the template level."""
        processor = self.template.get("pre_process")
        if not processor:
            return text
        for name in (processor if isinstance(processor, list) else [processor]):
            text = self._apply_pre_processor(name, text)
        return text

    def _apply_pre_processor(self, name: str, text: str) -> str:
        if name == "strip_underscores":
            # pdfplumber weaves underscores between every character on
            # separator lines, e.g. 'С_то_й_но_ст_'. Strip them all and
            # collapse the resulting runs of spaces.
            text = text.replace("_", "")
            text = re.sub(r" +", " ", text)
        else:
            logger.warning("Unknown pre_processor '%s' — skipped", name)
        return text

    # ------------------------------------------------------------------
    # Main extraction
    # ------------------------------------------------------------------

    def extract(self, pdf_text: str) -> dict:
        text = self._pre_process_text(pdf_text)

        result = {
            "vendor": self.template.get("vendor"),
            "vendor_normalized": self.template.get(
                "vendor_normalized", self.template.get("vendor")
            ),
            "currency": self.template.get("default_currency", "EUR"),
            "confidence": 0,
            "extraction_method": "template_driven",
        }

        fields_found = 0

        for field, config in self.template["fields"].items():
            if config["type"] == "regex":
                patterns = config.get("patterns", [config.get("pattern")])
                value = self._match_first(patterns, text)
                result[field] = self._post_process(
                    value, config.get("post_process"))
                if result[field] is not None:
                    fields_found += 1
            elif config["type"] == "literal":
                result[field] = config.get("value")
                fields_found += 1
            else:
                result[field] = None

        total_fields = len(self.template["fields"])
        if total_fields > 0:
            result["confidence"] = int((fields_found / total_fields) * 100)

        return result

    def _match_first(self, patterns: list, text: str):
        """Return the last capture group of the first matching pattern, or None."""
        for pattern in patterns:
            if not pattern:
                continue
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.groups()[-1].strip()
        return None

    # ------------------------------------------------------------------
    # Post-processors
    # ------------------------------------------------------------------

    def _post_process(self, value: str | None, processor_type: str | None):
        if not processor_type:
            return value

        if value is None:
            return None

        if processor_type == "to_decimal_eu":
            # 1.829,36  ->  1829.36
            try:
                return float(value.replace(".", "").replace(",", "."))
            except ValueError:
                logger.warning("Could not parse decimal (EU) from %r", value)
                return None

        if processor_type == "to_decimal_bg":
            # 1 829.36  ->  1829.36
            try:
                return float(value.replace(" ", "").replace(",", "."))
            except ValueError:
                logger.warning("Could not parse decimal (BG) from %r", value)
                return None
        if processor_type == "to_decimal_us":
            # Format: 5,816.92 -> 5816.92  (comma thousands, dot decimal)
            try:
                return float(value.replace(",", ""))
            except ValueError:
                logger.warning("Could not parse decimal (US) from %r", value)
                return None

        if processor_type == "strip_spaces":
            # Normalise IBANs that extract with internal spaces: "DE04 3003..." -> "DE04300..."
            return value.replace(" ", "")

        if processor_type == "to_date":
            formats = [
                "%d.%m.%Y",   # 29.01.2026
                "%d/%m/%Y",   # 29/01/2026
                "%Y-%m-%d",   # 2026-01-29
                "%d-%m-%Y",   # 02-03-2026  (NEP style)
                "%d-%b-%Y",   # 01-Mar-2026
                "%d-%b-%y",   # 01-Mar-26   ← the new case
                "%d %b %Y",   # 01 Mar 2026
                "%d %B %Y",   # 01 March 2026
            ]

            for fmt in formats:
                try:
                    return datetime.strptime(value, fmt).strftime("%Y-%m-%d")
                except ValueError:
                    continue
            logger.warning("Could not parse date from %r", value)
            return value
        logger.warning(
            "Unknown post_processor '%s' — returning raw value", processor_type)
        return value
