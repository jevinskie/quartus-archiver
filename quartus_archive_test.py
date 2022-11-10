#!/usr/bin/env python3

import http.client
import logging
import sys

import lxml.html
import mechanize
from lxml import objectify
from lxml.html import html5parser
from rich import print

logger = logging.getLogger("mechanize")
logger.addHandler(logging.StreamHandler(sys.stdout))
logger.setLevel(logging.DEBUG)

http.client.HTTPConnection.debuglevel = 5

landing_url = "https://www.intel.com/content/www/us/en/products/details/fpga/development-tools/quartus-prime/resource.html"

br = mechanize.Browser()
br.set_handle_robots(False)
br.set_header(
    "User-Agent",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
)


def get_dist_links() -> list[tuple[str, str, mechanize.Link]]:
    br.open(landing_url)
    dist_links = []
    dl_links = [l for l in br.links() if l.text.startswith("Download for")]
    print(f"dl_links {dl_links}")
    open("dump-meta.html", "wb").write(br.response().get_data())
    for l in dl_links:
        br.open(landing_url)
        print(f"l: {l}")
        print(f"l.absolute_url {l.absolute_url}")
        br.follow_link(l)
        open("dump.html", "wb").write(br.response().get_data())
        if "Pro" in br.title():
            edition = "pro"
        elif "Standard" in br.title():
            edition = "standard"
        elif "Lite" in br.title():
            edition = "lite"
        else:
            raise ValueError(f"unknown edition for '{br.title()}'")
        if "Windows" in br.title():
            os = "windows"
        elif "Linux" in br.title():
            os = "linux"
        else:
            raise ValueError(f"unknown os for '{br.title()}'")
        dist_links.append((edition, os, l))
    return dist_links


print(get_dist_links())
