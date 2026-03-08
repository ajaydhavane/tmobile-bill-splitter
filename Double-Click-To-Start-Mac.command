#!/bin/bash

cd "$(dirname "$0")"

if ! command -v uv &> /dev/null
then
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source "$HOME/.local/bin/env"
fi

echo "Do not close this window until you are done using the app."

uv run streamlit run src/main.py > /dev/null

echo "Process finished. You can close this window."
read -p "Press enter to exit..."
