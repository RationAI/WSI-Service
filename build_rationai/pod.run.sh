#!/usr/bin/env bash

if [ -f ".env" ] ; then
    echo ".env file found: setting env variables..."
    source .env
else
    echo "There is no .env available!"
fi

# arguments are passed externally: like --host 0.0.0.0 --port 8080 --loop=uvloop --http=httptools
exec /usr/bin/tini -- python3 -m uvicorn wsi_service.app:app $@