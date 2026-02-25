"""
Flow:
Upload PDF
Extract raw text
User selects line
Choose field name
Auto-generate regex
Build template JSON
Save template
"""

import gradio as gr
import pdfplumber
import re
from pathlib import Path
from pdf_extraction_project.template_registry import TemplateRegistry
from pdf_extraction_project.template_validator import TemplateValidator

TEMPLATE_DIR = Path("pdf_extraction_project/templates")
registry = TemplateRegistry(TEMPLATE_DIR)
validator = TemplateValidator()

current_template = {
    "vendor": "",
    "fields": {}
}


def extract_text(file):
    text = ""
    with pdfplumber.open(file.name) as pdf:
        for page in pdf.pages:
            text += page.extract_text() + "\n"
    return text


def add_field(vendor, selected_line, field_name):
    global current_template
    current_template["vendor"] = vendor

    pattern = re.escape(selected_line)
    pattern = pattern.replace("\\ ", "\\s*")
    pattern = f"{pattern}[:\\s]+(.+)"

    current_template["fields"][field_name] = {
        "type": "regex",
        "pattern": pattern
    }

    return current_template


def save_template():
    validator.validate(current_template)
    registry.save(current_template)
    return "Template saved successfully!"


def build_ui():

    with gr.Blocks() as demo:  # TODO: explain why 'demo'
        gr.Markdown("## Template Builder")

        pdf_file = gr.File(label="Upload Sample Invoice PDF")
        pdf_text = gr.Textbox(label="Extracted PDF Text", lines=15)

        pdf_file.upload(extract_text, pdf_file, pdf_text)

        vendor = gr.Textbox(label="Vendor Name")
        selected_line = gr.Textbox(label="Copy Line From Above")
        field_name = gr.Dropdown(
            ["invoice_number", "invoice_date", "total_amount", "vat_amount"]
        )

        add_btn = gr.Button("Add Field")
        template_output = gr.JSON()

        add_btn.click(add_field,
                      [vendor, selected_line, field_name],
                      template_output)

        save_btn = gr.Button("Save Template")
        save_msg = gr.Textbox()

        save_btn.click(save_template, None, save_msg)

    return demo
