# coding: utf-8
from __future__ import unicode_literals

import re

from .common import InfoExtractor
from ..compat import compat_urllib_parse_urlparse
from ..utils import (
    int_or_none,
    mimetype2ext,
    remove_end,
    url_or_none,
    urlencode_postdata,
    sanitized_Request,
)


class IwaraIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/videos/(?P<id>[a-zA-Z0-9]+)'
    _LOGIN_URL = 'https://iwara.tv/user/login'
    _NETRC_MACHINE = 'iwara'
    _TESTS = [{
        'url': 'http://iwara.tv/videos/amVwUl1EHpAD9RD',
        # md5 is unstable
        'info_dict': {
            'id': 'amVwUl1EHpAD9RD',
            'ext': 'mp4',
            'title': '【MMD R-18】ガールフレンド carry_me_off',
            'age_limit': 18,
        },
    }, {
        'url': 'http://ecchi.iwara.tv/videos/Vb4yf2yZspkzkBO',
        'md5': '7e5f1f359cd51a027ba4a7b7710a50f0',
        'info_dict': {
            'id': '0B1LvuHnL-sRFNXB1WHNqbGw4SXc',
            'ext': 'mp4',
            'title': '[3D Hentai] Kyonyu × Genkai × Emaki Shinobi Girls.mp4',
            'age_limit': 18,
        },
        'add_ie': ['GoogleDrive'],
        'skip': 'This video is unavailable',
    }, {
        'url': 'http://www.iwara.tv/videos/nawkaumd6ilezzgq',
        # md5 is unstable
        'info_dict': {
            'id': '6liAP9s2Ojc',
            'ext': 'mp4',
            'age_limit': 18,
            'title': '[MMD] Do It Again Ver.2 [1080p 60FPS] (Motion,Camera,Wav+DL)',
            'description': 'md5:590c12c0df1443d833fbebe05da8c47a',
            'upload_date': '20160910',
            'uploader': 'aMMDsork',
            'uploader_id': 'UCVOFyOSCyFkXTYYHITtqB7A',
        },
        'add_ie': ['Youtube'],
    }, {
        'url': 'https://ecchi.iwara.tv/videos/aeqwwtzqbdc79zrxk',
        'info_dict': {
            'id': 'aeqwwtzqbdc79zrxk',
            'ext': 'mp4',
            'title': 'Come And Get it【時崎狂三with紳士ハンド】ツインテ差分',
            'age_limit': 18,
        },
        'skip': 'This video is private',
    }]


    def _login(self):
        username, password = self._get_login_info()
        # No authentication to be performed
        if not username or not password:
            return

        self.report_login()

        login_form = {
            'name': username,
            'pass': password,
            'form_id': 'user_login'
        }


        payload = urlencode_postdata(login_form)
        request = sanitized_Request(self._LOGIN_URL, payload)
        login_page = self._download_webpage(
            request, None, errnote='Unable to perform login request', fatal=False)

        if not re.search(r'href=\"/user/logout\"', login_page):
            self.report_warning('Login failed: bad username or password')


    def _real_initialize(self):
        self._login()

    def _real_extract(self, url):
        video_id = self._match_id(url)

        webpage, urlh = self._download_webpage_handle(url, video_id)

        hostname = compat_urllib_parse_urlparse(urlh.geturl()).hostname
        # ecchi is 'sexy' in Japanese
        age_limit = 18 if hostname.split('.')[0] == 'ecchi' else 0

        video_data = self._download_json('http://www.iwara.tv/api/video/%s' % video_id, video_id)

        if not video_data:
            iframe_url = self._html_search_regex(
                r'<iframe[^>]+src=([\'"])(?P<url>[^\'"]+)\1',
                webpage, 'iframe URL', group='url')
            return {
                '_type': 'url_transparent',
                'url': iframe_url,
                'age_limit': age_limit,
            }

        title = remove_end(self._html_search_regex(
            r'<title>([^<]+)</title>', webpage, 'title'), ' | Iwara')

        formats = []
        for a_format in video_data:
            format_uri = url_or_none(a_format.get('uri'))
            if not format_uri:
                continue
            format_id = a_format.get('resolution')
            height = int_or_none(self._search_regex(
                r'(\d+)p', format_id, 'height', default=None))
            formats.append({
                'url': self._proto_relative_url(format_uri, 'https:'),
                'format_id': format_id,
                'ext': mimetype2ext(a_format.get('mime')) or 'mp4',
                'height': height,
                'width': int_or_none(height / 9.0 * 16.0 if height else None),
                'quality': 1 if format_id == 'Source' else 0,
            })

        self._sort_formats(formats)

        return {
            'id': video_id,
            'title': title,
            'age_limit': age_limit,
            'formats': formats,
        }


class IwaraPlaylistIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/playlist/(?P<id>[^\s\\]+)'

    _TEST = {
        'url': 'https://ecchi.iwara.tv/playlist/testplaylist',
        'info_dict': {
            'id': 'testplaylist',
            # Unique shortlink
            'display_id': '707704',
            'title': 'TestPlaylist',
            'uploader': 'iwaratestaccount',
            'uploader_id': '860558',
        },
        'playlist_count': 2,
    }

    def _real_extract(self, url):
        playlist_id = self._match_id(url)
        webpage = self._download_webpage(url, playlist_id)

        # For lack of API, extract playlist information directly from webpage
        short_id = self._html_search_regex(r'/node/(\d+)', webpage, 'short_id')
        username = self._html_search_regex(r'views-field-name.*<h2>(.+)</h2>', webpage, 'username')
        user_id = self._html_search_regex(r'data-uid=\"(\d+)\"', webpage, 'user_id')
        title = self._html_search_regex(r'<title>(.+?) \| Iwara</title>', webpage, 'title')

        entries = [{
            '_type': 'url',
            'ie_key': IwaraIE.ie_key(),
            'id': entry_info.group('id'),
            'title': entry_info.group('video_title'),
            'url': ('https://www.iwara.tv/videos/%s' % entry_info.group('id')),
        } for entry_info in re.finditer(
            r'<h3 class=\"title\">\s*.*videos\/(?P<id>\w+).+?\>(?P<video_title>.*)</a></h3>',
            webpage)]

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'display_id': short_id,
            'title': title,
            'uploader': username,
            'uploader_id': user_id,
            'entries': entries,
        }


class IwaraFavoritesIE(InfoExtractor):
    _VALID_URL = r'https?://(?:www\.|ecchi\.)?iwara\.tv/user/liked'
    _NETRC_MACHINE = 'iwara'
    _LOGIN_URL = 'https://iwara.tv/user/login'

    def _real_initialize(self):
        IwaraIE._login(self)

    def _real_extract(self, url):
        playlist_id = 'Liked Videos'
        webpage = self._download_webpage(url, playlist_id)

        if not re.search(r'href=\"/user/logout\"', webpage):
            self.raise_login_required('You must be logged-in to access Liked videos')

        username, password = IwaraIE._get_login_info(self)
        user_id = self._html_search_regex(r'/user/(\d+)/playlists', webpage, 'user_id')

        entries = [{
            '_type': 'url',
            'ie_key': IwaraIE.ie_key(),
            'id': entry_info.group('id'),
            'title': entry_info.group('video_title'),
            'url': ('https://www.iwara.tv/videos/%s' % entry_info.group('id')),
        } for entry_info in re.finditer(
            r'<h3 class=\"title\">\s*.*videos\/(?P<id>\w+).+?\>(?P<video_title>.*)</a></h3>',
            webpage)]

        return {
            '_type': 'playlist',
            'id': playlist_id,
            'title': username + '\'s Liked Videos',
            'uploader': username,
            'uploader_id': user_id,
            'entries': entries,
        }
