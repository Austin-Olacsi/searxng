# SPDX-License-Identifier: AGPL-3.0-or-later
# lint: pylint
"""Yandex (Web, images, videos)"""

import re
from urllib.parse import urlencode, urlparse, parse_qs
from lxml import html
from html import unescape
from searx import logger
from searx import utils
from searx.exceptions import SearxEngineCaptchaException
from datetime import datetime

# about
about = {
    "website": 'https://yandex.com/',
    "wikidata_id": 'Q5281',
    "official_api_documentation": "?",
    "use_official_api": False,
    "require_api_key": False,
    "results": 'HTML',
}

url_xpath = "//a[@class='b-serp-item__title-link']/@href"
title_xpath = "//h3[@class='b-serp-item__title']/a[@class='b-serp-item__title-link']/span"
#            title_texts = [html_data.xpath("normalize-space(.)") for title in titles] #GIVES CORRECT TITLES!
#content_xpath = "//div[@class='b-serp-item__content']//div[@class='b-serp-item__text']"
content_xpath = "//div[@class='b-serp-item__content']//div[@class='b-serp-item__text']"


# engine dependent config
categories = ['general', 'images', 'videos']
paging = True

# search-url
base_url_web = 'https://yandex.com/search/site/'
base_url_images = 'https://yandex.com/images/search'
base_url_videos = 'https://yandex.com/video/search'

url_extension = 'tmpl_version=releases%2Ffrontend%2Fvideo%2Fv1.1168.0%238d942de0f4ebc4eb6b8f3c24ffbd1f8dbc5bbe63'

images_request_block = '{"blocks":[{"block":"extra-content","params":{},"version":2},{"block":"i-global__params:ajax","params":{},"version":2},{"block":"search2:ajax","params":{},"version":2},{"block":"preview__isWallpaper","params":{},"version":2},{"block":"content_type_search","params":{},"version":2},{"block":"serp-controller","params":{},"version":2},{"block":"cookies_ajax","params":{},"version":2},{"block":"advanced-search-block","params":{},"version":2}],"metadata":{"bundles":{"lb":"AS?(E<X120"},"assets":{"las":"justifier-height=1;justifier-setheight=1;fitimages-height=1;justifier-fitincuts=1;react-with-dom=1;"},"extraContent":{"names":["i-react-ajax-adapter"]}}}'

videos_request_block = '{"blocks":[{"block":"extra-content","params":{},"version":2},{"block":"i-global__params:ajax","params":{},"version":2},{"block":"search2:ajax","params":{},"version":2},{"block":"vital-incut","params":{},"version":2},{"block":"content_type_search","params":{},"version":2},{"block":"serp-controller","params":{},"version":2},{"block":"cookies_ajax","params":{},"version":2}],"metadata":{"bundles":{"lb":"^G]!q<X120"},"assets":{"las":"react-with-dom=1;185.0=1;73.0=1;145.0=1;5a502a.0=1;32c342.0=1;b84ac8.0=1"},"extraContent":{"names":["i-react-ajax-adapter"]}}}'


def request(query, params):
    query_params_web = {
        "text": query,
        "web": "1",
        "frame": "1",
        "searchid": "3131712",
    }

    query_params_images = {
        "format": "json",
        "request": images_request_block,
        "text": query,
        "uinfo": "sw-1920-sh-1080-ww-1125-wh-999",
    }

    query_params_videos = {
        "format": "json",
        "request": videos_request_block,
        "text": query,
    }

    if params['pageno'] > 1:
        query_params_web.update({"p": params["pageno"] - 1, "lr": "21180"})
        query_params_images.update({"p": params["pageno"] - 1})
        query_params_videos.update({"p": params["pageno"] - 1})

    params['method'] = 'GET'
    params['headers']['accept'] = 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8'
    params['headers']['accept-encoding'] = 'gzip'
    params['headers']['accept-language'] = 'en-US,en;q=0.5'
    params['headers']['dnt'] = '1'
    params['headers']['referer'] = 'https://yandex.com/images/search'
    params['headers']['connection'] = 'keep-alive'
    params['headers']['upgrade-insecure-requests'] = '1'
    params['headers']['sec-fetch-dest'] = 'document'
    params['headers']['sec-fetch-mode'] = 'navigate'
    params['headers']['sec-fetch-site'] = 'cross-site'
    params["cookies"] = {'cookie': "yp=1716337604.sp.family%3A1#1685406411.szm.1:1920x1080:1920x999"}

    if yandex_category == 'web':
        params['url'] = f"{base_url_web}?{urlencode(query_params_web)}"
