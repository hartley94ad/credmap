#!/usr/bin/env python

"""
Copyright (c) 2015 Roberto Christopher Salgado Bjerre.

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation the
rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
sell copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

from __future__ import print_function

import re

from time import strftime
from xml.etree.ElementTree import parse
from sys import stdout as sys_stdout
from subprocess import Popen, PIPE
from optparse import OptionParser
from getpass import getpass
from random import sample
from os import listdir
from os.path import isfile, join, dirname, exists
from urllib2 import build_opener, install_opener, ProxyHandler
from urllib2 import HTTPCookieProcessor, HTTPHandler, HTTPSHandler

from lib.website import Website
from lib.common import color, cookie_handler
from lib.settings import BW
from lib.settings import ASK, PLUS, INFO, TEST, WARN, ERROR, DEBUG

NAME = "credmap"
VERSION = "v0.1"
URL = "https://github.com/lightos/credmap/"

# Maximum length of left option column in help listing
MAX_HELP_OPTION_LENGTH = 20

# Character used for progress rotator
ROTATOR_CHARS = "|/-\\"

BANNER_PASSWORDS = ("123456", "HUNTER2", "LOVE",
                    "SECRET", "ABC123", "GOD", "SEX")

BANNER = """               . .IIIII             .II
  I%sIIII. I  II  .    II..IIIIIIIIIIIIIIIIIIII
 .  .IIIIII  II             IIIIII%sIIIII  I.
    .IIIII.III I        IIIIIIIIIIIIIIIIIIIIIII
   .II%sII           II  .IIIII IIIIIIIIIIII. I
    IIIIII             IIII I  II%sIIIIIII I
    .II               IIIIIIIIIIIII  IIIIIIIII
       I.           .III%sIIII    I   II  I
         .IIII        IIIIIIIIIIII     .       I
          IIIII.          IIIIII           . I.
          II%sIII         IIIII             ..I  II .
           IIIIII          IIII...             IIII
            IIII           III. I            II%sII
            III             I                I  III
            II                                   I   .
             I                                        """

# Location of the folder containing the websites to test
SITES_DIR = "websites"

# Location of file containing user agents
USER_AGENTS_FILE = "agents.txt"

# Location of Git repository
GIT_REPOSITORY = "https://github.com/lightos/credmap.git"

EXAMPLES = """
Examples:
./credmap.py --username janedoe --email janedoe@email.com
./credmap.py -u johndoe -e johndoe@email.com --exclude "github.com, live.com"
./credmap.py -u johndoe -p abc123 -vvv --only "linkedin.com, facebook.com"
./credmap.py -e janedoe@example.com --verbose --proxy "https://127.0.0.1:8080"
./credmap.py --list
"""


def print(*args, **kwargs):
    """
    Currently no purpose.
    """

    return __builtins__.print(*args, **kwargs)


class AttribDict(dict):
    """
    Gets and Sets attributes for a dict.
    """
    def __getattr__(self, name):
        return self.get(name)

    def __setattr__(self, name, value):
        return self.__setitem__(name, value)


def get_revision():
    """
    Returns abbreviated commit hash number as retrieved with:
    "git rev-parse --short HEAD".
    """

    retval = None
    filepath = None
    _ = dirname(__file__)

    while True:
        filepath = join(_, ".git", "HEAD")
        if exists(filepath):
            break
        else:
            filepath = None
            if _ == dirname(_):
                break
            else:
                _ = dirname(_)

    while True:
        if filepath and isfile(filepath):
            with open(filepath, "r") as f:
                content = f.read()
                filepath = None
                if content.startswith("ref: "):
                    filepath = join(_, ".git", content.replace("ref: ", "")
                                    ).strip()
                else:
                    match = re.match(r"(?i)[0-9a-f]{32}", content)
                    retval = match.group(0) if match else None
                    break
        else:
            break

    if not retval:
        process = Popen("git rev-parse --verify HEAD", shell=True,
                        stdout=PIPE, stderr=PIPE)
        stdout, _ = process.communicate()
        match = re.search(r"(?i)[0-9a-f]{32}", stdout or "")
        retval = match.group(0) if match else None

    return retval[:7] if retval else None


def check_revision():
    """
    Adapts the default version string and banner to
    use the revision number.
    """

    global BANNER
    global VERSION

    revision = get_revision()

    if revision:
        _ = VERSION
        VERSION = "%s-%s" % (VERSION, revision)
        BANNER = BANNER.replace(_, VERSION)


def update():
    """
    Updates the program via git pull.
    """

    print("%s Checking for updates..." % INFO)

    process = Popen("git pull %s HEAD" % GIT_REPOSITORY, shell=True,
                    stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    success = not process.returncode

    if success:
        updated = "Already" not in stdout
        process = Popen("git rev-parse --verify HEAD", shell=True,
                        stdout=PIPE, stderr=PIPE)
        stdout, _ = process.communicate()
        revision = (stdout[:7] if stdout and
                    re.search(r"(?i)[0-9a-f]{32}", stdout) else "-")
        print("%s the latest revision '%s'." %
              ("%s Already at" % INFO if not updated else
               "%s Updated to" % PLUS, revision))
    else:
        print("%s Problem occurred while updating program.\n" % WARN)

        _ = re.search(r"(?P<error>Your\slocal\schanges\sto\sthe\sfollowing\s"
                      r"files\swould\sbe\soverwritten\sby\smerge:"
                      r"(?:\n\t[^\n]+)*)", stderr)
        if _:
            def question():
                print("\n%s Would you like to overwrite your changes and set "
                      "your local copy to the latest commit?" % ASK)
                sys_stdout.write("%s ALL of your local changes will be deleted"
                                 " [Y/n]: " % WARN)
                _ = raw_input()

                if not _:
                    _ = "y"

                if _.lower() == "n":
                    exit()
                elif _.lower() == "y":
                    return
                else:
                    print("%s Did not understand your answer! Try again." %
                          ERROR)
                    question()

            print("%s" % _.group("error"))

            question()

            process = Popen("git reset --hard", shell=True,
                            stdout=PIPE, stderr=PIPE)
            stdout, _ = process.communicate()

            if "HEAD is now at" in stdout:
                print("\n%s Local copy reset to current git branch." % INFO)
                print("%s Attemping to run update again..." % INFO)
            else:
                print("%s Unable to reset local copy to current git branch." %
                      WARN)
                exit()

            update()
        else:
            print("%s Please make sure that you have "
                  "a 'git' package installed.", INFO)


def parse_args():
    """
    Parses the command line arguments.
    """
    # Override epilog formatting
    OptionParser.format_epilog = lambda self, formatter: self.epilog

    parser = OptionParser(usage="usage: %prog --email EMAIL [options]",
                          epilog=EXAMPLES)

    parser.add_option("-v", "--verbose", action="count", dest="verbose",
                      help="display extra output information")

    parser.add_option("-u", "--username", dest="username",
                      help="set the username to test with")

    parser.add_option("-p", "--password", dest="password",
                      help="set the password to test with")

    parser.add_option("-e", "--email", dest="email",
                      help="set an email to test with")

    parser.add_option("-x", "--exclude", dest="exclude",
                      help="exclude sites from testing")

    parser.add_option("-o", "--only", dest="only",
                      help="test only listed sites")

    parser.add_option("-s", "--safe-urls", dest="safe_urls",
                      action="store_true",
                      help="only test sites that use HTTPS.")

    parser.add_option("-i", "--ignore-proxy", dest="ignore_proxy",
                      action="store_true",
                      help="ignore system default HTTP proxy")

    parser.add_option("--proxy", dest="proxy",
                      help="set proxy (e.g. \"socks5://192.168.1.2:9050\")")

    parser.add_option("--list", action="store_true", dest="list",
                      help="list available sites to test with")

    parser.add_option("--update", dest="update", action="store_true",
                      help="update from the official git repository")

    parser.formatter.store_option_strings(parser)
    parser.formatter.store_option_strings = lambda _: None

    for option, value in parser.formatter.option_strings.items():
        value = re.sub(r"\A(-\w+) (\w+), (--[\w-]+=(\2))\Z", r"\g<1>/\g<3>",
                       value)
        value = value.replace(", ", '/')
        if len(value) > MAX_HELP_OPTION_LENGTH:
            value = ("%%.%ds.." % (MAX_HELP_OPTION_LENGTH -
                                   parser.formatter.indent_increment)) % value
        parser.formatter.option_strings[option] = value

    args = parser.parse_args()[0]

    if not any((args.username, args.email, args.update, args.list)):
        parser.error("Required argument is missing. Use '-h' for help.")

    return args


def list_sites(extension=False):
    """
    List available sites for testing found in the websites folder.
    Read folder containing each website's XML files.
    """

    return [_ if extension else _.replace(".xml", "")
            for _ in listdir(SITES_DIR) if isfile(join(SITES_DIR, _))]


def populate_site(site, args):
    """
    Parse sites in XML files and return objects.
    """

    try:
        xml_tree = parse("%s/%s.xml" % (SITES_DIR, site)).getroot()
    except Exception:
        print("%s parsing XML file \"%s\". Skipping...\n" % (ERROR,
                                                             color(site, BW)))
        return

    site_properties = AttribDict()

    for _ in xml_tree:
        if _.tag == "multiple_params":
            site_properties.multiple_params = True
            site_properties.multiple_params_url = _.attrib["value"]
            continue
        if _.tag == "custom_search":
            site_properties.custom_search = {"regex": _.attrib["regex"],
                                             "value": _.attrib["value"]}
            continue
        if _.tag == "time_parameter":
            site_properties.time_parameter = {"type": _.attrib["type"],
                                              "value": _.attrib["value"]}
            continue
        if _.tag == "invalid_http_status":
            site_properties.invalid_http_status = {"msg": _.attrib["msg"],
                                                   "value": _.attrib["value"]}
            continue
        if "value" in _.attrib:
            site_properties[_.tag] = _.attrib["value"]
        if "type" in _.attrib:
            site_properties["%s_type" % _.tag] = _.attrib["type"]

    if site_properties.multiple_params:
        site_properties.multiple_params = []
        for _ in xml_tree.iter('param'):
            _ = {k: v for k, v in _.attrib.items() if v}
            if _:
                site_properties.multiple_params.append(_)

    match = re.match(r"(?P<type>[^:]+)://[^.]+(\.\w+)*",
                     site_properties.login_url, re.I)

    if not match:
        print("%s unable to read URL for login in XML file for \"%s\". "
              "Skipping site...\n" % (ERROR, color(site_properties.name, BW)))
        return

    if args.safe_urls and match.group("type").upper() != "HTTPS":
        if args.verbose:
            print("%s URL uses an unsafe transportation mechanism: \"%s\". "
                  "Skipping site...\n" % (WARN, match.group("type").upper()))
        return

    if(not site_properties.login_parameter or
       not site_properties.password_parameter):
        print("%s current XML file is missing parameter(s) for login. "
              "Skipping site...\n" % ERROR)
        return

    return site_properties


def main():
    """
    Initializes and executes the program
    """
    global args

    login_sucessful = []
    login_failed = []

    check_revision()

    print("%s\n\n%s %s (%s)\n" % (
        BANNER % tuple([color(_) for _ in BANNER_PASSWORDS]),
        NAME, VERSION, URL))

    args = parse_args()

    if args.update:
        update()
        exit()

    if args.list:
        sites = list_sites()
        for _ in sites:
            print("- %s" % _)
        exit()

    if not args.password:
        args.password = getpass("%s Please enter password:" % INFO)
        print("")

    if args.ignore_proxy:
        proxy_handler = ProxyHandler({})
        opener = build_opener(HTTPHandler(), HTTPSHandler(), proxy_handler,
                              HTTPCookieProcessor(cookie_handler))
        install_opener(opener)

    elif args.proxy:
        match = re.search(r"(?P<type>[^:]+)://(?P<address>[^:]+)"
                          r":(?P<port>\d+)", args.proxy, re.I)
        if match:
            if match.group("type").upper() in ("HTTP", "HTTPS"):
                proxy_handler = ProxyHandler({match.group("type"): args.proxy})
                opener = build_opener(
                    HTTPHandler(),
                    HTTPSHandler(),
                    proxy_handler,
                    HTTPCookieProcessor(cookie_handler))
                install_opener(opener)
            else:
                from thirdparty.socks import socks
                if match.group("type").upper() == "SOCKS4":
                    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS4,
                                          match.group("address"),
                                          int(match.group("port")), True)
                elif match.group("type").upper() == "SOCKS5":
                    socks.setdefaultproxy(socks.PROXY_TYPE_SOCKS5,
                                          match.group("address"),
                                          int(match.group("port")), True)
        else:
            print("%s wrong proxy format "
                  "(proper example: \"http://127.0.0.1:8080\")." % WARN)
            exit()
    else:
        opener = build_opener(HTTPHandler(),
                              HTTPSHandler(),
                              HTTPCookieProcessor(cookie_handler))
        install_opener(opener)

    with open(USER_AGENTS_FILE, 'r') as ua_file:
        args.user_agent = sample(ua_file.readlines(), 1)[0].strip()

    credentials = {"username": args.username, "email": args.email,
                   "password": args.password}
    sites = list_sites()

    if args.only:
        sites = [site for site in sites if site in args.only]
    elif args.exclude:
        sites = [site for site in sites if site not in args.exclude]

    print("%s Loaded %d %s to test." % (INFO, len(sites),
                                        "site" if len(sites) == 1
                                        else "sites"))
    print("%s Starting tests at: \"%s\"\n" % (INFO, color(strftime("%X"), BW)))

    for site in sites:
        _ = populate_site(site, args)
        if not _:
            continue
        target = Website(_, {"verbose": args.verbose})

        if (target.username_or_email == "email" and not args.email or
                target.username_or_email == "username" and not args.username):
            if args.verbose:
                print("%s Skipping \"%s\" since no \"%s\" was specified.\n" %
                      (INFO, color(target.name),
                       color(target.username_or_email)))
            continue

        print("%s Testing \"%s\"" % (TEST, color(target.name, BW)))

        if not target.user_agent:
            target.user_agent = args.user_agent

        if target.perform_login(credentials, cookie_handler):
            login_sucessful.append(target.name)
        else:
            login_failed.append(target.name)

    if not args.verbose:
        print()

    if len(login_sucessful) > 0 or len(login_failed) > 0:
        print("%s Succesfully logged into %s/%s websites." %
              (INFO, color(len(login_sucessful), BW),
               color(len(login_sucessful) + len(login_failed), BW)))
        print("%s An overall success rate of %s.\n" %
              (INFO, color("%%%s" % (100 * len(login_sucessful) / len(sites)),
                           BW)))

    if len(login_sucessful) > 0:
        print("%s The provided credentials worked on the following website%s: "
              "%s\n" % (PLUS, "s" if len(login_sucessful) != 1 else "",
                        ", ".join(login_sucessful)))

    print("%s Finished tests at: \"%s\"\n" % (INFO, color(strftime("%X"), BW)))


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n%s Ctrl-C pressed." % INFO)
