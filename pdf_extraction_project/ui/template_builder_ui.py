import gradio as gr
import pdfplumber
import re
from pathlib import Path
from pdf_extraction_project.template_registry import TemplateRegistry
from pdf_extraction_project.template_engine import TemplateExtractor

TEMPLATE_DIR = Path("pdf_extraction_project/templates")
registry = TemplateRegistry(TEMPLATE_DIR)

# ---------------------------------------------------------------------------
# Field metadata — centralised so UI and logic stay in sync
# ---------------------------------------------------------------------------

FIELD_DEFINITIONS = {
    "invoice_number":    {"post_process": None,            "label": "Invoice Number"},
    "invoice_date":      {"post_process": "to_date",       "label": "Invoice Date"},
    "due_date":          {"post_process": "to_date",       "label": "Due Date"},
    "net_amount_eur":    {"post_process": "to_decimal_eu", "label": "Net Amount (€)"},
    "vat_amount_eur":    {"post_process": "to_decimal_eu", "label": "VAT Amount (€)"},
    "total_amount_eur":  {"post_process": "to_decimal_eu", "label": "Total Amount (€)"},
    "payment_method":    {"post_process": None,            "label": "Payment Method"},
    "supplier_iban":     {"post_process": None,            "label": "Supplier IBAN"},
    "supplier_vat_number": {"post_process": None,          "label": "Supplier VAT Number"},
}

PRE_PROCESSORS = ["(none)", "strip_underscores"]

POST_PROCESS_OPTIONS = [
    "(use default)",   # reads default from FIELD_DEFINITIONS
    "to_decimal_eu",   # 1.234,56  → 1234.56
    "to_decimal_us",   # 1,234.56  → 1234.56  (Equinix, NEP)
    "to_date",
    "strip_spaces",    # removes internal spaces from IBANs
    "(none)",          # no post-processing
]

# ---------------------------------------------------------------------------
# PDF helpers
# ---------------------------------------------------------------------------


def extract_text(file) -> str:
    if file is None:
        return ""
    try:
        text = ""
        with pdfplumber.open(file.name) as pdf:
            for page in pdf.pages:
                text += (page.extract_text(x_tolerance=1.0) or "") + "\n"
        return text.strip()
    except Exception as exc:
        return f"❌ Error reading PDF: {exc}"


def _apply_pre_process(text: str, pre_process: str) -> str:
    """Mirror of TemplateExtractor._apply_pre_processor for live preview."""
    if pre_process == "strip_underscores":
        text = text.replace("_", "")
        text = re.sub(r" +", " ", text)
    return text

# ---------------------------------------------------------------------------
# Pattern builder — smarter than the original one-size-fits-all approach
# ---------------------------------------------------------------------------


def _build_pattern(label: str, field_name: str) -> str:
    """
    Build a context-aware regex from the label line the user highlighted. Strategy is:
    - Escape the label so literal dots, brackets, etc. are safe.
    - Append a capture group whose shape matches the expected value type:
        * date fields   → ISO / European date pattern
        * amount fields → EU decimal number (1.234,56 or 1234,56)
        * IBAN          → IBAN pattern
        * fallback      → greedy non-newline capture
    """
    escaped = re.escape(label.strip())

    if "date" in field_name:
        value_pattern = r"(\d{2}[.\-\/]\d{2}[.\-\/]\d{4})"
    elif "amount" in field_name:
        value_pattern = r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})"
    elif "iban" in field_name:
        value_pattern = r"([A-Z]{2}[0-9A-Z]{13,30})"
    elif "vat_number" in field_name:
        value_pattern = r"([A-Z]{2}[\d]{6,12})"
    elif "invoice_number" in field_name:
        value_pattern = r"([A-Z0-9\-\/]{4,20})"
    else:
        value_pattern = r"([^\n]+)"

    return rf"{escaped}[\s:]*{value_pattern}"


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _init_state(vendor: str) -> dict:
    return {
        "vendor": vendor,
        "vendor_normalized": vendor,
        "detection_patterns": [vendor] if vendor else [],
        "default_currency": "EUR",
        "fields": {},
    }


def _state_is_empty(state: dict) -> bool:
    return not state or not state.get("fields")

# ---------------------------------------------------------------------------
# UI callbacks
# ---------------------------------------------------------------------------


def on_vendor_change(vendor: str, state: dict) -> dict:
    """Keep vendor fields in state in sync as the user types."""
    if not state:
        state = _init_state(vendor)
    state["vendor"] = vendor
    state["vendor_normalized"] = vendor
    state["detection_patterns"] = [vendor] if vendor else []
    return state


