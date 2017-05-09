import sys
import json
import time
from datetime import datetime
import urlparse
from urlparse import parse_qsl

from dateutil import tz
import requests
import m3u8

import xbmcgui
import xbmcplugin
import xbmcaddon


__url__ = sys.argv[0]
__handle__ = int(sys.argv[1])
__args__ = urlparse.parse_qs(sys.argv[2][1:])


LIVESTREAM_API = 'http://api.new.livestream.com'
NRL_STREAMS = 'https://livestream.com/nrl'
NRL_ACCOUNT_ID = '3161248'

UPCOMING_PER_PAGE = 15
PAST_PER_PAGE = 30

BERNEX_PROXY = 'http://proxy.bernex.net/'


HTTP_HEADERS = {'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Connection': 'keep-alive',
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.87 Safari/537.36',
                'Upgrade-Insecure-Requests': '1'}

# Create a session object to store cookies
session = requests.Session()


def livestream_api_request(url, proxy=False):
    if proxy:
        r = proxy_request(url)
    else:
        r = requests.get(url)

    json_obj = json.loads(r.text)
    return json_obj


def proxy_request(url):
    r = session.post(BERNEX_PROXY + '/index.php',
                     headers=HTTP_HEADERS,
                     data={'q': url,
                           'hl[include_form]': 'on',
                           'hl[remove_scripts]': 'on',
                           'hl[accept_cookies]': 'on',
                           'hl[show_images]': 'on',
                           'hl[show_referer]': 'on',
                           'hl[base64_encode]': 'on',
                           'hl[strip_meta]': 'on',
                           'hl[session_cookies]': 'on',
                           })
    return r


def grab_m3u8_master(event_id):
    url = '{0}/accounts/{1}/events/{2}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, event_id)

    streams = []
    r = proxy_request(url)
    js = json.loads(r.text)
    data = js['feed']['data']
    if len(data) > 0:
        for item in data:
            if item['type'] == 'video':
                streams.append(item['data']['m3u8_url'])

        return streams[0]
    else:
        return js['stream_info']['m3u8_url']


def list_events():
    url = '{0}/accounts/{1}/events?newer={2}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, 5)
    upcoming_events = livestream_api_request(url)

    listing = []
    for event in upcoming_events['data']:
        if event['in_progress']:
            list_item = xbmcgui.ListItem(event['full_name'] + ' [LIVE]')
            list_item.setProperty('IsPlayable', 'true')
            list_item.setProperty('IsFolder', 'false')
            list_item.setInfo('video', {'mediaType': 'video',
                                        'playcount': 0,
                                        'title': event['full_name'],
                                        'originaltitle': event['full_name']})
            list_item.setArt({'thumb': event['logo']['url'],
                              'poster': event['background_image']['url'],
                              'banner': event['background_image']['url'],
                              'fanart': event['background_image']['url']})

            url = '{0}?action=play&event_id={1}'.format(__url__, event['id'])
            listing.append((url, list_item, False))

    list_item = xbmcgui.ListItem('Upcoming Events')
    list_item.setInfo('video', {'title': 'Upcoming Events'})
    list_item.setProperty('IsFolder', 'true')
    url = '{0}?action=list_upcoming'.format(__url__)
    listing.append((url, list_item, True))

    list_item = xbmcgui.ListItem('Past Events')
    list_item.setInfo('video', {'title': 'Upcoming Events'})
    list_item.setProperty('IsFolder', 'true')
    url = '{0}?action=list_past'.format(__url__)
    listing.append((url, list_item, True))

    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)


