import datetime
import string
from typing import Any, List, Literal, Optional

import arxiv
import requests
from crossref.restful import Works
from unidecode import unidecode

from .const import CROSSREF_TO_BIB, SKIPWORDS


def to_notionprop(content: Optional[Any],
                  mode: Literal['title', 'select', 'multi_select',
                                'rich_text', 'number', 'date']):
    def remove_comma_from_string(content: str):
        if ',' not in content:
            return content
        return content.replace(',', '_')  # comma is not accepted by Notion

    def remove_comma(content: Any):
        if isinstance(content, str) and (',' in content):
            return remove_comma_from_string(content)
        if isinstance(content, list):
            for i, content_ in enumerate(content):
                if not isinstance(content_, str):
                    continue
                content[i] = remove_comma_from_string(content_)
            return content
        return content

    if content is None:
        return None

    match mode:
        case 'title':
            assert isinstance(content, str)
            return {'title': [{'text': {'content': content}}]}
        case 'select':
            assert isinstance(content, str)
            content = remove_comma(content)
            return {'select': {'name': content}}
        case 'multi_select':
            assert isinstance(content, list)
            content = remove_comma(content)
            names = [{'name': content_} for content_ in content]
            return {'multi_select': names}
        case 'rich_text':
            assert isinstance(content, str)
            return {'rich_text': [{'text': {'content': content}}]}
        case 'number':
            assert isinstance(content, (int, float))
            return {'number': content}
        case 'date':
            assert isinstance(content, list)
            date = '-'.join([str(content_) for content_ in content[0]])
            return {'date': {'start': date}}
        case _:
            raise ValueError('Invalid mode')