def add_field(vendor: str, selected_line: str, field_name: str,
              custom_pattern: str, post_process_override: str,
              literal_value: str, pre_process: str, state: dict):
    """
    Add or update a field in the template state.
    - If literal_value is set  → writes {"type": "literal", "value": ...}
    - Otherwise               → builds a regex field, using custom_pattern
                                 or auto-generating one from selected_line.
    """
    if not vendor:
        return state, state, "⚠️ Please enter a vendor name first."
    if not field_name:
        return state, state, "⚠️ Please select a field type."

    if not state or "fields" not in state:
        state = _init_state(vendor)

    state["vendor"] = vendor
    state["vendor_normalized"] = vendor
    state["detection_patterns"] = [vendor]

    # Persist pre_process at template level
    if pre_process and pre_process != "(none)":
        state["pre_process"] = pre_process
    elif "pre_process" in state and pre_process == "(none)":
        del state["pre_process"]

    # ── Literal field (e.g. vat = 0.0 for reverse-charge) ──────────────
    if literal_value and literal_value.strip():
        try:
            parsed_literal = float(literal_value.strip())
        except ValueError:
            parsed_literal = literal_value.strip()

        state["fields"][field_name] = {
            "type": "literal",
            "value": parsed_literal,
        }
        msg = f"✅ Field **{field_name}** set as literal `{parsed_literal}`. {len(state['fields'])} field(s) configured."
        return state, state, msg

    # ── Regex field ──────────────────────────────────────────────────────
    if not selected_line and not custom_pattern:
        return state, state, "⚠️ Paste a label from the PDF text or enter a custom pattern."

    if custom_pattern.strip():
        patterns = [custom_pattern.strip()]
    else:
        patterns = [_build_pattern(selected_line, field_name)]

    if post_process_override == "(use default)":
        post_process = FIELD_DEFINITIONS.get(
            field_name, {}).get("post_process")
    elif post_process_override == "(none)":
        post_process = None
    else:
        post_process = post_process_override

    state["fields"][field_name] = {
        "type": "regex",
        "patterns": patterns,
        **({"post_process": post_process} if post_process else {}),
    }

    msg = f"✅ Field **{field_name}** added. {len(state['fields'])} field(s) configured."
    return state, state, msg


def remove_field(field_name: str, state: dict):
    """Remove a single field from the template."""
    if not state or field_name not in state.get("fields", {}):
        return state, state, f"⚠️ Field '{field_name}' not found."
    del state["fields"][field_name]
    msg = f"🗑️ Field **{field_name}** removed."
    return state, state, msg


def test_extraction(pdf_text: str, pre_process: str, state: dict) -> str:
    if _state_is_empty(state):
        return "⚠️ Add at least one field before testing."
    if not pdf_text.strip():
        return "⚠️ No PDF text loaded."

    # Apply live pre-processing so the test mirrors real extraction
    working_text = _apply_pre_process(
        pdf_text, pre_process if pre_process != "(none)" else "")

    extractor = TemplateExtractor(state)
    results = extractor.extract(working_text)

    lines = ["🔍 Extraction results:", "─" * 36]
    for field, value in results.items():
        if field in ("vendor", "vendor_normalized", "currency",
                     "confidence", "extraction_method"):
            continue
        icon = "✅" if value is not None else "❌"
        lines.append(f"{icon}  {field}: {value}")

    lines.append("─" * 36)
    lines.append(f"📊 Confidence: {results.get('confidence', 0)}%")
    return "\n".join(lines)


def preview_processed_text(pdf_text: str, pre_process: str) -> str:
    """Show what the text looks like after pre-processing — useful for debugging."""
    if not pdf_text.strip():
        return ""
    return _apply_pre_process(pdf_text, pre_process if pre_process != "(none)" else "")


def save_template(state: dict, tenant_id: str):
    if not state or not state.get("vendor"):
        return "❌ Missing vendor name.", state
    if _state_is_empty(state):
        return "❌ Add at least one field before saving.", state

    registry.save(state, tenant_id)
    vendor = state["vendor"]
    field_count = len(state["fields"])
    return (
        f"✅ Template for **{vendor}** saved successfully "
        f"({field_count} fields) under tenant `{tenant_id}`.",
        _init_state(""),
    )


def load_template(vendor: str, tenant_id: str):
    """Load an existing template back into the builder for editing."""
    try:
        template = registry.load(vendor, tenant_id)
        if not template:
            return {}, {}, f"⚠️ No template found for '{vendor}' / '{tenant_id}'."
        return template, template, f"✅ Loaded template for **{vendor}**."
    except Exception as exc:
        return {}, {}, f"❌ Error loading template: {exc}"


def clear_template(vendor: str):
    fresh = _init_state(vendor)
    return fresh, fresh, "🔄 Template cleared."


# ---------------------------------------------------------------------------
# UI layout
# ---------------------------------------------------------------------------

