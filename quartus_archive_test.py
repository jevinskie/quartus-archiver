#!/usr/bin/env python3

import http.client
import logging
import sys
import time

import lxml.html
import mechanize
import tenacity
from attrs import define
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


@define
class DistInfo:
    edition: str
    operating_system: str
    dl_page_url: str


@tenacity.retry(stop=tenacity.stop_after_attempt(5), wait=tenacity.wait_exponential(min=15, max=60))
def get_dist_link_info(dl_page_url: str) -> DistInfo:
    print(f"opening dl link url {dl_page_url}")
    br.open(dl_page_url)
    url = br.geturl()
    print(f"actual dl link url: {url}")
    if "homepage.html?ref=" in url:
        print(f"got a redirect to home")
        br.back()
        raise ValueError(f"got a redirect to home")
    if "Pro" in br.title():
        edition = "pro"
    elif "Standard" in br.title():
        edition = "standard"
    elif "Lite" in br.title():
        edition = "lite"
    else:
        print(f"unknown edition for '{br.title()}'")
        br.back()
        raise ValueError(f"unknown edition for '{br.title()}'")
    if "Windows" in br.title():
        operating_system = "windows"
    elif "Linux" in br.title():
        operating_system = "linux"
    else:
        print(f"unknown os for '{br.title()}'")
        br.back()
        raise ValueError(f"unknown os for '{br.title()}'")
    br.back()
    return DistInfo(edition=edition, operating_system=operating_system, dl_page_url=url)


def get_dist_infos() -> list[DistInfo]:
    br.open(landing_url)
    dist_infos = []
    dl_links = [lnk.absolute_url for lnk in br.links() if lnk.text.startswith("Download for")]
    for dl_link in dl_links:
        dist_infos.append(get_dist_link_info(dl_link))
    return dist_infos


print(get_dist_links())
