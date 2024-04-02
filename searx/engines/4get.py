# SPDX-License-Identifier: AGPL-3.0-or-later
# lint: pylint
"""4get (web, images, videos, music, news)"""

from urllib.parse import urlencode, urlparse, parse_qs
from datetime import datetime
from dateutil.relativedelta import relativedelta
from typing import Any
import time

# Engine metadata
about = {
    "website": 'https://4get.ca/',
    "wikidata_id": 'Q306956',
    "official_api_documentation": None,
    "use_official_api": False,
    "require_api_key": False,
    "results": 'JSON',
}

# Engine configuration
paging = True
base_url = Any
scraper = Any
search_type = Any
safesearch = True
time_range_support = True
safesearch_map = {0: 'maybe', 1: 'no', 2: 'no'}


def request(query, params):
    key = params['engine_data'].get('npt')

    query_params = {
        "s": query,
        "scraper": scraper,
        "country": "any",
        "nsfw": safesearch_map[params['safesearch']],
        "lang": "any",
    }

    if params['time_range']:
        date = (datetime.now() - relativedelta(**{f"{params['time_range']}s": 1})).strftime("%Y-%m-%d")
        query_params["newer"] = date

    if params['pageno'] > 1:
        params['url'] = f"{base_url}/api/v1/{search_type}?npt={key}"

    else:
        params["url"] = f"{base_url}/api/v1/{search_type}?{urlencode(query_params)}"

    return params


# Format the video duration
def format_duration(duration):
    seconds = int(duration)
    length = time.gmtime(seconds)
    if length.tm_hour:
        return time.strftime("%H:%M:%S", length)
    return time.strftime("%M:%S", length)


# get embedded youtube links
def _get_iframe_src(url):
    parsed_url = urlparse(url)
    if parsed_url.path == '/watch' and parsed_url.query:
        video_id = parse_qs(parsed_url.query).get('v', [])  # type: ignore
        if video_id:
            return 'https://www.youtube-nocookie.com/embed/' + video_id[0]  # type: ignore
    return None


def response(resp):
    results = []
    data = resp.json()

    try:
        results.append(
            {
                'engine_data': data["npt"],
                'key': "npt",
            }
        )
    except KeyError:
        # there are no more results
        results = None
        return results

    if search_type == 'web':
        for item in data["web"]:
            title = item["title"]
            description = item["description"]
            url = item["url"]
            unix_date = item.get("date")
            image = item["thumb"]["url"] or None
            formatted_date = None

            if unix_date is not None:
                formatted_date = datetime.utcfromtimestamp(unix_date)

            results.append(
                {
                    "title": title,
                    "url": url,
                    "content": description,
                    "publishedDate": formatted_date,
                    "img_src": image,
                }
            )

    elif search_type == 'images':
        for item in data["image"]:
            title = item["title"]
            url = item["url"]
            direct_link_fullsize = item["source"][0]["url"]
            source = item["url"]
            direct_link_preview = item["source"][-1]["url"]

            print(source)

            results.append(
                {
                    "title": title,
                    "url": direct_link_fullsize,
                    "img_src": direct_link_fullsize,
                    "thumbnail_src": direct_link_preview,
                    "source": source,
                    "template": "images.html",
                }
            )

    elif search_type == 'videos':
        for item in data["video"]:
            title = item["title"]
            url = item["url"]
            description = item["description"]
            thumbnail = item["thumb"]["url"]
            author = item["author"]["name"]
            unix_date = item["date"]
            duration = item["duration"]

            formatted_date = datetime.utcfromtimestamp(unix_date)
            formatted_duration = format_duration(duration)
            embedded_urls = _get_iframe_src(url)

            results.append(
                {
                    "url": url,
                    "title": title,
                    "content": description or "",
                    "author": author,
                    "publishedDate": formatted_date,
                    "length": formatted_duration,
                    "thumbnail": thumbnail,
                    "iframe_src": embedded_urls,
                    "template": "videos.html",
                }
            )

    elif search_type == 'news':
        for item in data["news"]:
            title = item["title"]
            description = item["description"]
            url = item["url"]
            author = item["author"]
            unix_date = item["date"]
            thumbnail = item["thumb"]["url"]

            formatted_date = datetime.utcfromtimestamp(unix_date)

            results.append(
                {
                    "title": title,
                    "url": url,
                    "content": description,
                    "author": author,
                    "publishedDate": formatted_date,
                    "img_src": thumbnail,
                }
            )

    else:
        print("Error: not finding things")

    return results
