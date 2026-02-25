# Architecture v2 – Template-Driven Extraction

## Before

Vendor-specific hardcoded extraction logic.

## After

Template Registry
Template Engine
Template Validator
UI Builder

## Layer Positioning

Templates → Adapter Layer
Extractor → Adapter Layer
Reconciliation → Domain Layer (unchanged)

## Benefits

- No code changes for new vendors
- UI-driven configuration
- Enterprise extensibility