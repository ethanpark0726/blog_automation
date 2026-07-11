import os
import sys
import subprocess

# The 3 original topics to regenerate under v1.9.0 quality guidelines
TOPICS = [
    "Discovering the Earthy Charm of Adobe Architecture",
    "How was our Solar System formed?",
    "Why does hot weather make CrossFit workouts harder to breathe?"
]

def main():
    print("🚀 Starting regeneration of existing posts...")
    
    # 1. Clean existing posts to prevent duplicates from slightly different slugs
    for lang in ['ko', 'en']:
        dir_path = f"_posts/{lang}"
        if os.path.exists(dir_path):
            for f in os.listdir(dir_path):
                if f.endswith('.md') and f != '.gitkeep':
                    file_path = os.path.join(dir_path, f)
                    try:
                        os.remove(file_path)
                        print(f"Removed old post: {file_path}")
                    except Exception as e:
                        print(f"Error removing {file_path}: {e}")

    # 2. Run the multi-agent pipeline for each topic
    for topic in TOPICS:
        print(f"\n==================================================")
        print(f"🔄 Regenerating topic: '{topic}'")
        print(f"==================================================")
        
        env = os.environ.copy()
        env["QUERY_INPUT"] = topic
        
        result = subprocess.run(
            [sys.executable, "scripts/multi_agent.py"],
            env=env,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print("Errors/Warnings:", result.stderr)

    print("\n🎉 Post regeneration completed successfully!")

if __name__ == "__main__":
    main()
