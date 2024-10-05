import configparser
import shutil
import sqlite3
import tempfile
from contextlib import closing, contextmanager
from pathlib import Path
from typing import Iterator, NamedTuple

from albert import (  # pylint: disable=import-error
    Action,
    GlobalQueryHandler,
    PluginInstance,
    RankItem,
    StandardItem,
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
    firefox_data_path = Path.home() / '.mozilla/firefox/'
    profile = configparser.ConfigParser()
    profile.read(firefox_data_path / 'profiles.ini')
    return firefox_data_path / profile.get('Profile0', 'Path')


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


class Plugin(PluginInstance, GlobalQueryHandler):
    def __init__(self) -> None:
        GlobalQueryHandler.__init__(
            self, id=__name__, name=md_name, description=md_description, synopsis='<query>|reload', defaultTrigger='ff '
        )
        PluginInstance.__init__(self)
        self.profile_path = get_profile_path()
        self.load_bookmarks()

    def load_bookmarks(self) -> None:
        self.bookmarks = get_bookmarks(self.profile_path)

    def handleGlobalQuery(self, query) -> list[RankItem]:
        res = []
        query_str = query.string.strip()
        if not query_str:
            return res

        if query_str == 'ff reload':
            self.load_bookmarks()
            return res

        query_str = query_str.lower()
        items_with_score = []
        for name, url in self.bookmarks:
            score = None
            name_index = name.lower().find(query_str)
            url_index = url.lower().find(query_str)
            if name_index != -1:
                score = (2, -name_index)
            elif url_index != -1:
                score = (1, -url_index)
            else:
                continue
            items_with_score.append(
                (
                    StandardItem(
                        id=md_name,
                        text=name,
                        subtext=url,
                        iconUrls=[ICON_URL],
                        actions=[Action(md_name, md_name, lambda url=url: runDetachedProcess(['xdg-open', url]))],
                    ),
                    score,
                )
            )
        items_with_score.sort(key=lambda item: item[1])
        for i, (item, score) in enumerate(items_with_score):
            res.append(RankItem(item, -i))
        return res
