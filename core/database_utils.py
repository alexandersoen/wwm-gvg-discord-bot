import json
from typing import Type, TypeVar, Generic, Any, Optional
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy.engine.interfaces import Dialect
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class PydanticJSON(TypeDecorator, Generic[T]):
  """
  Handles the transition between a JSON string in the DB and
  a Pydantic model in Python.
  """

  impl = TEXT
  cache_ok = True

  def __init__(self, pydantic_model: Type[T]):
    super().__init__()
    self.pydantic_model = pydantic_model

  def process_bind_param(self, value: Any, dialect: Dialect) -> Optional[str]:
    """Convert Pydantic object to JSON string for storage."""
    _ = dialect

    if value is None:
      return None
    if isinstance(value, dict):
      return json.dumps(value)
    # Ensure we are using Pydantic's serialization
    if isinstance(value, BaseModel):
      return value.model_dump_json()
    return json.dumps(value)

  def process_result_value(self, value: Optional[str], dialect: Dialect) -> Optional[T]:
    """Convert JSON string from DB back into a Pydantic object."""
    _ = dialect

    if value is None:
      return None

    try:
      data = json.loads(value)
      # This is the magic line that fixes your AttributeError
      return self.pydantic_model.model_validate(data)
    except (json.JSONDecodeError, ValueError):
      return None
