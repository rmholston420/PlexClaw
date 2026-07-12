# Release checklist

## Frontend cache-busting note

- `run.sh` now stamps the served frontend with a content-hash cache-busting query string for `sdk-bridge-client.js` automatically at launch time.
- `frontend/index.html` keeps a stable placeholder token in source so working-tree diffs stay clean.
