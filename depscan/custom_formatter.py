import logging
import sys


def init_logging(verbose=False, stream=None):
    stream = stream if stream is not None else sys.stderr
    level = logging.DEBUG if verbose else logging.WARNING
    log = logging.getLogger("depscan")
    log.setLevel(level)
    if not log.handlers:
        handler = logging.StreamHandler(stream)
        handler.setFormatter(CustomFormatter())
        log.addHandler(handler)
    log.propagate = False


class CustomFormatter(logging.Formatter):
    # Reset
    reset = "\x1b[0m"

    # Regular Colors
    black = "\x1b[30m"
    red = "\x1b[31m"
    green = "\x1b[32m"
    yellow = "\x1b[33m"
    blue = "\x1b[34m"
    magenta = "\x1b[35m"
    cyan = "\x1b[36m"
    white = "\x1b[37m"
    grey = "\x1b[90m"  # Often used for light black or grey

    # Bright Colors (Bold/High Intensity)
    bright_black = "\x1b[90m"
    bright_red = "\x1b[91m"
    bright_green = "\x1b[92m"
    bright_yellow = "\x1b[93m"
    bright_blue = "\x1b[94m"
    bright_magenta = "\x1b[95m"
    bright_cyan = "\x1b[96m"
    bright_white = "\x1b[97m"

    # Background Colors
    bg_black = "\x1b[40m"
    bg_red = "\x1b[41m"
    bg_green = "\x1b[42m"
    bg_yellow = "\x1b[43m"
    bg_blue = "\x1b[44m"
    bg_magenta = "\x1b[45m"
    bg_cyan = "\x1b[46m"
    bg_white = "\x1b[47m"
    bg_grey = "\x1b[100m"  # Often used for light black or grey background

    # Bright Background Colors
    bg_bright_black = "\x1b[100m"
    bg_bright_red = "\x1b[101m"
    bg_bright_green = "\x1b[102m"
    bg_bright_yellow = "\x1b[103m"
    bg_bright_blue = "\x1b[104m"
    bg_bright_magenta = "\x1b[105m"
    bg_bright_cyan = "\x1b[106m"
    bg_bright_white = "\x1b[107m"

    # Bold, Underline, Reversed, and Reset Formatting
    bold = "\x1b[1m"
    underline = "\x1b[4m"
    reverse = "\x1b[7m"

    time_format = grey + "%(asctime)s " + white + "["
    level_format = "%(levelname)s"
    line_format = white + "] %(message)s " + grey + "(%(filename)s:%(lineno)d)"

    FORMATS = {
        logging.DEBUG: reset + time_format + reset + blue + level_format + reset + line_format + reset,
        logging.INFO: reset + time_format + reset + green + level_format + reset + line_format + reset,
        logging.WARNING: reset + time_format + reset + yellow + level_format + reset + line_format + reset,
        logging.ERROR: reset + time_format + reset + red + level_format + reset + line_format + reset,
        logging.CRITICAL: reset + time_format + reset + bright_red + level_format + reset + line_format + reset
    }

    def format(self, record):
        record.levelname = record.levelname.lower()
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)
