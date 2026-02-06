from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

from services.signup_service import get_and_hydrate_signup, get_react_data, RosterMember

# TODO: Make this configurable in the UI
MAX_NUM_GROUPS = 3

# Initialize FastAPI
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")


@app.get("/")
async def hello_world(request: Request):
  # This sends 'request' and a 'message' variable to hello.html
  return templates.TemplateResponse(
    "hello.html",
    {"request": request, "message": "The Team Builder is under construction!"},
  )


@app.get("/roster")
async def view_roster(request: Request):
  bot = request.app.state.bot

  # Get the config from DB
  signup = await get_and_hydrate_signup(bot)

  # TODO: Error catch this
  if not signup:
    raise NotImplementedError()

  react_data = await get_react_data(signup.guild, signup.post)

  # TEMP, no filtering
  members = set().union(*react_data.values())

  gvg_roles = []
  for role in signup.roles:
    if role:
      gvg_roles.append({"id": role.id, "name": role.name, "color": str(role.color)})

  roster = []
  for member in members:
    roster.append(
      {
        "id": member.id,
        "display_name": member.display_name,
        "avatar_url":member.display_avatar.url,
        "role_ids":[r.id for r in member.roles if r in signup.roles],
      }
    )

  return templates.TemplateResponse(
    "roster.html",
    {
      "request": request,
      "roster": roster,
      "guild_name": signup.guild.name,
      "all_gvg_roles": gvg_roles,
      "max_num_groups": MAX_NUM_GROUPS,
    },
  )
