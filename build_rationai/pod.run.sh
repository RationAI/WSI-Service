#!/usr/bin/env bash

# arguments are passed externally: like --host 0.0.0.0 --port 8080 --loop=uvloop --http=httptools
exec /usr/bin/tini -- python3 -m uvicorn wsi_service.app:app $@