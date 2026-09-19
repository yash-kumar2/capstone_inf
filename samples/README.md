# Sample invoice pack

This directory holds a lightweight representative set of invoice inputs for local validation and demos.

## Included sample classes

- EN: English invoices
- ES: Spanish invoices
- DE: German invoices
- FR: French invoices
- DOCX: Word-based invoice layouts
- PNG: image-based invoice captures
- Duplicate: repeated file for dedupe testing
- Unsupported: a file type intentionally rejected by the monitor
- Corrupt: an unreadable or malformed file showing the error path

## Expected behavior

- Duplicate inputs should be skipped without creating a second audit record.
- Unsupported file types should log a file event and stop.
- Corrupt input should be marked error and leave a trace in the audit log.
- Valid invoice files should flow through OCR, translation, parsing, and validation.

## Files included

The pack includes representative placeholders for invoice processing, with realistic naming and file type intent.
