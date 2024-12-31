import os

def check_env():
    required_vars = ['DISCORD_TOKEN', 'PREFIX', 'MONGO_URI']
    for var in required_vars:
        if os.getenv(var) is None:
            raise Exception(f"{var} not found, please check your .env file")
