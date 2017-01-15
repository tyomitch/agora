#!/usr/bin/python

from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from urlparse import urljoin
import urllib2, yaml

strptime = datetime.strptime

# A very generic event scraping framework

parse_time = lambda s: strptime(s, '%H:%M').time()
parse_date = lambda s: strptime(s, '%a %d %b %Y').date()

class Event:
    date = start = end = title = desc = None

def soupify(url):
    request = urllib2.Request(url)
    request.add_header('User-Agent', 'Mozilla/5.0')
    return BeautifulSoup(urllib2.urlopen(request))

def scrape(baseurl, items, sublink, title, desc, dates, times, next):
    events = []
    url = baseurl

    while url:
        soup = soupify(url)
        for item in items(soup):
            _sublink = sublink(item)
            _title = title(_sublink)
            subpage = soupify(urljoin(baseurl, _sublink['href']))
            _desc = desc(subpage)

            for date, time in dates(item, subpage):
                e = Event()
                e.date = date
                e.title = _title
                e.desc = _desc
                if time:
                    _times = times(time)
                    if _times[0]!='TBC' and _times[0]!='00:00':
                        e.start = parse_time(_times[0])
                    if len(_times)>1 and _times[1]!='00:00':
                        e.end = parse_time(_times[1])
                events.append(e)

        _next = next(soup)
        url = _next and urljoin(baseurl, _next['href'])

    return events


# Simple scraper for unionevents

def parse_unionevents_date(date):
    try:
        date = strptime(date, '%d%b%Y')
    except:
        date = strptime(date, '%d%B%Y')
    return date.date()

events = scrape('http://www.unionevents.org/events/',
    lambda soup: soup('li', class_='three-fourth-block'),  # items
    lambda item: item.find('div', class_='event-title').a, # sublink
    lambda sublink: sublink.string.strip(),                # title
    lambda subpage: '\n'.join(' '.join(p.stripped_strings) # desc
                              for p in subpage.find('div', class_='two-third-block')('p')),
    lambda item, subpage:                                  # dates
        (yield parse_unionevents_date(''.join(item.find('div', class_='event-date').stripped_strings)), item),
    lambda item: item.find('div', class_='event-time').string.strip().split(' - '), # times
    lambda soup: soup.find('a', class_='next'))            # next


# Sophisticated scraping for visitleeds

url = "http://www.visitleeds.co.uk/whats-on/"
url = urljoin(url, soupify(url).find('a', title='Browse all events')['href'])

def visitleeds_desc(subpage):
    desc = subpage.find('div', class_='dmsField-d1').p
    for br in desc('br'):
        br.replace_with('\n')
    return ''.join(desc.strings)

def date_range(first, last): # inclusive
    for d in range((last-first).days+1):
        yield first + timedelta(d)

def visitleeds_dates(item, subpage):
    for daterow in subpage('tr', class_='dmsOpenTime'):
        dates, time = daterow('td')
        dates = dates.string.split(' - ')
        date2 = len(dates)>1 and parse_date(dates[1])
        try: # Sat 12 Nov 2016 - Wed 25 Jan 2017
            date1 = parse_date(dates[0])
        except:
            try: # Tue 31 Jan - Sun 5 Feb 2017
                date1 = dates[0] + date2.strftime(' %Y')
                date1 = parse_date(date1)
            except: # Tue 10 - Sun 15 Jan 2017
                date1 = dates[0] + date2.strftime(' %b %Y')
                date1 = parse_date(date1)
        date2 = date2 or date1

        for date in date_range(date1, date2):
            yield date, time.string

events += scrape(url,
    lambda soup: soup('div', class_='thedmsBrowseRow'), # items
    lambda item: item.h2.a,                             # sublink
    lambda sublink: sublink.strings.next().strip(),     # title
    visitleeds_desc, visitleeds_dates,                  # desc, dates
    lambda time: time.strip().replace(' to ', ' ').split(' ', 2), # times
    lambda soup: soup.find('a', class_='pagenextbrowsedata12'))   # next


print yaml.dump(events)

