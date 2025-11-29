try:
    from ballsdex.settings import settings
except ModuleNotFoundError:
    from settings.models import settings

settings = settings
