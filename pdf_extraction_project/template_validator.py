class TemplateValidator:

    REQUIRED_FIELDS = [
        "invoice_number",
        "invoice_date",
        "total_amount"
    ]

    def validate(self, template: dict):
        if "vendor" not in template:
            raise ValueError("Missing vendor name")

        if "fields" not in template:
            raise ValueError("Missing fields section")

        for field in self.REQUIRED_FIELDS:
            if field not in template["fields"]:
                raise ValueError(f"Missing required field: {field}")
