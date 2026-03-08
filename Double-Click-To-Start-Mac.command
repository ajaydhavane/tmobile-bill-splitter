#!/bin/bash

cd "$(dirname "$0")"

if ! command -v uv &> /dev/null
then
    echo "Installing dependencies..."
    curl -LsSf https://astral.sh/uv/install.sh | sh > /dev/null 2>&1
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ""
echo -e "\033[0;31mDo not close this window until you are done using the app!!!\033[0m"
echo ""

uv run streamlit run src/main.py > /dev/null

read -p "Press enter to exit..."
