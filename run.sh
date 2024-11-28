#!/bin/bash
source .env
#find . -mindepth 1 ! -name ".env" ! -name "run.sh" -exec rm -rf {} +
# Pull code from GitHub
git clone https://$GH_ACCESS_TOKEN@github.com/$GH_USERNAME/$GH_REPO.git temp_dir
mv temp_dir/* temp_dir/.* .  # Di chuyển cả file ẩn
rm -rf temp_dir
rm -rf .git

pip install -r requirements.txt
python bot.py
