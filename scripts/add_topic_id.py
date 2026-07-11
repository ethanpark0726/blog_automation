"""Add topic_id to existing posts for KO/EN pairing."""
import glob, re

# Define topic_id mapping by date+time (unique per topic pair)
TOPIC_MAP = {
    "2026-07-08 05:19:15": "adobe-architecture",
    "2026-07-08 05:42:52": "solar-system-formation",
    "2026-07-10 01:37:38": "crossfit-heat-science",
}

files = glob.glob('_posts/**/*.md', recursive=True)
for f in files:
    with open(f, encoding='utf-8') as fh:
        content = fh.read()
    
    for date_str, topic_id in TOPIC_MAP.items():
        if date_str in content and 'topic_id:' not in content:
            # Insert topic_id after lang line
            content = re.sub(
                r'(lang: \w+)',
                rf'\1\ntopic_id: "{topic_id}"',
                content,
                count=1
            )
            with open(f, 'w', encoding='utf-8') as fh:
                fh.write(content)
            print(f"[OK] {f} -> topic_id: {topic_id}")
            break