class NotionPropMaker:
    def __init__(self):
        self.notes = []

    def from_doi(self, doi: str, propnames: dict) -> dict:
        if 'arXiv' in doi:
            doi_style_info = self._fetch_info_from_arxiv(doi)
        else:
            doi_style_info = self._fetch_info_from_doi(doi)
        return self._make_properties(doi_style_info, propnames)

    def from_doi_jalc(self, doi: str, propnames: dict) -> dict:
        doi_style_info = self._fetch_info_from_doi_jalc(doi)
        return self._make_properties(doi_style_info, propnames)

    def _fetch_info_from_arxiv(self, doi: str) -> dict:
        doi = doi.replace('//', '/')
        arxiv_id = doi.split('arXiv.')[1]
        paper = next(arxiv.Client().results(arxiv.Search(id_list=[arxiv_id])))

        authors = []
        for author in paper.authors:
            authors.append({
                'given': ' '.join(author.name.split(' ')[:-1]),
                'family': author.name.split(' ')[-1]})

        date = paper.published
        return {
            'author': authors,
            'published': {'date-parts': [[date.year, date.month, date.day]]},
            'type': 'journal-article',
            'title': [paper.title],
            'container-title': ['arXiv'],
            'DOI': doi}

    def _fetch_info_from_doi(self, doi: str) -> dict:
        doi = doi.replace('//', '/')
        works = Works()
        info = works.doi(doi)

        if info is None:
            raise Exception(f'Extracted DOI ({doi}) was not found.')
        return works.doi(doi)

    def _fetch_info_from_doi_jalc(self, doi: str) -> dict:        
        url = f"https://api.japanlinkcenter.org/dois/{doi}"
        headers = {"Accept": "application/json"}

        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status()  # HTTPエラーを例外にする
        except requests.exceptions.HTTPError as e:
            raise Exception(f"JaLC API HTTP error for DOI '{doi}': {e}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"JaLC API connection error: {e}")

        try:
            data = response.json()
        except ValueError:
            raise Exception(f"JaLC API returned invalid JSON for DOI '{doi}'.")
        meta = data.get("data", {})
        if not meta:
            raise Exception(f"No metadata found in JaLC response for DOI '{doi}'.")

        # タイトル（日本語 or 英語）
        title_list = meta.get("title_list", [])
        title = next((t["title"] for t in title_list if t["lang"] == "ja"), None)
        if title is None:
            title = next((t["title"] for t in title_list if t["lang"] == "en"), None)

        # 著者リスト（日本語または英語から取得）
        author = []
        for person in meta.get("creator_list", []):
            name_obj = next((n for n in person.get("names", []) if n["lang"] == "ja"), None)
            if not name_obj:
                name_obj = next((n for n in person.get("names", []) if n["lang"] == "en"), None)
            if name_obj:
                author.append({
                    "given": name_obj.get("first_name"),
                    "family": name_obj.get("last_name")
                })

        published = None
        if "date" in meta:
            try:
                dt = datetime.datetime.strptime(meta["date"], "%Y-%m-%d")
                published = {"date-parts": [[dt.year, dt.month, dt.day]]}
            except ValueError:
                pass

        # ジャーナル名（日本語優先）
        journal_list = meta.get("journal_title_name_list", [])
        container = next((j["journal_title_name"] for j in journal_list if j["lang"] == "ja" and j["type"] == "full"), None)
        if container is None:
            container = next((j["journal_title_name"] for j in journal_list if j["lang"] == "en" and j["type"] == "full"), None)

        # 出版社（日本語優先）
        pub_list = meta.get("publisher_list", [])
        publisher = next((p["publisher_name"] for p in pub_list if p["lang"] == "ja"), None)
        if publisher is None:
            publisher = next((p["publisher_name"] for p in pub_list if p["lang"] == "en"), None)

        # ページ番号
        first_page = meta.get("first_page")
        last_page = meta.get("last_page")
        page = None
        if first_page and last_page:
            page = f"{first_page}–{last_page}"
        elif first_page:
            page = first_page

        # JaLCの article_type → Crossref 準拠の型にマッピング
        article_type_map = {
            "pub": "journal-article",
            "dataset": "dataset",
            "book": "book",
            "conference-paper": "proceedings-article",
            "poster": "posted-content"
            # 必要なら追加
        }
        raw_type = meta.get("article_type")
        cr_type = article_type_map.get(raw_type, "article")  # fallback: "article"

        # フォーマット整形
        info = {
            "DOI": doi,
            "title": [title] if title else [],
            "author": author,
            "published": published,  # {"date-parts": [[year]]} if year else None,
            "container-title": [container] if container else [],
            "publisher": publisher,
            "volume": meta.get("volume"),
            "issue": meta.get("issue"),
            "page": page,
            "type": cr_type,
            "_source": "jalc"
        }
        info = {k: v for k, v in info.items() if v is not None}

        return info

    def _make_citekey(self, lastname, title, year):
        # from [extensions.zotero.translators.better-bibtex.skipWords], zotero.
        def convert_lastname(lastname):
            lastname = lastname.replace('_', '')
            return unidecode(lastname).lower().replace(' ', '')

        def up(str_):
            if len(str_) < 2:
                return str_.upper()
            if str_[0] == ' ':
                return ' ' + str_[1].upper() + str_[2:]
            return str_[0].upper() + str_[1:]

        def simplify(title):
            for key in ['/', '‐', '—']: # hyphen and dash, not minus (-).
                title = title.replace(key, ' ')
            title = ' ' + unidecode(title) + ' '
            for key in ['\'s', '\'t', '\'S', '\'T']:
                title = title.replace(key, '')
            title = title.translate(str.maketrans('', '', string.punctuation))
            for key in SKIPWORDS:
                key = ' ' + key + ' '
                title = title.replace(key, ' ')
                title = title.replace(key.upper(), ' ').replace(up(key), ' ')
            return title

        def make_shorttitle(title, n_title=3):
            while True:
                len_before = len(title.replace(' ', ''))
                title = simplify(title)
                if len_before == len(title.replace(' ', '')):
                    break

            title = [up(t) for t in title.split(' ') if t]
            if len(title) < n_title:
                return ''.join(title)
            return ''.join(title[:n_title])

        citekey = ''.join([
            convert_lastname(lastname),
            make_shorttitle(title),
            str(year)])

        return citekey

    def _make_properties(self, info: dict, propnames: dict):
        authors = self._make_author_list(info['author'])
        first_author_lastname = authors[0].split(' ')[-1]
        year = int(info['published']['date-parts'][0][0])
        record_name = first_author_lastname + str(year)
        entrytype = CROSSREF_TO_BIB.get(info['type']) or 'misc'
        citekey = self._make_citekey(
            first_author_lastname, info['title'][0], year)
        journal = info['container-title']
        journal = journal[0] if journal else None
        properties = {
            'Name': to_notionprop(record_name, 'title'),
            'doi': to_notionprop(info['DOI'], 'rich_text'),
            'edition': to_notionprop(info.get('edition-number'), 'rich_text'),
            'First': to_notionprop(authors[0], 'select'),
            'author': to_notionprop(authors, 'multi_select'),
            'title': to_notionprop(info['title'][0], 'rich_text'),
            'year': to_notionprop(year, 'number'),
            'journal': to_notionprop(journal, 'select'),
            'volume': to_notionprop(info.get('volume'), 'rich_text'),
            'Issue': to_notionprop(info.get('issue'), 'rich_text'),
            'pages': to_notionprop(info.get('page'), 'rich_text'),
            'publisher': to_notionprop(info.get('publisher'), 'select'),
            'Subject': to_notionprop(info.get('subject'), 'multi_select'),
            'id': to_notionprop(citekey, 'rich_text'),
            'entrytype': to_notionprop(entrytype, 'select'),
        }
        return {propnames.get(key) or key: value for key, value
                in properties.items() if value is not None}

    def _make_author_list(self, authors: List[dict]) -> List[str]:
        MAX_N_NOTION_MULTISELECT = 100
        authors_ = []
        for author in authors:
            given = author.get('given')
            family = author.get('family')
            if given and family:
                authors_.append(given + ' ' + family)
            elif (given is None) and family:
                authors_.append(family.replace(' ', '_'))
            elif name:=author.get('name'):
                authors_.append(name)
            else:
                raise RuntimeError('Valid author name was not found')
        if len(authors_) > MAX_N_NOTION_MULTISELECT:
            extra_authors = authors_[99:-1]
            self.notes.append('From the 100th to the second to last author'
                              f': {"; ".join(extra_authors)}')
            authors_ = authors_[:MAX_N_NOTION_MULTISELECT - 1] + [authors_[-1]]
        return authors_
