import asyncio
from io import StringIO

from arsenic import browsers, get_session, services
from lxml import etree

class NewsCrawler():
    def __init__(self):
        self.service = services.Chromedriver()
        self.browser = browsers.Chrome(chromeOptions={
            'args': ['--headless', '--disable-gpu']
        })
        self.request_semaphore = asyncio.Semaphore(5)

    def _parse_etree_from_html(self, html):
        parser = etree.HTMLParser()
        tree = etree.parse(StringIO(html), parser)
        return tree

    def _parse_interesting_links_from_tree(self, tree):
        link_elements = tree.xpath('//a[@href]')
        elements = link_elements
        common_parents = dict()

        # This loop searches for common parents of link elements. If the parent for
        # the elements has already been seen, add the parent to the common parents
        # dictionary. Recurse up the tree with those elements that haven't been 
        # deemed as common parents, breaking when there are no more than 1 parent 
        # left (<html>)
        while True:
            parent_elements = set()
            for elem in elements:
                parent = elem.getparent()
                if not parent:
                    continue

                if parent not in parent_elements:
                    parent_elements.add(parent)

                else:
                    if parent not in common_parents:
                        common_parents[parent] = []
                    common_parents[parent].append(elem)
            
            elements = parent_elements - set(common_parents.keys())
            if len(parent_elements) <= 1:
                break
        
        # Get the most common "common parent", and find the links from 
        # it's children elements.
        max_parent_elem = max(common_parents, key=lambda x: len(x))
        interesting_links = []
        for elem in max_parent_elem:
            link_elem = elem.xpath('./descendant::a[@href]')
            if link_elem:
                interesting_links.append(link_elem[0].get('href'))

        return interesting_links

    def _parse_articles_from_htmls(self, htmls):
        parsed_articles = []
        for html in htmls:
            new_article = {
                'content': '',
                'headline': '',
                'published': '',
                'url': html[1]
            }

            html = html[0]
            tree = self._parse_etree_from_html(html)
            h1_elements = tree.xpath('//h1[contains(@class, "yle__article__heading")]')
            for elem in h1_elements:
                new_article['headline'] += ' '.join(elem.itertext())

            content_elements = tree.xpath('//div[@class="yle__article__content"]')
            for elem in content_elements:
                new_article['content'] += ' '.join(elem.itertext())

            publish_elements = tree.xpath('//span[@class="yle__article__date--published"]')
            for elem in publish_elements:
                new_article['published'] += ' '.join(elem.itertext())
            
            parsed_articles.append(new_article)        
        return parsed_articles

    def _validate_links(self, news_site_url, links):
        validated_links = []
        for link in links:
            if link.startswith('http'):
                validated_links.append(link)
            elif link.startswith('/'):
                validated_links.append(news_site_url + link)
            else:
                continue
        return validated_links

    async def _request_url(self, url, session):
        async with self.request_semaphore:
            await session.get(url)
            html = await session.get_page_source()
        return html, url
 
    async def _fetch_articles(self, urls):
        async with get_session(self.service, self.browser) as session:
            tasks = []
            for url in urls:
                tasks.append(
                    self._request_url(url, session)
                )
            htmls = await asyncio.gather(*tasks)
        return htmls

    async def crawl_news(self, news_site_url):
        async with get_session(self.service, self.browser) as session:
            html, _ = await self._request_url(news_site_url, session)

        tree = self._parse_etree_from_html(html)
        newslinks = self._parse_interesting_links_from_tree(tree)
        validated_newslinks = self._validate_links('https://yle.fi', newslinks)
        article_htmls = await self._fetch_articles(validated_newslinks)
        news_articles = self._parse_articles_from_htmls(article_htmls)
        return news_articles

if __name__ == "__main__":
    url = 'https://yle.fi/uutiset/tuoreimmat'
    crawler = NewsCrawler()
    loop = asyncio.get_event_loop()
    news = loop.run_until_complete(crawler.crawl_news(url))
    print(len(news))
    print(news[0])