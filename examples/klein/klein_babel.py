# Inpired by muffin-babel https://github.com/klen/muffin-babel

import re
from functools import wraps

from babel import support
from twisted.python import context

locale_delim_re = re.compile(r"[_-]")
accept_re = re.compile(
    r"""(                         # media-range capturing-parenthesis
            [^\s;,]+              # type/subtype
            (?:[ \t]*;[ \t]*      # ";"
            (?:                   # parameter non-capturing-parenthesis
                [^\s;,q][^\s;,]*  # token that doesn't start with "q"
            |                     # or
                q[^\s;,=][^\s;,]* # token that is more than just "q"
            )
            )*                    # zero or more parameters
        )                         # end of media-range
        (?:[ \t]*;[ \t]*q=        # weight is a "q" parameter
            (\d*(?:\.\d+)?)       # qvalue capturing-parentheses
            [^,]*                 # "extension" accept params: who cares?
        )?                        # accept params are optional
    """,
    re.VERBOSE,
)


def parse_accept_header(header):
    """Parse accept headers."""
    result = []
    for match in accept_re.finditer(header):
        quality = match.group(2)
        if not quality:
            quality = 1
        else:
            quality = max(min(float(quality), 1), 0)
        result.append((match.group(1), quality))
    return result


def select_locale_by_request(request, default="en"):
    accept_language = request.getHeader("ACCEPT-LANGUAGE")
    if not accept_language:
        return default

    ulocales = [
        (q, locale_delim_re.split(v)[0])
        for v, q in parse_accept_header(accept_language)
    ]
    ulocales.sort()
    ulocales.reverse()

    return ulocales[0][1]


def locale_from_request(fn):
    @wraps(fn)
    def wrapper(request, *args, **kwargs):
        locale = select_locale_by_request(request)
        translations = support.Translations.load(
            "translations",
            locales=locale,
            domain="messages",
        )
        ctx = {"locale": locale, "translations": translations}
        return context.call(ctx, fn, request, *args, **kwargs)

    return wrapper


def gettext(string):
    return context.get("translations", default=support.NullTranslations()).gettext(
        string,
    )
