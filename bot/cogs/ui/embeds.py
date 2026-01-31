import discord


async def forward_as_embed(
  source_msg: discord.Message,
  footer_content: str,
) -> discord.Embed:
  embed = discord.Embed(
    description=source_msg.content,
    color=discord.Color.blue(),
    timestamp=source_msg.created_at,
  )
  embed.set_author(
    name=source_msg.author.display_name, icon_url=source_msg.author.display_avatar.url
  )
  embed.set_footer(text=footer_content)

  # Handle images/attachments if they exist
  if source_msg.attachments:
    embed.set_image(url=source_msg.attachments[0].url)

  return embed
