# news_crawler_demo
A simplified demo of a news article crawler.

Crawls news from [Yle](https://yle.fi/uutiset/tuoreimmat). Automatically selects the correct links by finding common element parents. News article parsing is currently done with hardcoded xpaths, which works as long as the page is not changed. Deeper element analysis would be a better solution.

Uses Python3, lxml for parsing html, and arsenic/chrome as headless driver. Async requests with maximum of 5 simultaneous requests.