def build_ui():
    with gr.Blocks(title="Invoice Template Builder") as demo:

        gr.Markdown(
            "## 🧾 Invoice Template Builder\n"
            "Load a PDF, highlight label text, assign field types and save the extraction template."
        )

        template_state = gr.State(_init_state(""))
        status_msg = gr.Markdown(value="")

        # ── Row 1: PDF loader + processed text preview ──────────────────────
        with gr.Row():
            with gr.Column(scale=1):
                pdf_file = gr.File(
                    label="1. Upload sample PDF", file_types=[".pdf"])
                pre_process_selector = gr.Dropdown(
                    label="Pre-processor (apply before matching)",
                    choices=PRE_PROCESSORS,
                    value="(none)",
                    info="Use 'strip_underscores' for A1 Bulgaria invoices."
                )
                pdf_text_raw = gr.Textbox(
                    label="Raw extracted text",
                    lines=14,
                    interactive=False,
                    show_copy_button=True,
                )
                pdf_text_processed = gr.Textbox(
                    label="Text after pre-processing (used for matching)",
                    lines=6,
                    interactive=False,
                    visible=False,
                )
                pdf_file.upload(extract_text, pdf_file, pdf_text_raw)

            # ── Column 2: Template configuration ────────────────────────────
            with gr.Column(scale=1):
                gr.Markdown("### 2. Configure template")

                with gr.Group():
                    tenant_selector = gr.Dropdown(
                        label="Tenant",
                        choices=["default_tenant", "company_a", "company_b"],
                        value="default_tenant",
                    )
                    vendor_name = gr.Textbox(
                        label="Vendor name",
                        placeholder="e.g. NEP Media Solutions",
                    )

                gr.Markdown("#### Add / update a field")
                with gr.Group():
                    selected_text = gr.Textbox(
                        label="Paste label from PDF text",
                        placeholder="e.g.  Total €",
                        info="Copy the label that appears just before the value you want to capture.",
                    )
                    field_type = gr.Dropdown(
                        label="Field type",
                        choices=list(FIELD_DEFINITIONS.keys()),
                    )
                    custom_pattern = gr.Textbox(
                        label="Custom regex (optional — overrides auto-generated pattern)",
                        placeholder=r"e.g.  Total\s+€\s+([\d.,]+)",
                        info="Leave blank to auto-build from the label above.",
                    )
                    post_process_override = gr.Dropdown(
                        label="Post-process override (optional)",
                        choices=POST_PROCESS_OPTIONS,
                        value="(use default)",
                        info="Overrides the default for this field type. Use 'to_decimal_us' for invoices with 1,234.56 format.",
                    )
                    literal_value = gr.Textbox(
                        label="Literal value (optional — skips regex entirely)",
                        placeholder="e.g. 0.0",
                        info="Set a fixed value for this field. Useful for VAT = 0 on reverse-charge invoices.",
                    )
                    with gr.Row():
                        add_btn = gr.Button("➕ Add field", variant="secondary")
                        remove_btn = gr.Button(
                            "🗑️ Remove field", variant="secondary")

                gr.Markdown("#### Actions")
                with gr.Row():
                    test_btn = gr.Button(
                        "🧪 Test extraction", variant="secondary")
                    clear_btn = gr.Button(
                        "🔄 Clear template", variant="secondary")
                with gr.Row():
                    load_btn = gr.Button(
                        "📂 Load existing", variant="secondary")
                    save_btn = gr.Button("💾 Save template", variant="primary")

        # ── Row 2: Results ───────────────────────────────────────────────────
        with gr.Row():
            template_preview = gr.JSON(label="Current template JSON")
            test_results = gr.Textbox(
                label="Extraction test results", lines=12)

        # ── Vendor sync ──────────────────────────────────────────────────────
        vendor_name.change(
            on_vendor_change,
            inputs=[vendor_name, template_state],
            outputs=[template_state],
        )

        # Show/hide processed text when pre-processor changes
        def toggle_processed_preview(pdf_text, pre_process):
            if pre_process == "(none)" or not pdf_text.strip():
                return gr.update(visible=False, value="")
            processed = _apply_pre_process(pdf_text, pre_process)
            return gr.update(visible=True, value=processed)

        pre_process_selector.change(
            toggle_processed_preview,
            inputs=[pdf_text_raw, pre_process_selector],
            outputs=[pdf_text_processed],
        )
        pdf_text_raw.change(
            toggle_processed_preview,
            inputs=[pdf_text_raw, pre_process_selector],
            outputs=[pdf_text_processed],
        )

        # ── Button wiring ────────────────────────────────────────────────────
        add_btn.click(
            add_field,
            inputs=[vendor_name, selected_text, field_type,
                    custom_pattern, post_process_override, literal_value,
                    pre_process_selector, template_state],
            outputs=[template_state, template_preview, status_msg],
        )

        remove_btn.click(
            remove_field,
            inputs=[field_type, template_state],
            outputs=[template_state, template_preview, status_msg],
        )

        test_btn.click(
            test_extraction,
            inputs=[pdf_text_raw, pre_process_selector, template_state],
            outputs=[test_results],
        )

        clear_btn.click(
            clear_template,
            inputs=[vendor_name],
            outputs=[template_state, template_preview, status_msg],
        )

        load_btn.click(
            load_template,
            inputs=[vendor_name, tenant_selector],
            outputs=[template_state, template_preview, status_msg],
        )

        save_btn.click(
            save_template,
            inputs=[template_state, tenant_selector],
            outputs=[status_msg, template_preview],
        )

    return demo


if __name__ == "__main__":
    demo = build_ui()
    demo.launch()