def list_upcoming_events(event_id=None):
    if event_id:
        url = '{0}/accounts/{1}/events?id={2}&newer={3}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, event_id, UPCOMING_PER_PAGE)
    else:
        url = '{0}/accounts/{1}/events?newer={2}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, UPCOMING_PER_PAGE)

    upcoming_events = livestream_api_request(url)

    listing = []
    for event in upcoming_events['data'][::-1]:
        try:
            event_date = datetime.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except TypeError:
            event_date = datetime.fromtimestamp(time.mktime(time.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ')))

        event_date = event_date.replace(tzinfo=tz.tzutc())
        event_date = event_date.astimezone(tz.tzlocal())

        if event['in_progress']:
            list_item = xbmcgui.ListItem(event['full_name'] + ' [LIVE]')
            list_item.setProperty('IsPlayable', 'true')
        else:
            list_item = xbmcgui.ListItem(event['full_name'] + ' [%s]' % event_date.strftime('%a, %b %d @ %I:%M%p'))
            list_item.setProperty('IsPlayable', 'false')

        list_item.setInfo('video', {'mediaType': 'video',
                                    'playcount': 0,
                                    'title': event['full_name'],
                                    'originaltitle': event['full_name']})

        try:
            logo = event['logo']['url']
        except:
            logo = None

        try:
            bg_image = event['background_image']['url']
        except:
            bg_image = None

        list_item.setArt({'thumb': logo,
                          'poster': bg_image,
                          'banner': bg_image,
                          'fanart': bg_image})

        url = '{0}?action=play&event_id={1}'.format(__url__, event['id'])
        listing.append((url, list_item, False))

    if upcoming_events['after'] > 0:
        list_item = xbmcgui.ListItem('Next Page')
        list_item.setProperty('IsFolder', 'true')
        url = '{0}?action=list_upcoming&event_id={1}'.format(__url__, upcoming_events['data'][0]['id'])
        listing.append((url, list_item, True))

    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)


def list_past_events(event_id=None):
    if event_id:
        url = '{0}/accounts/{1}/events?id={2}&older={3}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, event_id, PAST_PER_PAGE)
    else:
        url = '{0}/accounts/{1}/events?older={2}'.format(LIVESTREAM_API, NRL_ACCOUNT_ID, PAST_PER_PAGE)

    past_events = livestream_api_request(url)

    listing = []
    for event in past_events['data']:
        try:
            event_date = datetime.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ')
        except TypeError:
            event_date = datetime.fromtimestamp(time.mktime(time.strptime(event['start_time'], '%Y-%m-%dT%H:%M:%S.%fZ')))

        event_date = event_date.replace(tzinfo=tz.tzutc())
        event_date = event_date.astimezone(tz.tzlocal())

        list_item = xbmcgui.ListItem(event['full_name'] + ' [%s]' % event_date.strftime('%A, %B %d'))
        list_item.setProperty('IsPlayable', 'true')
        list_item.setInfo('video', {'mediaType': 'video',
                                    'playcount': 0,
                                    'title': event['full_name'],
                                    'originaltitle': event['full_name']})

        try:
            logo = event['logo']['url']
        except:
            logo = None

        try:
            bg_image = event['background_image']['url']
        except:
            bg_image = None

        list_item.setArt({'thumb': logo,
                          'poster': bg_image,
                          'banner': bg_image,
                          'fanart': bg_image})

        url = '{0}?action=play&event_id={1}'.format(__url__, event['id'])
        listing.append((url, list_item, False))

    if past_events['before'] > 0:
        list_item = xbmcgui.ListItem('Next Page')
        list_item.setProperty('IsFolder', 'true')
        url = '{0}?action=list_past&event_id={1}'.format(__url__, past_events['data'][-1]['id'])
        listing.append((url, list_item, True))

    xbmcplugin.addDirectoryItems(__handle__, listing, len(listing))
    xbmcplugin.endOfDirectory(__handle__)


def play_stream(event_id):
    master_url = grab_m3u8_master(event_id)

    r = proxy_request(master_url)
    m3u8_obj = m3u8.loads(r.text)

    # Select the highest quality stream
    stream = max(m3u8_obj.playlists, key=lambda p: p.stream_info.bandwidth)

    item = xbmcgui.ListItem(path=stream.absolute_uri)
    xbmcplugin.setResolvedUrl(__handle__, True, listitem=item)


def router(paramstring):
    params = dict(parse_qsl(paramstring[1:]))

    if params:
        action = params.pop('action')

        if action == 'play':
            play_stream(params['event_id'])
        elif action == 'list_upcoming':
            list_upcoming_events(**params)
        elif action == 'list_past':
            list_past_events(**params)
    else:
        list_events()


if __name__ == '__main__':
    router(sys.argv[2])
