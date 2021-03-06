# -*- coding: utf-8 -*-
# © 2015 ACSONE SA/NV
# License AGPLv3 (http://www.gnu.org/licenses/agpl-3.0-standalone.html)

import logging
import os

import argparse
import argcomplete
import fnmatch

from .log import DebugLogFormatter
from .log import LogFormatter
from .config import load_config
from .repo import Repo


logger = logging.getLogger(__name__)

_LOG_LEVEL_STRINGS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']

VERSION='1.0.1.ot2'


def _log_level_string_to_int(log_level_string):
    if log_level_string not in _LOG_LEVEL_STRINGS:
        message = 'invalid choice: {0} (choose from {1})'.format(
            log_level_string, _LOG_LEVEL_STRINGS)
        raise argparse.ArgumentTypeError(message)

    log_level_int = getattr(logging, log_level_string, logging.INFO)
    # check the logging log_level_choices have not changed from our expected
    # values
    assert isinstance(log_level_int, int)

    return log_level_int


def setup_logger(log=None, level=logging.INFO):
    """Setup logging for CLI use.
    :param log: instance of logger
    :type log: :py:class:`Logger`
    """
    if not log:
        log = logging.getLogger()
    if not log.handlers:
        channel = logging.StreamHandler()
        if level == logging.DEBUG:
            channel.setFormatter(DebugLogFormatter())
        else:
            channel.setFormatter(LogFormatter())

        log.setLevel(level)
        log.addHandler(channel)


def get_parser():
    """Return :py:class:`argparse.ArgumentParser` instance for CLI."""

    main_parser = argparse.ArgumentParser()

    main_parser.add_argument(
        '-v', '--version',
        dest='show_version',
        action='store_true', default=False,
        help='Show version and exit',
    )

    main_parser.add_argument(
        '-c', '--config',
        dest='config',
        type=str,
        nargs='?',
        help='Pull the latest repositories from config(s)'
    ).completer = argcomplete.completers.FilesCompleter(
        allowednames=('.yaml', '.json'), directories=False
    )

    main_parser.add_argument(
        '-p', '--push',
        dest='do_push',
        action='store_true', default=False,
        help='Push result to target',
    )

    main_parser.add_argument(
        '-d', '--dirmatch',
        dest='dirmatch',
        type=str,
        nargs='?',
        help='Pull only from the directories. Accepts fnmatch(1)'
             'by commands'
    )
    main_parser.add_argument(
        '--log-level',
        default='INFO',
        dest='log_level',
        type=_log_level_string_to_int,
        nargs='?',
        help='Set the logging output level. {0}'.format(_LOG_LEVEL_STRINGS))
    return main_parser


def main():
    """Main CLI application."""

    parser = get_parser()

    argcomplete.autocomplete(parser, always_complete_options=False)

    args = parser.parse_args()

    if args.show_version:
        print("GitAggregate v%s" % VERSION)
        exit(0)

    setup_logger(
        level=args.log_level
    )

    try:
        if args.config:
            load_aggregate(args)
        else:
            parser.print_help()
    except KeyboardInterrupt:
        pass


def match_dir(cwd, dirmatch=None):
    if not dirmatch:
        return True
    return (fnmatch.fnmatch(cwd, dirmatch) or
            fnmatch.fnmatch(os.path.relpath(cwd), dirmatch) or
            os.path.relpath(cwd) == os.path.relpath(dirmatch))


def load_aggregate(args):
    """Load YAML and JSON configs and begin creating / updating , aggregating
    and pushing the repos"""
    repos = load_config(args.config)
    dirmatch = args.dirmatch
    for repo_dict in repos:
        r = Repo(**repo_dict)
        logger.debug('%s' % r)
        if not match_dir(r.cwd, dirmatch):
            logger.info("Skip %s", r.cwd)
            continue
        r.aggregate()
        if args.do_push:
            r.push()
