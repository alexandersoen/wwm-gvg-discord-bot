from __future__ import annotations

from sqlmodel import Column, SQLModel, Field, JSON, CheckConstraint

from core.database_utils import PydanticJSON


class ChannelConfig(SQLModel):
  channel_id: int
  guild_id: int | None = None


class MessageConfig(SQLModel):
  message_id: int
  channel_config: ChannelConfig

  content: str


class SignupConfig(SQLModel, table=True):
  # Singleton, only one global config
  id: int = Field(
    default=1, primary_key=True, sa_column_args=[CheckConstraint("id = 1")]
  )

  management_channel: ChannelConfig | None = Field(
    default=None, sa_column=Column(PydanticJSON(ChannelConfig))
  )
  selected_post: MessageConfig | None = Field(
    default=None, sa_column=Column(PydanticJSON(MessageConfig))
  )
  gvg_roles: list[int] = Field(
    default_factory=list, sa_column=Column(JSON, nullable=False)
  )
  gvg_reacts: list[str] = Field(
    default_factory=list, sa_column=Column(JSON, nullable=False)
  )

