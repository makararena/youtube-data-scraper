from __future__ import print_function

import json
import re
import time

YOUTUBE_VIDEO_URL = 'https://www.youtube.com/watch?v={youtube_id}'

SORT_BY_POPULAR = 0
SORT_BY_RECENT = 1

# Allow importing repo-root `shared/` when running from this subproject.
import os
import sys

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from shared.youtube import (  # type: ignore  # noqa: E402
    extract_ytcfg,
    extract_ytinitialdata,
    fetch_html,
    inertube_ajax_request,
    make_session,
    search_dict,
)


class YoutubeCommentDownloader:

    def __init__(self):
        self.session = make_session()

    def ajax_request(self, endpoint, ytcfg, retries=5, sleep=20, timeout=60):
        return inertube_ajax_request(
            self.session, endpoint, ytcfg, retries=retries, sleep=float(sleep), timeout=timeout
        )

    def get_comments(self, youtube_id, *args, **kwargs):
        return self.get_comments_from_url(YOUTUBE_VIDEO_URL.format(youtube_id=youtube_id), *args, **kwargs)

    def get_comments_from_url(self, youtube_url, sort_by=SORT_BY_RECENT, language=None, sleep=.1):
        html, _final_url = fetch_html(self.session, youtube_url, timeout=30)
        ytcfg = extract_ytcfg(html)
        if language:
            ytcfg['INNERTUBE_CONTEXT']['client']['hl'] = language

        data = extract_ytinitialdata(html)

        item_section = next(search_dict(data, 'itemSectionRenderer'), None)
        renderer = next(search_dict(item_section, 'continuationItemRenderer'), None) if item_section else None
        if not renderer:
            # Comments disabled?
            return

        sort_menu = next(search_dict(data, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
        if not sort_menu:
            # No sort menu. Maybe this is a request for community posts?
            section_list = next(search_dict(data, 'sectionListRenderer'), {})
            continuations = list(search_dict(section_list, 'continuationEndpoint'))
            # Retry..
            data = self.ajax_request(continuations[0], ytcfg) if continuations else {}
            sort_menu = next(search_dict(data, 'sortFilterSubMenuRenderer'), {}).get('subMenuItems', [])
        if not sort_menu or sort_by >= len(sort_menu):
            raise RuntimeError('Failed to set sorting')
        continuations = [sort_menu[sort_by]['serviceEndpoint']]

        while continuations:
            continuation = continuations.pop()
            response = self.ajax_request(continuation, ytcfg)

            if not response:
                break

            error = next(search_dict(response, 'externalErrorMessage'), None)
            if error:
                raise RuntimeError('Error returned from server: ' + error)

            actions = list(search_dict(response, 'reloadContinuationItemsCommand')) + \
                      list(search_dict(response, 'appendContinuationItemsAction'))
            for action in actions:
                for item in action.get('continuationItems', []):
                    if action['targetId'] in ['comments-section',
                                              'engagement-panel-comments-section',
                                              'shorts-engagement-panel-comments-section']:
                        # Process continuations for comments and replies.
                        continuations[:0] = [ep for ep in search_dict(item, 'continuationEndpoint')]
                    if action['targetId'].startswith('comment-replies-item') and 'continuationItemRenderer' in item:
                        # Process the 'Show more replies' button
                        continuations.append(next(search_dict(item, 'buttonRenderer'))['command'])

            toolbar_payloads = search_dict(response, 'engagementToolbarStateEntityPayload')
            toolbar_states = {payload['key']: payload for payload in toolbar_payloads}
            for comment in reversed(list(search_dict(response, 'commentEntityPayload'))):
                properties = comment['properties']
                cid = properties['commentId']
                author = comment['author']
                toolbar = comment['toolbar']
                toolbar_state = toolbar_states[properties['toolbarStateKey']]
                result = {'cid': cid,
                          'text': properties['content']['content'],
                          'time': properties['publishedTime'],
                          'author': author['displayName'],
                          'channel': author['channelId'],
                          'votes': toolbar['likeCountNotliked'].strip() or "0",
                          'replies': toolbar['replyCount'],
                          'photo': author['avatarThumbnailUrl'],
                          'heart': toolbar_state.get('heartState', '') == 'TOOLBAR_HEART_STATE_HEARTED',
                          'reply': '.' in cid}

                yield result
            time.sleep(sleep)

    # NOTE: shared.youtube.search_dict is used; do not re-implement here.
