# Refactor v2 – Template Builder Integration

## Objective

Introduce a configuration-driven template extraction system
with a Gradio-based Template Builder UI.

## Major Changes

1. Replaced hardcoded vendor extraction logic.
2. Introduced TemplateRegistry.
3. Introduced TemplateExtractor engine.
4. Added TemplateValidator.
5. Created /templates folder.
6. Added UI module for template creation.
7. Integrated builder into app.py.

## Architectural Impact

Extraction is now configuration-driven.
New vendors require NO code changes.
System becomes extensible and platform-ready.

## Backward Compatibility

Existing reconciliation architecture untouched.
Legacy vendor extractors can coexist temporarily.