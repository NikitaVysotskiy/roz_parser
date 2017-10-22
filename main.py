import csv
import time
import re
import requests


from bs4 import BeautifulSoup
from collections import namedtuple
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException


def load_all_data(url, driver):
    driver.get(url)
    print('Received page into driver')
    soup = BeautifulSoup(driver.page_source, 'lxml')
    page_count_tag = soup.select('ul[name=paginator] li')
    if page_count_tag:
        page_count = int(page_count_tag[-1]['id'].replace('page', ''))
    else:
        page_count = 0
    for i in range(1, page_count + 2):
        try:
            load_more_button = driver.find_element_by_css_selector('div.g-i-tile.g-i-tile-catalog.preloader-trigger')
            load_more_button.click()
            time.sleep(4)
        except NoSuchElementException:
            print('Button "load more" not found. Continue...')

        print('Loading page {} of {}'.format(i, page_count))

    page_src = driver.page_source
    # driver.close()
    return page_src


def get_items_html(soup, selector='.g-i-tile.g-i-tile-catalog'):
    return soup.select(selector)


def get_details_links(soup):
    items = get_items_html(soup)
    print('Total number:', len(items))
    selector = '.g-i-tile-i-title a'
    links = []
    for item_src in items:
        title = item_src.select(selector)
        if title:
            links.append(title[0]['href'])
    return links


def parse_characteristics(driver=None, soup=None):
    if driver:
        tab = driver.find_element_by_css_selector('li.m-tabs-i[name="characteristics"]')
        tab.click()
        time.sleep(1)
        soup = BeautifulSoup(driver.page_source, 'lxml')
    elif not soup:
        return {}
    trs = soup.select('table.chars-t tr')
    description = {}
    for tr in trs:
        if not tr.select('td[class$="empty"]') and len(tr.select('td')) == 2:
            key_tag = tr.select('td.chars-t-cell .chars-title')[0]
            inner = key_tag.select('.glossary-term')
            key = inner[0].text if inner else key_tag.text

            value_tag = tr.select('td.chars-t-cell .chars-value')[0]
            inner = value_tag.select('.glossary-term')
            value = inner[0].text if inner else value_tag.text

            description[key.strip()] = value.strip()
    return description


def parse_tag(soup, selector, attr=''):
    tags = soup.select(selector)
    if tags:
        if isinstance(tags, list):
            if attr:
                return tags[0][attr]
            else:
                return tags[0].text.strip()
        else:
            return tags.text
    else:
        return ''


def get_price(soup, selector):
    # may be missing as it's dynamically loaded on frontend, use driver
    price = parse_tag(soup, selector).replace(' ', '')
    if not price:
        price = parse_tag(soup, '.g-kit-i-1 .g-price').replace(' ', '')[:-4]
    return price


def parse_details(details_links, driver=None, file_name='output.csv'):
    selectors = {'title': '.detail-title-code h1.detail-title',
                 'image_src': '#basic_image img',
                 'promo_text': '.detail-promo-title a',
                 'price': '#price_label',
                 }
    with open(file_name, 'w') as output_file:
        # not using selectors.keys() as 2nd param, 'cause it doesn't saves order
        dict_writer = csv.DictWriter(output_file, ['title', 'image_src', 'price', 'characteristics'])
        dict_writer.writeheader()
        for i, link in enumerate(details_links):
            current_item = {}
            print('-' * 50)
            print('Parsing {} of {}'.format(i + 1, len(details_links)))
            t1 = time.time()
            if driver:
                driver.get(link)
                soup = BeautifulSoup(driver.page_source, 'lxml')
                print('Request via driver took: ', time.time() - t1)
            else:
                soup = BeautifulSoup(requests.get(link).content, 'lxml')
                print('Request took: ', time.time() - t1)
                time.sleep(0.5)
            current_item['title'] = parse_tag(soup, selectors['title'])
            current_item['image_src'] = parse_tag(soup, selectors['image_src'], 'src')
            current_item['price'] = get_price(soup, selectors['price'])
            current_item['characteristics'] = parse_characteristics(soup=soup)
            dict_writer.writerow(current_item)


def test_output(file_name="output.csv"):
    with open(file_name, newline="") as infile:
        print('Output file has: {} lines'.format(len(infile.readlines()) - 1))
        # reader = csv.reader(infile)
        # Item = namedtuple('Item', next(reader))
        # for data in map(Item._make, reader):
        #     print(data)


def main():
    driver = webdriver.PhantomJS()
    print('Driver initialized')

    base_url = 'https://rozetka.com.ua/'
    category_path = 'mobile-phones/c80003/'
    params = 'preset=smartfon;view=tile'

    print('Getting dynamically loaded content...')
    page_src = load_all_data(base_url + category_path + params, driver)
    soup = BeautifulSoup(page_src, 'lxml')

    print('Getting items links...')
    details_links = get_details_links(soup)

    # if driver is used, request takes more time, but all data is loaded
    parse_details(details_links)  # , driver)

    test_output()


if __name__ == '__main__':
    main()
