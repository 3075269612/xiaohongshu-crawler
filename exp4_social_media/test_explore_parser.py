"""Quick test of fixed parser on Explore page HTML."""
from pathlib import Path
from social_media_crawler.src.xhs_parser import _iter_profile_card_objects, parse_profile_note_cards
import time, sys

html = Path('social_media_crawler/data/debug_explore.html').read_text(encoding='utf-8')
print(f"HTML: {len(html)} bytes", flush=True)

# Test the low-level iterator
t0 = time.time()
objects = _iter_profile_card_objects(html)
t1 = time.time()
print(f"iter_objects: {len(objects)} objects in {t1-t0:.2f}s", flush=True)

if objects:
    print(f"First object keys: {list(objects[0].keys())}", flush=True)
    card = objects[0].get("noteCard", {})
    print(f"noteCard keys: {list(card.keys())}", flush=True)
    print(f"noteCard title: {card.get('displayTitle', 'N/A')}", flush=True)

# Test full parser
t0 = time.time()
cards = parse_profile_note_cards(html, source_url='explore')
t1 = time.time()
print(f"parse_cards: {len(cards)} cards in {t1-t0:.2f}s", flush=True)

for c in cards[:3]:
    print(f"  id={c.post_id} author={c.author_name} title={(c.title or 'N/A')[:40]}", flush=True)
    print(f"    xsec={c.raw.get('xsec_token','')[:25]}... type={c.raw.get('type')} like={c.like_count}", flush=True)
