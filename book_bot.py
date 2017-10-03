# -*- coding: utf-8 -*-
# __author__ = "Zhassulan Zhussupov"
# __copyright__ = "Copyright (c) 2017 Zhassulan Zhussupov"

import requests
import urllib
import urllib.parse
import sys, os
import re

import asyncio
import logging

import lxml.html
from lxml import etree
from user_agent import generate_navigator

from optparse import OptionParser
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(name)s: %(levelname)s %(message)s')

usage = "%prog [options]\n\n"
usage += "Run book bot\n"
option_parser = OptionParser(usage=usage, version="%prog 1.0")
option_parser.add_option("-p", "--proxy", help = "proxy list file", default = './proxy_http_ip_1201.csv')
option_parser.add_option("-a", "--author", help = "author letter", default = "A")
option_parser.add_option('-d', "--dl", help = "download books or not", default = True)
(options, args) = option_parser.parse_args()

MAIN_URL = 'http://www.e-reading.club'
R_MAX_LOOP = 3

AUTHORS_XPATH = './/table//a[contains(@href, "bookbyauthor")]/@href'
BOOKS_XPATH = './/table[@class="booklist"]//div[contains(@class, "downloadhide")]/@id'

def get_page_proxy(url, proxy_ip = None, headers = {}, t = 0):
    if t == R_MAX_LOOP:
        return None

    t += 1
    logging.info("get page: %s" % url)

    try:
        headers['User-agent'] = generate_navigator(navigator="chrome")['user_agent']
        try:
            if proxy_ip:
                logging.info("set proxy ip: %s" % proxy_ip)
                proxies = {
                    'http': 'http://%s' % proxy_ip,
                    'https': 'https://%s' % proxy_ip,
                }
                r = requests.get(url, proxies = proxies, timeout = 3, headers = headers)
            else:
                r = requests.get(url, timeout = 3, headers = headers)
            r.encoding = 'utf-8'
            if r.status_code == 200:
                return r.text
        except requests.Timeout as e:
            logging.error("Timeout ex %s" % e)
            return get_page_proxy(url = url, proxy_ip = proxy_ip, headers = headers, t = t)
        except requests.ConnectionError as e:
            logging.error("conn err %s" % e)
            return get_page_proxy(url = url, proxy_ip = proxy_ip, headers = headers, t = t)
        else:
            logging.error("status code: %s, ip: %s (req)" % (r.status_code, proxy_ip))
            return None
    except Exception as e:
        logging.error("error get page by req: %s" % e)
    return None

# parse authors
def parse_authors(letter = "A"):
    authors = []
    letter = urllib.parse.quote(letter, safe ='')
    url = "%s/author.php?letter=%s" % (MAIN_URL, letter)
    authors_page = get_page_proxy(url = url)
    if authors_page:
        try:
            tree = lxml.html.fromstring(authors_page)
            author_ids = tree.xpath(AUTHORS_XPATH)
            if author_ids:
                authors = [re.sub("[^0-9]", "", a) for a in author_ids]
        except Exception as e:
            logging.error(e)
    return authors

# parse current author books by author id
async def parse_author_books(author_id):
    books = []
    url = "%s/bookbyauthor.php?author=%s" % (MAIN_URL, author_id)
    author_page = get_page_proxy(url = url)
    if author_page:
        try:
            tree = lxml.html.fromstring(author_page)
            book_ids = tree.xpath(BOOKS_XPATH)
            if book_ids:
                books = [re.sub("[^0-9]", "", b) for b in book_ids]
        except Exception as e:
            logging.error(e)
    return (author_id, books)

# download book by id
async def download_book(author_id, book_id):
    url = "%s/download.php?book=%s" % (MAIN_URL, book_id)
    filename = './books/author_%s/book_%s.zip' % (author_id, book_id)
    try:
        resp = urllib.request.urlopen(url)
        if resp.getcode()  == 200:
            if not os.path.exists(os.path.dirname(filename)):
                os.makedirs(os.path.dirname(filename))
            size = resp.headers.get('Content-Length')
            logging.info("Starting downloading book: %s. Size: %s bytes" % (url, size))
            f = open(filename, "wb")
            downloaded = 0
            block = 1024
            while True:
                buffer = resp.read(block)
                if not buffer:
                    break
                downloaded += len(buffer)
                f.write(buffer)
                p = float(downloaded) / int(size)
                status = r"{0}  [{1:.2%}]".format(downloaded, p)
                status = status + chr(8)*(len(status)+1)
                sys.stdout.write(status)
            f.close()
            logging.info("book %s: OK" % filename)
        else:
            logging.info("book %s: NOK. Server response code: %s" % (filename, resp.getcode()))
        resp.close()
    except Exception as e:
        logging.info("Cannot download book %s: NOK. error: %s" % (book_id, e))
    return filename

async def parse_books_authors(letter = "A"):
    authors = parse_authors(letter = letter)
    authors_cor = [parse_author_books(i) for i in authors]
    completed, pending = await asyncio.wait(authors_cor)
    author_books = []
    for i in completed:
        res = i.result()
        [author_books.append((res[0], j)) for j in res[1]]
    return author_books

async def download_books(books = []):
    books_cor = [download_book(author_id = i[0], book_id = i[1]) for i in books]
    completed, pending = await asyncio.wait(books_cor)
    books = []
    for i in completed:
        books.append(i.result())
    return books

if __name__ == '__main__':
    event_loop = asyncio.get_event_loop()
    try:
        books = event_loop.run_until_complete(parse_books_authors(letter = str(options.author)))
        files = event_loop.run_until_complete(download_books(books = books))
    finally:
        event_loop.close()
        print (files)
