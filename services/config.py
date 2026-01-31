from sqlmodel import Session

from core.models import SignupConfig


def get_signup_config(session: Session) -> SignupConfig:
  config = session.get(SignupConfig, ident=1)
  if not config:
    config = SignupConfig(id=1)
    session.add(config)
    session.commit()
    session.refresh(config)

  return config

def update_signup_config(session: Session, updated_config: SignupConfig) -> SignupConfig:
  db_config = get_signup_config(session)

  # Ensure singleton never violated
  update_data = updated_config.model_dump(exclude_unset=True, exclude={"id"})

  db_config.sqlmodel_update(update_data)

  session.add(db_config)
  session.commit()
  session.refresh(db_config)
  return db_config
