#!/bin/bash
set -euo pipefail

apt-get update
apt-get install -y curl

curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.2/install.sh | bash

source "$HOME/.nvm/nvm.sh"

nvm install 22
npm -v


npm install -g @google/gemini-cli@latest


# Enable experimental skills feature
mkdir -p ~/.gemini
cat > ~/.gemini/settings.json << 'EOF'
{
  "experimental": {
    "skills": true
  }
}
EOF