#        params['url'] = f"https://yandex.com/search/?text=apple&lr=21180&search_source=yacom_desktop_common"
    elif yandex_category == 'images':
        params['url'] = f"{base_url_images}?{url_extension}{urlencode(query_params_images)}"
    elif yandex_category == 'videos':
        params['url'] = f"{base_url_videos}?{url_extension}{urlencode(query_params_videos)}"

    return params


def get_youtube_iframe_src(url):
    parsed_url = urlparse(url)

    # Check for http://www.youtube.com/v/videoid format
    if (
        parsed_url.netloc.endswith('youtube.com')
        and parsed_url.path.startswith('/v/')
        and len(parsed_url.path.split('/')) == 3
    ):
        video_id = parsed_url.path.split('/')[-1]
        return 'https://www.youtube-nocookie.com/embed/' + video_id

    # Check for http://www.youtube.com/watch?v=videoid format
    elif parsed_url.netloc.endswith('youtube.com') and parsed_url.path == '/watch' and parsed_url.query:
        video_id = parse_qs(parsed_url.query).get('v', [])
        if video_id:
            return 'https://www.youtube-nocookie.com/embed/' + video_id[0]



# engine dependent config
categories = ['general', 'images', 'videos']
paging = True

def response(resp):
    if yandex_category == 'web':
        if (resp.url).path.startswith('/showcaptcha'):
            raise SearxEngineCaptchaException()

        dom = html.fromstring(resp.text)
        results_dom = dom.xpath('//li[contains(@class, "serp-item")]')

        results = []
        for result_dom in results_dom:
            urls = result_dom.xpath(url_xpath)
            titles = result_dom.xpath(title_xpath)
            contents = result_dom.xpath(content_xpath)

            title_texts = [title.xpath("normalize-space(.)") for title in titles]
            content_texts = [content.xpath("normalize-space(.)") for content in contents]

            for url, title_text, content_text in zip(urls, title_texts, content_texts):
                results.append({
                    "url": url,
                    "title": title_text,
                    "content": content_text,
                })

        return results

    elif yandex_category == 'images':
        if (resp.url).path.startswith('/showcaptcha'):
            raise SearxEngineCaptchaException()

        html_data = html.fromstring(resp.text)
        #response is encoded, we decode the html first
        #NOTE: the json_resp from the ask and brave images/videos engines is ENCODED, maybe we should use like that???
        html_sample = unescape(html.tostring(html_data, encoding='unicode'))

        start_tag = 'data-state="'
        end_tag = '"advRsyaSearchColumn":null}}"'

        start_pos = html_sample.find(start_tag)
        start_pos += len(start_tag)

        end_pos = html_sample.find(end_tag, start_pos)
        end_pos += len(end_tag) - 1

        content_between_tags = html_sample[start_pos:end_pos]

        json_resp = utils.js_variable_to_python(content_between_tags)

        print(json_resp)

        results = []
        for result in json_resp['serpList']['items']['entities']:
            url = entity_data['url']
            print(url)

            results.append({
#                "title": title,
                "url": url,
#                "img_src": url,
#                "thumbnail_src": url,
#                "template": "images.html",
            })

        return results

    elif yandex_category == 'videos':
        if (resp.url).path.startswith('/showcaptcha'):
            raise SearxEngineCaptchaException()

        html_data = html.fromstring(resp.text)
        text = unescape(html.tostring(html_data, encoding='unicode'))

        results = []
        for result in html_data.xpath('//li[contains(@class, "video")]'):
            url = result.xpath('.//a[contains(@class, "serp-item__title-link")]/@href')[0]
            title = result.xpath('.//h2[contains(@class, "video__title")]/text()')[0]
            description = result.xpath('.//div[contains(@class, "video__snippet")]/text()')[0]
            author = result.xpath('.//div[contains(@class, "video__channel")]/text()')[0]
            raw_date = result.xpath('.//div[contains(@class, "video__date")]/text()')[0]
            duration = result.xpath('.//div[contains(@class, "video__duration")]/text()')[0]
            thumbnail = result.xpath('.//img[contains(@class, "thumb__image")]/@src')[0]

            date_timestamp = datetime.strptime(raw_date.split("T")[0], "%Y-%m-%d")
            date_utc = datetime.utcfromtimestamp(date_timestamp.timestamp())

            results.append({
                "url": url,
                "title": title,
                "content": description,
                "author": author,
                "publishedDate": date_utc,
                "length": duration,
                "thumbnail": thumbnail,
                "template": "videos.html",
            })

        return results

