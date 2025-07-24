import json
import glob
from collections import Counter
from pathlib import Path

def analyze_university_data():
    """
    Analyze all universities_data_*.json files and print statistics about:
    - Number of programs for each score type (dil, ea, say, etc.)
    - Total number of programs
    - Total set of attributes
    """

    # Find all data files matching the pattern
    data_files = glob.glob("universities_data_*.json")

    if not data_files:
        print("No universities_data_*.json files found!")
        return

    print(f"Found {len(data_files)} data files:")
    for file in data_files:
        print(f"  - {file}")
    print()

    # Initialize counters and sets
    score_type_counts = Counter()
    all_attributes = set()
    total_programs = 0

    # Process each file
    for file_path in data_files:
        print(f"Processing {file_path}...")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)

            print(f"  - Loaded {len(data)} programs from {file_path}")

            # Process each program in the file
            for program in data:
                # Count score types
                score_type = program.get('score_type', 'Unknown')
                score_type_counts[score_type] += 1

                # Collect attributes
                attributes = program.get('attributes', [])
                all_attributes.update(attributes)

                total_programs += 1

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            continue

    print(f"\nAnalysis complete!\n")

    # Print results
    print("="*60)
    print("ANALYTICS RESULTS")
    print("="*60)

    # 1. Number of programs for each score type
    print(f"\n1. NUMBER OF PROGRAMS FOR EACH SCORE TYPE ({len(score_type_counts)} unique types):")
    print("-" * 50)

    # Sort by count (descending) for better readability
    for score_type, count in score_type_counts.most_common():
        print(f"{score_type:<20} : {count:>6}")

    # 2. Total number of programs
    print(f"\n2. TOTAL NUMBER OF PROGRAMS: {total_programs}")

    # 3. Total set of attributes
    print(f"\n3. TOTAL SET OF ATTRIBUTES ({len(all_attributes)} unique attributes):")
    print("-" * 50)

    # Sort attributes alphabetically for better readability
    sorted_attributes = sorted(all_attributes)
    for i, attribute in enumerate(sorted_attributes, 1):
        print(f"{i:>3}. {attribute}")

    print("="*60)

if __name__ == "__main__":
    analyze_university_data()
