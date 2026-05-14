# Ingestion Pipeline

> Phase 2+ — rich media ingestion not yet implemented.

## Supported Input Types

| Input | Method |
|-------|--------|
| Manual page | Editor |
| File | Drag/drop or upload |
| URL | Paste URL |
| YouTube | Paste URL |
| Chat export | Upload JSON/Markdown |
| CSV | Upload |

## Pipeline Stages

1. Capture (upload / URL fetch / paste)
2. Normalize (detect type, extract metadata)
3. Store original (content-addressed filesystem)
4. Extract text / transcript
5. Generate thumbnails / previews
6. Chunk for retrieval
7. Generate embeddings (Phase 3)
8. Extract entities / claims / tasks (Phase 5)
9. Create graph links (Phase 4)
10. Mark as processed

## Job Types

- `file_import`
- `url_import`
- `youtube_import`
- `pdf_import`
- `image_import`
- `video_import`
- `csv_import`
- `chat_import`
