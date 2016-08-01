_gettext = None


def gettext(message):
    """
    Return the localized translation of message.

    .. note:: If :func:`set_gettext` is not called prior, this function
              retuns the message unchanged
    """
    return message if not _gettext else _gettext(message)


def set_gettext(gettext):
    """
    Define a function that will be used to localize messages.

    .. note:: Most common function to use for this would be default :func:`gettext.gettext`
    """
    global _gettext
    _gettext = gettext
