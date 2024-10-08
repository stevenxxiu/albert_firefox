import configparser
import re
import shutil
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator, NamedTuple

from albert import (  # pylint: disable=import-error
    Action,
    Matcher,
    PluginInstance,
    StandardItem,
    TriggerQueryHandler,
    runDetachedProcess,
)


md_iid = '2.3'
md_version = '1.0'
md_name = 'Firefox'
md_description = 'Open Firefox bookmarks'
md_url = 'https://github.com/stevenxxiu/albert_firefox_steven'
md_maintainers = '@stevenxxiu'

ICON_URL = 'xdg:firefox-developer-edition'


class Bookmark(NamedTuple):
    name: str
    url: str


def get_profile_path() -> Path:
    """
    :return: path of the last selected profile if it was used, or the dev profile
    """
    firefox_data_path = Path.home() / '.mozilla/firefox/'
    profile = configparser.ConfigParser()
    profile.read(firefox_data_path / 'profiles.ini')

    last_used_profile = None
    dev_profile = None
    for key, obj in profile.items():
        if not re.match(r'Profile\d+', key):
            continue
        # `Default = 1` indicates the profile was last used. Dev profiles don't have the setting.
        if obj.get('Default', None) == '1':
            last_used_profile = obj['Path']
        elif obj['Name'].startswith('dev-edition-'):
            dev_profile = obj['Path']

    if last_used_profile and (firefox_data_path / 'places.sqlite').exists():
        return firefox_data_path / last_used_profile
    if dev_profile and (firefox_data_path / dev_profile / 'places.sqlite').exists():
        return firefox_data_path / dev_profile
    raise ValueError


@contextmanager
def open_places_db(profile_path: Path) -> Iterator[sqlite3.Connection]:
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = Path(temp_dir)
        shutil.copy(profile_path / 'places.sqlite', temp_dir)
        wal_path = profile_path / 'places.sqlite-wal'
        if wal_path.exists():
            shutil.copy(wal_path, temp_dir)

        with closing(sqlite3.connect(temp_dir / 'places.sqlite')) as con:
            yield con


def get_bookmarks(profile_path: Path) -> list[Bookmark]:
    with open_places_db(profile_path) as con:
        cur = con.cursor()

        # Ignore *Firefox* bookmarks menu official bookmarks
        cur.execute('SELECT id FROM moz_bookmarks WHERE title LIKE "Mozilla Firefox" AND fk IS NULL')
        ignored_folders = [res[0] for res in cur.fetchall()]

        # Empty bound parameters aren't allowed
        if not ignored_folders:
            ignored_folders = [-1]

        cur.execute(
            """
            SELECT moz_bookmarks.title, moz_places.url FROM moz_bookmarks
            INNER JOIN moz_places ON moz_bookmarks.fk=moz_places.id
            WHERE moz_bookmarks.fk is NOT NULL
            AND moz_bookmarks.parent NOT IN (?)
            """,
            ignored_folders,
        )
        return list(cur)


class Plugin(PluginInstance, TriggerQueryHandler):
    def __init__(self) -> None:
        TriggerQueryHandler.__init__(
            self, id=__name__, name=md_name, description=md_description, synopsis='<query>', defaultTrigger='br '
        )
        PluginInstance.__init__(self)
        self.profile_path = get_profile_path()
        self.load_bookmarks()

    def load_bookmarks(self) -> None:
        self.bookmarks = get_bookmarks(self.profile_path)

    def handleTriggerQuery(self, query) -> None:
        matcher = Matcher(query.string)

        items_with_score = []
        for i, (name, url) in enumerate(self.bookmarks):
            score = None
            if not score:
                match = matcher.match(name)
                if match:
                    score = (2, match.score)
            if not score:
                match = matcher.match(url)
                if match:
                    score = (1, match.score)
            if not score:
                continue
            items_with_score.append(
                (
                    StandardItem(
                        id=f'{md_name}/{i}',
                        text=name,
                        subtext=url,
                        iconUrls=[ICON_URL],
                        actions=[
                            Action(md_name, f'{md_name}/{i}', lambda url=url: runDetachedProcess(['xdg-open', url]))
                        ],
                    ),
                    score,
                )
            )
        items_with_score.sort(key=lambda item: item[1], reverse=True)
        for item, _score in items_with_score:
            query.add(item)

        item = StandardItem(
            id=f'{md_name}/reload',
            text='Reload bookmarks database',
            iconUrls=[ICON_URL],
            actions=[Action(f'{md_name}/reload', 'Reload bookmarks database', self.load_bookmarks)],
        )
        query.add(item)
