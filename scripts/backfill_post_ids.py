#!/usr/bin/env python3
"""
Backfill post_id for existing Jekyll posts.
"""

import os
import re
import hashlib
import glob
from pathlib import Path

def backfill_post_ids(directory):
    files = glob.glob(f"{directory}/**/*.md", recursive=True)
    count = 0
    
    for file_path in files:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Skip if already has post_id
        if re.search(r"^post_id:\s*", content, re.MULTILINE):
            continue
            
        # Extract topic_id
        topic_match = re.search(r"^topic_id:\s*\"([^\"]+)\"", content, re.MULTILINE)
        if not topic_match:
            print(f"Skipping {file_path}: No topic_id found.")
            continue
        topic_id = topic_match.group(1)
        
        # Extract date (e.g., date: 2026-07-08 05:19:15 +0900)
        date_match = re.search(r"^date:\s*(\d{4}-\d{2}-\d{2})", content, re.MULTILINE)
        if not date_match:
            print(f"Skipping {file_path}: No date found.")
            continue
        date_str = date_match.group(1)
        
        # Generate post_id
        post_id_hash = hashlib.sha256((topic_id + date_str).encode("utf-8")).hexdigest()[:8]
        post_id = f"{topic_id}-{post_id_hash}"
        
        # Insert post_id right after topic_id
        new_content = re.sub(
            r"^(topic_id:\s*\"[^\"]+\"\n)",
            f"\\1post_id: \"{post_id}\"\n",
            content,
            flags=re.MULTILINE
        )
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(new_content)
            
        print(f"Updated {file_path} with post_id: {post_id}")
        count += 1
        
    print(f"\nBackfill complete. Updated {count} files in {directory}.")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    posts_dir = os.path.join(base_dir, "_posts")
    print(f"Scanning {posts_dir} for posts missing post_id...")
    backfill_post_ids(posts_dir)
