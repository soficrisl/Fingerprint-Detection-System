"""
Analysis script for SD302c database to understand its structure.
This will help determine the number of subjects, fingers, and impressions.
"""

import os
from collections import defaultdict
from typing import Dict, Set, Tuple, List


def analyze_sd302c_database(directory: str) -> Dict:
    """
    Analyze the SD302c database structure.
    
    Args:
        directory: Path to the SD302c database directory
        
    Returns:
        Dictionary with analysis results
    """
    # Data structures to collect information
    subjects = set()
    hands = set()
    resolutions = set()
    finger_types = set()
    finger_numbers = set()
    
    # Detailed tracking
    subject_fingers = defaultdict(set)  # subject -> set of (hand, finger_type, finger_num)
    subject_impressions = defaultdict(set)  # subject -> set of resolutions
    complete_data = defaultdict(lambda: defaultdict(set))  # subject -> (hand,finger_type,finger_num) -> resolutions
    
    files_processed = 0
    parsing_errors = []
    
    # Process all files
    for root, dirs, files in os.walk(directory):
        for filename in files:
            if filename.endswith('.png'):
                files_processed += 1
                
                try:
                    # Parse filename: {subject}_{hand}_{resolution}_{finger_type}_{finger_number}.png
                    name_without_ext = filename.replace('.png', '')
                    parts = name_without_ext.split('_')
                    
                    if len(parts) != 5:
                        parsing_errors.append(f"Invalid format: {filename} (expected 5 parts, got {len(parts)})")
                        continue
                    
                    subject_id = parts[0]
                    hand = parts[1]
                    resolution = parts[2]
                    finger_type = parts[3]
                    finger_num = parts[4]
                    
                    # Collect unique values
                    subjects.add(subject_id)
                    hands.add(hand)
                    resolutions.add(resolution)
                    finger_types.add(finger_type)
                    finger_numbers.add(finger_num)
                    
                    # Track combinations
                    finger_key = (hand, finger_type, finger_num)
                    subject_fingers[subject_id].add(finger_key)
                    subject_impressions[subject_id].add(resolution)
                    complete_data[subject_id][finger_key].add(resolution)
                    
                except Exception as e:
                    parsing_errors.append(f"Error parsing {filename}: {str(e)}")
    
    # Analyze completeness
    expected_resolutions = sorted(resolutions)
    incomplete_subjects = []
    subject_stats = []
    
    for subject_id in sorted(subjects):
        fingers = subject_fingers[subject_id]
        impressions = subject_impressions[subject_id]
        
        # Check if all fingers have all resolutions
        incomplete_fingers = []
        for finger_key in fingers:
            finger_resolutions = complete_data[subject_id][finger_key]
            if finger_resolutions != resolutions:
                missing = resolutions - finger_resolutions
                incomplete_fingers.append(f"{finger_key}: missing {missing}")
        
        if incomplete_fingers:
            incomplete_subjects.append({
                'subject': subject_id,
                'incomplete_fingers': incomplete_fingers
            })
        
        subject_stats.append({
            'subject': subject_id,
            'num_fingers': len(fingers),
            'num_impressions': len(impressions),
            'total_files': sum(len(res) for res in complete_data[subject_id].values())
        })
    
    # Create unique subject-finger mapping for sequential IDs
    all_subject_fingers = []
    for subject_id in sorted(subjects):
        for finger_key in sorted(subject_fingers[subject_id]):
            all_subject_fingers.append((subject_id, *finger_key))
    
    # Generate sequential mapping
    sequential_mapping = {
        combo: idx for idx, combo in enumerate(sorted(all_subject_fingers))
    }
    
    # Prepare results
    results = {
        'summary': {
            'total_files': files_processed,
            'num_subjects': len(subjects),
            'num_unique_subject_fingers': len(all_subject_fingers),
            'num_resolutions': len(resolutions),
            'expected_total_files': len(all_subject_fingers) * len(resolutions),
        },
        'unique_values': {
            'subjects': sorted(subjects),
            'hands': sorted(hands),
            'resolutions': sorted(resolutions),
            'finger_types': sorted(finger_types),
            'finger_numbers': sorted(finger_numbers),
        },
        'subject_details': subject_stats,
        'incomplete_data': incomplete_subjects,
        'parsing_errors': parsing_errors,
        'sequential_mapping_sample': dict(list(sequential_mapping.items())[:20]),  # First 20 for preview
        'sequential_mapping_size': len(sequential_mapping)
    }
    
    return results, sequential_mapping


