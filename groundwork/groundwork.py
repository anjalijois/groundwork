import logging
import logging.config
import sys
import os

from groundwork.configuration import ConfigManager
from groundwork.pluginmanager import PluginManager
from groundwork.sharedobject import SharedObjectManager
from groundwork.signals import SignalsApplication


class App:
    """
    Application object for a groundwork app.
    Loads configurations, configures logs, initialize and activates plugins and provides managers for
    shared objects and functions.

    Performed steps during start up:
      1. load configuration
      2. configure logs
      3. get valid groundwork plugins
      4. activate configured plugins
    """

    def __init__(self, config_files=[], plugins=None, strict=False):
        self.log = logging.getLogger("groundwork")
        self._configure_logging()
        self.log.info("Initializing groundwork")
        self.log.info("Reading configuration")
        self.config = ConfigManager(config_files).load()
        self._configure_logging(self.config.get("GROUNDWORK_LOGGING"))
        self.name = self.config.get("APP_NAME", None) or "NoName App"
        self.path = os.path.abspath(self.config.get("BASE_PATH", None) or os.getcwd())

        self.signals = SignalsApplication(app=self)

        self.signals.register("plugin_activate_pre", self,
                              "Gets send right before activation routine of a plugins will be executed")
        self.signals.register("plugin_activate_post", self,
                              "Gets send right after activation routine of a plugins was executed")
        self.signals.register("plugin_deactivate_pre", self,
                              "Gets send right before deactivation routine of a plugins will be executed")
        self.signals.register("plugin_deactivate_post", self,
                              "Gets send right after deactivation routine of a plugins was executed")

        self.plugins = PluginManager(app=self, strict=strict)

        if plugins is not None:
            self.plugins.classes.register(plugins)

        self.shared_objects = SharedObjectManager()

    def _configure_logging(self, logger_dict=None):
        self.log.debug("Configure logging")
        if logger_dict is None:
            self.log.debug("No logger dictionary defined. Doing default logger configuration")
            formatter = logging.Formatter("%(name)s - %(asctime)s - [%(levelname)s] - %(module)s - %(message)s")
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(logging.DEBUG)
            stream_handler.setFormatter(formatter)
            self.log.addHandler(stream_handler)
            self.log.setLevel(logging.INFO)
        else:
            self.log.debug("Logger dictionary defined. Loading dictConfig for logging")
            logging.config.dictConfig(logger_dict)
            self.log.debug("dictConfig loaded")



