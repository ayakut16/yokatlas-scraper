#!/usr/bin/env python3
"""
Script to read all JSON files and create a final data.json with normalization.
"""

import json
import glob
import re
from typing import List, Dict, Any


def normalize_quota_status(quota_status: str, max_rank: List[str], total_quota: List[str], filled_quota: List[str]) -> str:
    """
    Normalize quota_status according to the rules:
    1. If quota_status is "Doldu#", return "Doldu"
    2. If quota_status is empty, compare first numbers from total_quota[0] and filled_quota[0]
    """
    if quota_status and quota_status.endswith('#'):
        return quota_status.rstrip('#')
    if not quota_status and len(max_rank) > 0 and max_rank[0] == "Dolmadı":
        return "Dolmadı"
    if not quota_status and total_quota and filled_quota:
        # Extract first number before '+' from total_quota[0] and filled_quota[0]
        try:
            total_first = int(total_quota[0].split('+')[0])
            # Handle filled_quota format - it might be "Doldu-XX" or "XX+..."
            filled_str = filled_quota[0]
            if filled_str.startswith('Doldu'):
                # If it starts with "Doldu", it means it's filled
                return "Doldu"
            else:
                filled_first = int(filled_str.split('+')[0])
                return "Doldu" if filled_first >= total_first else "Dolmadı"
        except (ValueError, IndexError):
            # If we can't parse the numbers, return Doldu
            return "Doldu"

    return quota_status


def normalize_attributes(attributes: List[str]) -> List[str]:
    """
    Normalize attributes by splitting combined attributes like "İngilizce)KKTC Uyruklu (4 Yıllık"
    into separate attributes: ["İngilizce", "KKTC Uyruklu", "4 Yıllık"]
    """
    normalized = []

    for attr in attributes:
        # Check if attribute contains the pattern with )...(
        if ')' in attr and '(' in attr:
            # Split by ') ' to separate the first part
            parts = attr.split(')')
            if len(parts) >= 2:
                # First part is before the ')'
                first_part = parts[0].strip()
                if first_part:
                    normalized.append(first_part)

                # The rest contains the middle and last parts
                remaining = ')'.join(parts[1:])

                # Split by '(' to separate middle and last parts
                if '(' in remaining:
                    middle_and_last = remaining.split('(')
                    middle_part = middle_and_last[0].strip()
                    if middle_part:
                        normalized.append(middle_part)

                    # Last part is after '(' and before ')'
                    if len(middle_and_last) > 1:
                        last_part = middle_and_last[1].replace(')', '').strip()
                        if last_part:
                            normalized.append(last_part)
                else:
                    # No '(', just add the remaining part
                    remaining = remaining.strip()
                    if remaining:
                        normalized.append(remaining)
            else:
                normalized.append(attr)
        else:
            normalized.append(attr)

    return normalized


def process_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process a single entry by applying all normalization rules.
    """
    processed_entry = entry.copy()

    # Normalize quota_status
    processed_entry['quota_status'] = normalize_quota_status(
        entry.get('quota_status', ''),
        entry.get('max_rank', []),
        entry.get('total_quota', []),
        entry.get('filled_quota', [])
    )

    # Normalize attributes
    if 'attributes' in entry:
        processed_entry['attributes'] = normalize_attributes(entry['attributes'])

    return processed_entry


def main():
    """
    Main function to read all JSON files and create final data.json.
    """
    # Find all university data JSON files
    json_files = glob.glob('universities_data_*.json')

    if not json_files:
        print("No university data JSON files found!")
        return

    print(f"Found {len(json_files)} JSON files to process:")
    for file in json_files:
        print(f"  - {file}")

    all_data = []

    # Process each JSON file
    for json_file in json_files:
        print(f"Processing {json_file}...")
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Process each entry in the file
            for entry in data:
                processed_entry = process_entry(entry)
                all_data.append(processed_entry)

            print(f"  Processed {len(data)} entries from {json_file}")

        except Exception as e:
            print(f"Error processing {json_file}: {e}")
            continue

    # Write final data to data.json
    print(f"\nWriting {len(all_data)} total entries to data.json...")
    try:
        with open('data.json', 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print("Successfully created data.json!")

        # Print some statistics
        quota_statuses = {}
        for entry in all_data:
            status = entry.get('quota_status', 'Unknown')
            quota_statuses[status] = quota_statuses.get(status, 0) + 1

        print(f"\nQuota status distribution:")
        for status, count in sorted(quota_statuses.items()):
            print(f"  {status}: {count}")

    except Exception as e:
        print(f"Error writing data.json: {e}")


if __name__ == "__main__":
    main()
