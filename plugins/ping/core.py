def get_ping_message(heartbeat_latency: float) -> str:
    latency = heartbeat_latency * 1000
    return f"Ping is **{round(latency, 1)} ms**"