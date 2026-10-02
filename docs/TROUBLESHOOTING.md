# Troubleshooting

## "Ollama is not reachable" / `OllamaUnavailableError`

- Confirm Ollama is running: `ollama list` (starts the background service on
  most installs) or check for the Ollama tray/menu-bar icon.
- Confirm `OLLAMA_BASE_URL` in your `.env` matches where it's listening
  (default `http://localhost:11434`).
- Run `python scripts/check_ollama.py` for a direct diagnostic.

## "Model 'qwen3:1.7b' is not available" / `OllamaModelNotFoundError`

Pull it: `ollama pull qwen3:1.7b`. This app never pulls models automatically
(for you or for embeddings) - see `docs/OLLAMA.md`.

## Every generation call is slow (~20-30s)

Expected if `OLLAMA_KEEP_ALIVE=0`: Ollama unloads the model after every
request, so each call pays a reload cost. The default is `300` (keep it loaded
for 5 minutes after the last call); raise it, or use `-1` to keep it loaded
indefinitely. Only the first query after a pause should be slow.

## Qdrant path / permission issues

`QDRANT_PATH` (default `./data/indexes/qdrant`) must be a directory the
process can create and write to. Only one process can hold an embedded
Qdrant client open on a given path at a time - if you see a lock error,
make sure no other `uvicorn`/script process is already using that path.

## Windows / `py` launcher notes

This project targets Python 3.11 specifically (safer wheel availability for
torch/sentence-transformers/qdrant-client than newer interpreters). If your
default `python` is a different version, create the venv explicitly:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\pip install -e ".[dev]"
```

If `mypy` fails with `ImportError: DLL load failed ... Application Control
policy has blocked this file`, your organization's Windows Defender
Application Control (or similar) policy is blocking mypy's compiled
(mypyc) extension. Reinstall from source to get a pure-Python build:
`pip install --no-binary mypy --force-reinstall mypy`.

## Optional: Docker Compose

Not required - Qdrant runs in embedded local-persistent mode
(`QdrantClient(path=...)`), no server process needed. If you'd rather run a
standalone Qdrant server (e.g. to share an index across machines), a minimal
compose file would look like:

```yaml
services:
  qdrant:
    image: qdrant/qdrant:latest
    ports: ["6333:6333"]
    volumes: ["./data/indexes/qdrant:/qdrant/storage"]
```

Switching to it requires changing `storage/qdrant_store.py` to construct
`QdrantClient(url=...)` instead of `QdrantClient(path=...)` - not wired up by
default since it adds a Docker dependency this project otherwise avoids.