def print_analysis_report(results: Dict):
    """Print a formatted analysis report."""
    
    print("=" * 70)
    print("SD302C DATABASE ANALYSIS REPORT")
    print("=" * 70)
    
    # Summary
    print("\n SUMMARY")
    print("-" * 40)
    summary = results['summary']
    for key, value in summary.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    # Unique values
    print("\nUNIQUE VALUES FOUND")
    print("-" * 40)
    unique = results['unique_values']
    
    print(f"  Subjects ({len(unique['subjects'])}): {unique['subjects'][:5]}...")
    print(f"  Hands: {unique['hands']}")
    print(f"  Resolutions (impressions): {unique['resolutions']}")
    print(f"  Finger types: {unique['finger_types']}")
    print(f"  Finger numbers: {unique['finger_numbers']}")
    
    # Subject statistics
    print("\n PER-SUBJECT STATISTICS")
    print("-" * 40)
    for stat in results['subject_details'][:5]:  # Show first 5
        print(f"  Subject {stat['subject']}: {stat['num_fingers']} fingers, "
              f"{stat['num_impressions']} impressions, {stat['total_files']} files")
    if len(results['subject_details']) > 5:
        print(f"  ... and {len(results['subject_details']) - 5} more subjects")
    
    # Check consistency
    print("\n CONSISTENCY CHECK")
    print("-" * 40)
    
    # Check if all subjects have same number of fingers
    finger_counts = [s['num_fingers'] for s in results['subject_details']]
    if len(set(finger_counts)) == 1:
        print(f"All subjects have {finger_counts[0]} fingers")
    else:
        print(f"Inconsistent finger counts: {set(finger_counts)}")
    
    # Check if all subjects have same impressions
    impression_counts = [s['num_impressions'] for s in results['subject_details']]
    if len(set(impression_counts)) == 1:
        print(f"All subjects have {impression_counts[0]} impressions/resolutions")
    else:
        print(f"Inconsistent impression counts: {set(impression_counts)}")
    
    # Incomplete data
    if results['incomplete_data']:
        print(f"\n  INCOMPLETE DATA")
        print("-" * 40)
        print(f"  {len(results['incomplete_data'])} subjects have missing files")
        for item in results['incomplete_data'][:3]:
            print(f"    Subject {item['subject']}: {len(item['incomplete_fingers'])} incomplete fingers")
    else:
        print(f"All subjects have complete data")
    
    # Parsing errors
    if results['parsing_errors']:
        print(f"\n PARSING ERRORS")
        print("-" * 40)
        for error in results['parsing_errors'][:5]:
            print(f"  {error}")
    
    # Sequential mapping preview
    print(f"\n SEQUENTIAL MAPPING PREVIEW")
    print("-" * 40)
    print(f"  Total unique subject-finger combinations: {results['sequential_mapping_size']}")
    print("  First few mappings:")
    for combo, idx in list(results['sequential_mapping_sample'].items())[:10]:
        print(f"    {combo} -> {idx}")
    
    print("\n" + "=" * 70)


def generate_mapping_dict(sequential_mapping: Dict) -> str:
    """Generate Python dictionary code for the mapping."""
    
    lines = ["SUBJECT_FINGER_MAPPING = {"]
    for combo, idx in sorted(sequential_mapping.items(), key=lambda x: x[1]):
        # combo is (subject_id, hand, finger_type, finger_num)
        tupcopy = list(combo)
        tupcopy.pop(1)
        tupcopy.pop(1)
        final = tuple(tupcopy)
        lines.append(f"    {final}: {idx},")
    lines.append("}")
    
    return "\n".join(lines)


if __name__ == "__main__":
    # Change this to your SD302c database directory
    database_dir = r"C:\Users\sofic\OneDrive\Documentos\Work\Development\Databases\sd302c100500"
    
    print("Analyzing SD302c database...")
    results, sequential_mapping = analyze_sd302c_database(database_dir)
    
    # Print analysis report
    print_analysis_report(results)
    
    # Optionally save the mapping to a file
    save_mapping = input("\nDo you want to save the sequential mapping to a file? (y/n): ")
    if save_mapping.lower() == 'y':
        mapping_code = generate_mapping_dict(sequential_mapping)
        with open("sd302c_mapping.py", "w") as f:
            f.write(mapping_code)
        print("Mapping saved to sd302c_mapping.py")
    
    # Return key information
    print(f"\n📋 KEY INFORMATION FOR LOADER:")
    print(f"  - Use {results['summary']['num_unique_subject_fingers']} as the number of unique subjects")
    print(f"  - Resolutions {results['unique_values']['resolutions']} are your 'impressions'")
    print(f"  - Map resolutions to impression IDs: {dict(zip(sorted(results['unique_values']['resolutions']), range(1, len(results['unique_values']['resolutions'])+1)))}")