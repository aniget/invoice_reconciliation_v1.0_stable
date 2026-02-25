# Template-Driven Extraction Refactor

## Objective

Replace generic hardcoded extractor with fully template-driven system.

## Changes Made

1. Removed logic from generic_extractor.py
2. Introduced generic.json template
3. Updated TemplateExtractor to support multi-capture groups
4. Modified pdf_processor.py to use registry lookup
5. Implemented fallback to Generic template

## Result

All PDF extraction is now configuration-driven.

New vendors require:
- Create JSON template
- No Python code changes

## Architecture Impact

Extraction now belongs entirely to Adapter Layer.
Reconciliation layer untouched.

## Backward Compatibility

Vendor-specific extractors may remain temporarily,
but system no longer depends on them.