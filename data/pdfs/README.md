# PDF data layout

- Place subject ZIPs under `data/pdfs/<subject>/`, e.g., `data/pdfs/chemistry/chemistry_plus1.zip`.
- Extract into `data/pdfs/<subject>/unzipped/<book_name>/<files>.pdf` before ingestion. Keep book folder names stable for hashing.
- Temporary downloads and unzip work files live in `data/pdfs/tmp` (auto-created).
- Hash/etag checks will skip unchanged PDFs; keep filenames stable to avoid churn.
- Chunking is by page window (default 6 pages, 1-page overlap). Content is trimmed near a soft ceiling at sentence boundaries (default ~12k chars) to keep prompts clean. Question count per chunk is treated as a hint, not a hard requirement.
