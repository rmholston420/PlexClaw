# Release checklist

## Frontend cache-busting note

- When `frontend/sdk-bridge-client.js` changes, update the cache-busting query string in `frontend/plexclaw-ui-canonical.html` (`sdk-bridge-client.js?v=...`) before release.
- Preferred long-term fix: replace manual `?v=` versioning with a content-hash build step so the URL changes automatically when file content changes.
