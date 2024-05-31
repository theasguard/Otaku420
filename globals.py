
import xbmc
import xbmcaddon
from resources.lib.common import tools
from resources.lib.third_party import pytz

class g:
    """Container for global variables."""
    
    ADDON = xbmcaddon.Addon()
    ADDON_ID = ADDON.getAddonInfo('id')
    ADDON_NAME = ADDON.getAddonInfo('name')
    ADDON_USERDATA_PATH = tools.translate_path(f"special://profile/addon_data/{ADDON_ID}")

    CONTENT_MENU = 'menu'
    CONTENT_SHOW = 'tvshows'
    CONTENT_MOVIE = 'movies'
    CONTENT_EPISODE = 'episodes'
    CONTENT_SEASON = 'seasons'

    #... any other content types for navigation as needed

    def get_language_code():
        """Gets current language code from Kodi settings"""
        lang = xbmc.getLanguage(xbmc.ISO_639_1)
        if lang is None:
            logger.warning("Could not determine language, defaulting to en")
            lang = "en"
        return lang
 
    def log(msg, level='info'):
        """Logs messages with the addon name as prefix."""
        if level == 'error':
            xbmc.log(f"{g.ADDON_NAME}: ERROR - {msg}", xbmc.LOGERROR)
        elif level == 'warning':
            xbmc.log(f"{g.ADDON_NAME}: WARNING - {msg}", xbmc.LOGWARNING)
        elif level == 'notice':
            xbmc.log(f"{g.ADDON_NAME}: NOTICE - {msg}", xbmc.LOGNOTICE)
        elif level == 'debug':
            xbmc.log(f"{g.ADDON_NAME}: DEBUG - {msg}", xbmc.LOGDEBUG)
        else:
            xbmc.log(f"{g.ADDON_NAME}: INFO - {msg}", xbmc.LOGINFO)

    def color_string(text, color='deepskyblue'):
        """Wraps text in Kodi color tags."""
        return f"[COLOR {color}]{text}[/COLOR]"

    def notification(heading, message, time=5000, icon=ADDON.getAddonInfo('icon'), sound=True):
        """Displays a Kodi notification to the user."""
        xbmcgui.Dialog().notification(heading, message, icon, time, sound)

    def get_setting(setting_id):
        """Gets addon setting value."""
        return g.ADDON.getSetting(setting_id)

    def get_int_setting(setting_id, default_value=0):
        """Gets addon setting as integer."""
        return int(g.ADDON.getSettingInt(setting_id)) if g.ADDON.getSettingInt(setting_id) else default_value

    def get_bool_setting(setting_id, default_value=False):
        """Gets addon setting as boolean."""
        return g.ADDON.getSettingBool(setting_id) if g.ADDON.getSettingBool(setting_id) else default_value

    def set_setting(setting_id, value):
        """Sets addon setting value."""
        return g.ADDON.setSetting(setting_id, str(value))

    def open_addon_settings(self):
        """Opens the addon settings dialog."""
        xbmc.executebuiltin(f"Addon.OpenSettings({g.ADDON_ID})")

    @staticmethod
    def create_url(base_url, params):
        """Constructs a Seren URL with provided params."""
        if params is None:
            return base_url
        if 'action_args' in params and isinstance(params['action_args'], dict):
            params['action_args'] = json.dumps(params['action_args'], sort_keys=True)
        return f"{base_url}/?{parse.urlencode(params)}"
  
    UTC_TIMEZONE = pytz.utc

    def local_to_utc(datetime_string):
        """Converts a local datetime string to UTC."""
        if not datetime_string:
            return None

        try:
            local_dt = tools.parse_datetime(datetime_string)
            localized_dt = g.LOCAL_TIMEZONE.localize(local_dt)
            utc_dt = localized_dt.astimezone(g.UTC_TIMEZONE)
            return utc_dt.isoformat()
        except (ValueError, TypeError):
            g.log(f"Failed to convert local datetime to UTC: {datetime_string}")
            return None
        
    LOCAL_TIMEZONE = pytz.timezone(g.get_setting("general.localtimezone"))

    #... Other required constants and variables for UI as needed
