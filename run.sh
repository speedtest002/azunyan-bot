#!/bin/bash
source .env

git clone https://$GH_ACCESS_TOKEN@github.com/$GH_USERNAME/$GH_REPO.git temp_dir
mv temp_dir/* temp_dir/.* .
rm -rf temp_dir
rm -rf .git

pip install -r requirements.txt
python bot.py
