"""Discover new user URLs by refreshing the Explore page."""
from DrissionPage import ChromiumOptions, ChromiumPage
from social_media_crawler.src.xhs_parser import parse_profile_note_cards
import json, re, time, random
from pathlib import Path

def main():
    vpath = Path('social_media_crawler/data/xhs_visited_users.txt')
    visited_ids = set()
    for line in vpath.read_text(encoding='utf-8').splitlines():
        m = re.search(r'/user/profile/([0-9a-zA-Z]+)', line)
        if m:
            visited_ids.add(m.group(1))

    ppath = Path('social_media_crawler/data/xhs_posts.jsonl')
    for line in ppath.read_text(encoding='utf-8').splitlines():
        if not line.strip(): continue
        p = json.loads(line)
        aid = p.get('author_id','')
        if aid: visited_ids.add(aid)

    print(f'Known authors: {len(visited_ids)}')

    page = ChromiumPage(ChromiumOptions())
    page.get('https://www.xiaohongshu.com/explore')
    time.sleep(6)
    print('Login wait 10s...')
    time.sleep(10)

    new_authors = []
    for i in range(30):
        html = page.html
        cards = parse_profile_note_cards(html, source_url='explore')
        for c in cards:
            aid = c.author_id
            if aid and aid not in visited_ids:
                visited_ids.add(aid)
                new_authors.append(f'https://www.xiaohongshu.com/user/profile/{aid}')
        print(f'Refresh {i+1}: {len(cards)} cards, new: {len(new_authors)}', flush=True)
        if len(new_authors) >= 80:
            break
        page.refresh()
        time.sleep(random.uniform(3, 6))

    page.quit()
    print(f'New author URLs: {len(new_authors)}')

    qpath = Path('social_media_crawler/data/xhs_user_queue.txt')
    existing = set()
    if qpath.exists():
        for line in qpath.read_text(encoding='utf-8').splitlines():
            if line.strip() and not line.startswith('#'):
                existing.add(line.strip())
    added = 0
    with qpath.open('a', encoding='utf-8') as f:
        for url in new_authors:
            if url not in existing:
                f.write(url + '\n')
                existing.add(url)
                added += 1
    print(f'Added {added} to queue, total queue: {len(existing)}')

if __name__ == '__main__':
    main()
