#!/usr/bin/env python3

import datetime
import http.client
import logging
import os
import pickle
import re
import sys
import time
from http.cookiejar import CookieJar
from multiprocessing import Pool
from typing import Optional

import lxml.html
import mechanize
import packaging.version
import requests
import tenacity
from attrs import define
from rich import print

landing_url = "https://www.intel.com/content/www/us/en/products/details/fpga/development-tools/quartus-prime/resource.html"


def static_vars(**kwargs):
    def decorate(func):
        for k in kwargs:
            setattr(func, k, kwargs[k])
        return func

    return decorate


class Version(packaging.version.Version):
    def __repr__(self) -> str:
        return f"Version('{self}')"


@define
class DistInfo:
    edition: str
    operating_system: str
    dl_page_urls: tuple[Version, str]


@define
class Download:
    filename: str
    dist_url: str
    cdn_url: Optional[str]
    sha1: str
    version: Version
    ident: int
    updated_date: datetime.date
    listed_size: int
    operating_system: str
    edition: str


static_dist_infos = [
    DistInfo(
        edition="pro",
        operating_system="windows",
        dl_page_urls=[
            (
                Version("22.3"),
                "https://www.intel.com/content/www/us/en/software-kit/746667/intel-quartus-prime-pro-edition-design-software-version-22-3-for-windows.html",
            ),
            (
                Version("22.2"),
                "https://www.intel.com/content/www/us/en/software-kit/734898/intel-quartus-prime-pro-edition-design-software-version-22-2-for-windows.html",
            ),
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/727907/intel-quartus-prime-pro-edition-design-software-version-22-1-for-windows.html",
            ),
            (
                Version("21.4"),
                "https://www.intel.com/content/www/us/en/software-kit/706105/intel-quartus-prime-pro-edition-design-software-version-21-4-for-windows.html",
            ),
            (
                Version("21.3"),
                "https://www.intel.com/content/www/us/en/software-kit/670288/intel-quartus-prime-pro-edition-design-software-version-21-3-for-windows.html",
            ),
            (
                Version("21.2"),
                "https://www.intel.com/content/www/us/en/software-kit/670232/intel-quartus-prime-pro-edition-design-software-version-21-2-for-windows.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/670601/intel-quartus-prime-pro-edition-design-software-version-21-1-for-windows.html",
            ),
            (
                Version("20.4"),
                "https://www.intel.com/content/www/us/en/software-kit/710229/intel-quartus-prime-pro-edition-design-software-version-20-4-for-windows.html",
            ),
            (
                Version("20.3"),
                "https://www.intel.com/content/www/us/en/software-kit/660536/intel-quartus-prime-pro-edition-design-software-version-20-3-for-windows.html",
            ),
            (
                Version("20.2"),
                "https://www.intel.com/content/www/us/en/software-kit/660537/intel-quartus-prime-pro-edition-design-software-version-20-2-for-windows.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660925/intel-quartus-prime-pro-edition-design-software-version-20-1-for-windows.html",
            ),
            (
                Version("19.4"),
                "https://www.intel.com/content/www/us/en/software-kit/661628/intel-quartus-prime-pro-edition-design-software-version-19-4-for-windows.html",
            ),
            (
                Version("19.3"),
                "https://www.intel.com/content/www/us/en/software-kit/661657/intel-quartus-prime-pro-edition-design-software-version-19-3-for-windows.html",
            ),
            (
                Version("19.2"),
                "https://www.intel.com/content/www/us/en/software-kit/661713/intel-quartus-prime-pro-edition-design-software-version-19-2-for-windows.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665934/intel-quartus-prime-pro-edition-design-software-version-19-1-for-windows.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664781/intel-quartus-prime-pro-edition-design-software-version-18-1-for-windows.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667146/intel-quartus-prime-pro-edition-design-software-version-18-0-for-windows.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669352/intel-quartus-prime-pro-edition-design-software-version-17-1-for-windows.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669449/intel-quartus-prime-pro-edition-design-software-version-17-0-for-windows.html",
            ),
        ],
    ),
    DistInfo(
        edition="pro",
        operating_system="linux",
        dl_page_urls=[
            (
                Version("22.3"),
                "https://www.intel.com/content/www/us/en/software-kit/746666/intel-quartus-prime-pro-edition-design-software-version-22-3-for-linux.html",
            ),
            (
                Version("22.2"),
                "https://www.intel.com/content/www/us/en/software-kit/734897/intel-quartus-prime-pro-edition-design-software-version-22-2-for-linux.html",
            ),
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/727906/intel-quartus-prime-pro-edition-design-software-version-22-1-for-linux.html",
            ),
            (
                Version("21.4"),
                "https://www.intel.com/content/www/us/en/software-kit/706104/intel-quartus-prime-pro-edition-design-software-version-21-4-for-linux.html",
            ),
            (
                Version("21.3"),
                "https://www.intel.com/content/www/us/en/software-kit/670287/intel-quartus-prime-pro-edition-design-software-version-21-3-for-linux.html",
            ),
            (
                Version("21.2"),
                "https://www.intel.com/content/www/us/en/software-kit/670231/intel-quartus-prime-pro-edition-design-software-version-21-2-for-linux.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/670599/intel-quartus-prime-pro-edition-design-software-version-21-1-for-linux.html",
            ),
            (
                Version("20.4"),
                "https://www.intel.com/content/www/us/en/software-kit/710228/intel-quartus-prime-pro-edition-design-software-version-20-4-for-linux.html",
            ),
            (
                Version("20.3"),
                "https://www.intel.com/content/www/us/en/software-kit/660532/intel-quartus-prime-pro-edition-design-software-version-20-3-for-linux.html",
            ),
            (
                Version("20.2"),
                "https://www.intel.com/content/www/us/en/software-kit/660533/intel-quartus-prime-pro-edition-design-software-version-20-2-for-linux.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660923/intel-quartus-prime-pro-edition-design-software-version-20-1-for-linux.html",
            ),
            (
                Version("19.4"),
                "https://www.intel.com/content/www/us/en/software-kit/661627/intel-quartus-prime-pro-edition-design-software-version-19-4-for-linux.html",
            ),
            (
                Version("19.3"),
                "https://www.intel.com/content/www/us/en/software-kit/661656/intel-quartus-prime-pro-edition-design-software-version-19-3-for-linux.html",
            ),
            (
                Version("19.2"),
                "https://www.intel.com/content/www/us/en/software-kit/661712/intel-quartus-prime-pro-edition-design-software-version-19-2-for-linux.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665933/intel-quartus-prime-pro-edition-design-software-version-19-1-for-linux.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664780/intel-quartus-prime-pro-edition-design-software-version-18-1-for-linux.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667145/intel-quartus-prime-pro-edition-design-software-version-18-0-for-linux.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669351/intel-quartus-prime-pro-edition-design-software-version-17-1-for-linux.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669446/intel-quartus-prime-pro-edition-design-software-version-17-0-for-linux.html",
            ),
        ],
    ),
    DistInfo(
        edition="standard",
        operating_system="windows",
        dl_page_urls=[
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/757236/intel-quartus-prime-standard-edition-design-software-version-22-1-for-windows.html",
            ),
            (
                Version("21.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/736595/intel-quartus-prime-standard-edition-design-software-version-21-1-1-for-windows.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/684188/intel-quartus-prime-standard-edition-design-software-version-21-1-for-windows.html",
            ),
            (
                Version("20.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660905/intel-quartus-prime-standard-edition-design-software-version-20-1-1-for-windows.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/661015/intel-quartus-prime-standard-edition-design-software-version-20-1-for-windows.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664522/intel-quartus-prime-standard-edition-design-software-version-19-1-for-windows.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665987/intel-quartus-prime-standard-edition-design-software-version-18-1-for-windows.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667160/intel-quartus-prime-standard-edition-design-software-version-18-0-for-windows.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669393/intel-quartus-prime-standard-edition-design-software-version-17-1-for-windows.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669514/intel-quartus-prime-standard-edition-design-software-version-17-0-for-windows.html",
            ),
        ],
    ),
    DistInfo(
        edition="standard",
        operating_system="linux",
        dl_page_urls=[
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/757235/intel-quartus-prime-standard-edition-design-software-version-22-1-for-linux.html",
            ),
            (
                Version("21.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/736594/intel-quartus-prime-standard-edition-design-software-version-21-1-1-for-linux.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/684187/intel-quartus-prime-standard-edition-design-software-version-21-1-for-linux.html",
            ),
            (
                Version("20.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660903/intel-quartus-prime-standard-edition-design-software-version-20-1-1-for-linux.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/661005/intel-quartus-prime-standard-edition-design-software-version-20-1-for-linux.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664520/intel-quartus-prime-standard-edition-design-software-version-19-1-for-linux.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665986/intel-quartus-prime-standard-edition-design-software-version-18-1-for-linux.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667157/intel-quartus-prime-standard-edition-design-software-version-18-0-for-linux.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669392/intel-quartus-prime-standard-edition-design-software-version-17-1-for-linux.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669513/intel-quartus-prime-standard-edition-design-software-version-17-0-for-linux.html",
            ),
        ],
    ),
    DistInfo(
        edition="lite",
        operating_system="windows",
        dl_page_urls=[
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/757262/intel-quartus-prime-lite-edition-design-software-version-22-1-for-windows.html",
            ),
            (
                Version("21.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/736572/intel-quartus-prime-lite-edition-design-software-version-21-1-1-for-windows.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/684216/intel-quartus-prime-lite-edition-design-software-version-21-1-for-windows.html",
            ),
            (
                Version("20.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660907/intel-quartus-prime-lite-edition-design-software-version-20-1-1-for-windows.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/661019/intel-quartus-prime-lite-edition-design-software-version-20-1-for-windows.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664527/intel-quartus-prime-lite-edition-design-software-version-19-1-for-windows.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665990/intel-quartus-prime-lite-edition-design-software-version-18-1-for-windows.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667193/intel-quartus-prime-lite-edition-design-software-version-18-0-for-windows.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669444/intel-quartus-prime-lite-edition-design-software-version-17-1-for-windows.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669557/intel-quartus-prime-lite-edition-design-software-version-17-0-for-windows.html",
            ),
        ],
    ),
    DistInfo(
        edition="lite",
        operating_system="linux",
        dl_page_urls=[
            (
                Version("22.1"),
                "https://www.intel.com/content/www/us/en/software-kit/757261/intel-quartus-prime-lite-edition-design-software-version-22-1-for-linux.html",
            ),
            (
                Version("21.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/736571/intel-quartus-prime-lite-edition-design-software-version-21-1-1-for-linux.html",
            ),
            (
                Version("21.1"),
                "https://www.intel.com/content/www/us/en/software-kit/684215/intel-quartus-prime-lite-edition-design-software-version-21-1-for-linux.html",
            ),
            (
                Version("20.1.1"),
                "https://www.intel.com/content/www/us/en/software-kit/660904/intel-quartus-prime-lite-edition-design-software-version-20-1-1-for-linux.html",
            ),
            (
                Version("20.1"),
                "https://www.intel.com/content/www/us/en/software-kit/661017/intel-quartus-prime-lite-edition-design-software-version-20-1-for-linux.html",
            ),
            (
                Version("19.1"),
                "https://www.intel.com/content/www/us/en/software-kit/664524/intel-quartus-prime-lite-edition-design-software-version-19-1-for-linux.html",
            ),
            (
                Version("18.1"),
                "https://www.intel.com/content/www/us/en/software-kit/665988/intel-quartus-prime-lite-edition-design-software-version-18-1-for-linux.html",
            ),
            (
                Version("18.0"),
                "https://www.intel.com/content/www/us/en/software-kit/667188/intel-quartus-prime-lite-edition-design-software-version-18-0-for-linux.html",
            ),
            (
                Version("17.1"),
                "https://www.intel.com/content/www/us/en/software-kit/669440/intel-quartus-prime-lite-edition-design-software-version-17-1-for-linux.html",
            ),
            (
                Version("17.0"),
                "https://www.intel.com/content/www/us/en/software-kit/669553/intel-quartus-prime-lite-edition-design-software-version-17-0-for-linux.html",
            ),
        ],
    ),
]

retry_kwargs = {
    "stop": tenacity.stop_after_attempt(5),
    "wait": tenacity.wait_exponential(min=15, max=60),
}


def init() -> tuple[mechanize.Browser, requests.Session]:
    br = mechanize.Browser()
    br.set_handle_robots(False)
    br.set_header(
        "User-Agent",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.1 Safari/605.1.15",
    )
    session = requests.Session()
    # proxies = {"http": "http://localhost:8888", "https": "http://localhost:8888"}
    # br.set_proxies(proxies)
    # br.set_ca_data("charles.pem")
    # session.proxies = proxies
    # session.verify = "charles.pem"

    # logger = logging.getLogger("mechanize")
    # logger.addHandler(logging.StreamHandler(sys.stdout))
    # logger.setLevel(logging.DEBUG)
    # http.client.HTTPConnection.debuglevel = 5
    return br, session


def login(br):
    br.open("https://signin.intel.com/")
    br.select_form(nr=0)
    br["UserID"] = os.environ["INTEL_USER"]
    br["Password"] = os.environ["INTEL_PASS"]
    br.submit()
    assert br.geturl() == "https://www.intel.com/content/www/us/en/homepage.html"
    html = lxml.html.fromstring(br.response().get_data().decode("utf-8"))
    assert len(html.xpath("//span[@id='logged-in-scenario']")) == 1


# @tenacity.retry(**retry_kwargs)
def get_dist_link_info(dl_page_url: str, br: mechanize.Browser) -> list[DistInfo]:
    print(f"opening dl link url {dl_page_url}")
    br.open(dl_page_url)
    url = br.geturl()
    print(f"actual dl link url: {url}")
    if "homepage.html?ref=" in url:
        print(f"got a redirect to home")
        raise ValueError(f"got a redirect to home")
    if "Pro" in br.title():
        edition = "pro"
    elif "Standard" in br.title():
        edition = "standard"
    elif "Lite" in br.title():
        edition = "lite"
    else:
        print(f"unknown edition for '{br.title()}'")
        raise ValueError(f"unknown edition for '{br.title()}'")
    if "Windows" in br.title():
        operating_system = "windows"
    elif "Linux" in br.title():
        operating_system = "linux"
    else:
        print(f"unknown os for '{br.title()}'")
        raise ValueError(f"unknown os for '{br.title()}'")
    html = lxml.html.fromstring(br.response().get_data().decode("utf-8"))
    version_select = html.xpath(f"//select[@id='version-driver-select']")[0]
    ver_urls = []
    for ver_opt in version_select:
        ver_str = ver_opt.text.removesuffix(" (Latest)")
        ver = Version(ver_str)
        url = "https://www.intel.com" + ver_opt.attrib["value"]
        ver_urls.append((ver, url))
    return DistInfo(edition=edition, operating_system=operating_system, dl_page_urls=ver_urls)


def get_dist_infos(br) -> list[DistInfo]:
    br.open(landing_url)
    dist_infos = []
    dl_links = [lnk.absolute_url for lnk in br.links() if lnk.text.startswith("Download for")]
    for dl_link in dl_links:
        dist_infos.append(get_dist_link_info(dl_link))
    return dist_infos


def xp_contains(attrib: str, val: str) -> str:
    return f"contains(concat(' ',normalize-space(@{attrib}),' '),' {val} ')"


def byte_size(size_str: str) -> int:
    sz, unit = size_str.split()
    sz = float(sz)
    unit = unit.lower()
    if unit == "kb":
        sz *= 1024
    elif unit == "mb":
        sz *= 1024 * 1024
    elif unit == "gb":
        sz *= 1024 * 1024 * 1024
    return int(sz)


@static_vars(cookies=None)
@tenacity.retry(**retry_kwargs)
def get_cdn_url(session, url: str) -> str:
    f = get_cdn_url
    if f.cookies is None:
        expired = True
    else:
        expired = False
        for c in f.cookies:
            expired |= c.is_expired(time.time() - 60)
    if expired:
        r = session.head(url, allow_redirects=True)
        f.cookies = CookieJar()
        for c in r.cookies:
            f.cookies.set_cookie(c)

    print(f"get_cdn_url: {url}")
    url_eula = url.replace("getContent", "acceptEula")
    session.get(url_eula, cookies=f.cookies, allow_redirects=True)
    r = session.head(url, cookies=f.cookies, allow_redirects=True)
    print(f"url: {url} cdn url: {r.url}")
    assert "downloads.intel.com/akdlm" in r.url
    return r.url


def get_download_no_cdn_url(dl_div, operating_system, edition) -> Download:
    dl_butt = dl_div.xpath(".//button[@data-direct-path or @data-href]")[0]
    dist_url = dl_butt.attrib["data-href"]
    dl_str, fname = dl_butt.text_content().split()
    assert dl_str == "Download"
    details_elem = dl_div.xpath(
        f".//li[{xp_contains('class', 'kit-detail-detailed-package__list-detail')}]"
    )
    details = dict(
        map(lambda e: re.sub("\s+", " ", e.text_content()).strip().split(": "), details_elem)
    )
    sha1_str = details["sha1"].lower()
    assert len(sha1_str) == 40
    ident = int(details["ID"])
    version = Version(details["Version"])
    m, d, y = map(int, details["Last Updated"].split("/"))
    updated_date = datetime.date(y, m, d)
    sz = byte_size(details["Size"].replace(",", ""))
    return Download(
        fname,
        dist_url,
        None,
        sha1_str,
        version,
        ident,
        updated_date,
        sz,
        operating_system,
        edition,
    )


def get_download(dl: Download, session) -> Download:
    dl.cdn_url = get_cdn_url(session, dl.dist_url)
    return dl


# @tenacity.retry(**retry_kwargs)
def get_downloads_no_cdn_url(dl_page_url: str, br, session) -> list[Download]:
    print(f"get_downloads: {dl_page_url}")
    dls = []
    br.open(dl_page_url + "?")  # ? prevents infinite redirect
    html = lxml.html.fromstring(br.response().get_data().decode("utf-8"))
    if "Pro" in br.title():
        edition = "pro"
    elif "Standard" in br.title():
        edition = "standard"
    elif "Lite" in br.title():
        edition = "lite"
    dl_divs = html.xpath(
        f".//div[{xp_contains('class', 'kit-detail-detailed-package__downloads')}]"
    )
    # mpfr windows pro 22.2 doesn't list OS
    if "Windows" in br.title():
        operating_system = "windows"
    elif "Linux" in br.title():
        operating_system = "linux"
    return list(map(lambda div: get_download_no_cdn_url(div, operating_system, edition), dl_divs))


def get_dist_downloads(dist: DistInfo, br, session, pool) -> dict[Version, Download]:
    dls = {}
    for ver, url in dist.dl_page_urls:
        dls[ver] = get_downloads(url, br, session, pool)
    return dls


def main(pool):
    br, session = init()
    login(br)

    # dist_infos = get_dist_infos(br)
    dist_infos = static_dist_infos
    # print(dist_infos)
    with open("dist_infos.txt", "w") as f:
        print(dist_infos, file=f)

    num_dist_vers = sum(len(di.dl_page_urls) for di in dist_infos)

    if False:
        dls_no_cdn_url = []
        for dist_info in dist_infos:
            for ver, dist_url in dist_info.dl_page_urls:
                dls_no_cdn_url.append(get_downloads_no_cdn_url(dist_url, br, session))
                # pass

        with open("downloads_no_cdn_url.txt", "w") as f:
            print(dls_no_cdn_url, file=f)
        pickle.dump(dls_no_cdn_url, open("downloads_no_cdn_url.pickle", "wb"))
    else:
        dls_no_cdn_url = pickle.load(open("downloads_no_cdn_url.pickle", "rb"))
    print(dls_no_cdn_url)

    # dist = next(i for i in dist_infos if i.edition == "pro" and i.operating_system == "windows")
    # dls_no_cdn_url = get_downloads_no_cdn_url("https://www.intel.com/content/www/us/en/software-kit/661713/intel-quartus-prime-pro-edition-design-software-version-19-2-for-windows.html", br, session)
    # print(dls_no_cdn_url)
    # with open("downloads_no_cdn_url.txt", "w") as f:
    #     print(dls_no_cdn_url, file=f)


if __name__ == "__main__":
    # freeze_support()
    pool = Pool(10)
    main(pool)
