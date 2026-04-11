import hikari

def get_avatar_embed(target: hikari.User) -> hikari.Embed:
    avatar_url = target.display_avatar_url.url
    return hikari.Embed(title=f"Avatar của {target.username}", color=0x7289DA).set_image(avatar_url)