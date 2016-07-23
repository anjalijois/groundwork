import logging

from .exceptions import PluginAttributeMissing


class GwPluginPattern(object):
    def __init__(self, app, *args, name=None, **kwargs):
        super().__init__()
        self.app = app
        self.log = logging.getLogger(self.name)
        self.signals = SignalsPlugin(self)

        # There must be a name for this plugin. Otherwise it is not detectable and manageable on application level
        if not hasattr(self, "name"):
            raise PluginAttributeMissing("name attribute not set in Plugin class. Plugin initialisation stops here.")

        # Let's be sure active is false, even if a child class set something different
        if not hasattr(self, "active"):
            self.active = False

        # This is used as flag for the pluginManager to be sure, that an initiated class has called the __init__()
        # routine of GwPluginPatter
        self._plugin_base_initialised = True

        # Let's tell the pluginManager that this plugin got initialised, so that it gets tracked on app level.
        # This is needed if this class gets initiated by hand and the function self.app.plugins._load() was not used
        # for doing this job.
        self.app.plugins._register_load(self)

    def __getattribute__(self, name):
        """
        Catches all calls on class attributes, but care only for activate() and deactivate().

        If the plugin gets activated or deactivated, the base class can perform extra work.
        So there is no need for a plugin developer to call something like super().activate() for
        his/her plugin. This gets done automatically.
        """
        attr = object.__getattribute__(self, name)
        if hasattr(attr, '__call__'):
            if attr.__name__ == "activate":
                def newfunc(*args, **kwargs):
                    self._pre_activate_injection()
                    result = attr(*args, **kwargs)
                    self._post_activate_injection()
                    return result
                return newfunc
            elif attr.__name__ == "deactivate":
                def newfunc(*args, **kwargs):
                    self._pre_deactivate_injection()
                    result = attr(*args, **kwargs)
                    self._post_deactivate_injection()
                    return result
                return newfunc
            else:
                return attr
        else:
            return attr

    def activate(self):
        """
        Must be overwritten by the plugin class itself.
        """
        self.log.warn("No activation routine in Plugin defined. Define self.activate() in plugin %s" % self.name)

    def deactivate(self):
        """
        Must be overwritten by the plugin class itself.
        """
        self.log.warn("No activation routine in Plugin defined. Define self.deactivate() in plugin %s" % self.name)

    def _pre_activate_injection(self):
        """
        Injects functions before the activation routine of child classes gets called
        :return: None
        """
        if not self.app.plugins.classes.exist(self.__class__.__name__):
            self.app.plugins.classes.register(self.__class__)

        self.app.signals.send("plugin_activate_pre", self)

    def _post_activate_injection(self):
        """
        Injects functions after the activation routine of child classes got called
        :return: None
        """
        self.active = True
        self.app.signals.send("plugin_activate_post", self)

    def _pre_deactivate_injection(self):
        """
        Injects functions before the deactivation routine of child classes gets called
        :return: None
        """
        self.app.signals.send("plugin_deactivate_pre", self)

    def _post_deactivate_injection(self):
        """
        Injects functions after the deactivation routine of child classes got called
        :return: None
        """
        # Lets be sure that active is really set to false.
        self.active = False
        self.app.signals.send("plugin_deactivate_post", self)
        # After all receivers are handled. We start to clean up signals and receivers of this plugin
        # Attention: This clean must not be called via a signal (like in other patterns),
        # because the call order of receivers is not clear and a signal/receiver clean up would prohibit the call
        # of all "later" receivers.
        self.signals.deactivate_plugin_signals()


class SignalsPlugin:
    """
    Signal and Receiver management class on plugin level.
    This class gets initiated once per plugin.

    Mostly delegates function calls to the SingnalListApplication instance on application level.

    :param plugin: The plugin, which wants to use signals
    :type plugin: GwPluginPattern
    """

    def __init__(self, plugin):
        self._plugin = plugin
        self.__app = plugin.app
        self.__log = plugin.log
        self.__log.info("Plugin messages initialised")

    def deactivate_plugin_signals(self):
        receivers = self.get_receiver()
        for receiver in receivers.keys():
            self.disconnect(receiver)

        signals = self.get()
        for signal in signals:
            self.unregister(signal)

    def register(self, signal, description):
        """
        Registers a new signal.
        Only registered signals are allowed to be send.

        :param signal: Unique name of the signal
        :param description: Description of the reason or use case, why this signal is needed.
                            Used for documentation.
        """
        return self.__app.signals.register(signal, self._plugin, description)

    def unregister(self, signal):
        return self.__app.signals.unregister(signal)

    def connect(self, receiver, signal, function, description):
        """
        Connect a receiver to a signal

        :param receiver: Name of the receiver
        :type receiver: str
        :param signal: Name of the signal. Must already be registered!
        :type signal: str
        :param function: Callable functions, which shall be executed, of signal is send.
        :param description: Description of the reason or use case, why this connection is needed.
                            Used for documentation.
        """
        return self.__app.signals.connect(receiver, signal, function, self._plugin, description)

    def disconnect(self, receiver):
        """
        Disconnect a receiver from a signal.
        Receiver must exist, otherwise an exception is thrown.

        :param receiver: Name of the receiver
        """
        return self.__app.signals.disconnect(receiver)

    def send(self, signal, **kwargs):
        """
        Sends a signal for the given plugin.

        :param signal: Name of the signal
        :type signal: str
        """
        return self.__app.signals.send(signal, plugin=self._plugin, **kwargs)

    def get(self, signal=None):
        return self.__app.signals.get(signal, self._plugin)

    def get_receiver(self, receiver=None):
        return self.__app.signals.get_receiver(receiver, self._plugin)

    def __getattr__(self, item):
        """
        Catches unknown function/attribute calls and delegates them to SignalsListApplication
        """

        def method(*args, **kwargs):
            func = getattr(self.__app.signals, item, None)
            if func is None:
                raise AttributeError("SignalsListApplication does not have an attribute called %s" % item)
            return func(*args, plugin=self._plugin, **kwargs)

        return method
