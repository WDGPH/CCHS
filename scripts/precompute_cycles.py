"""
Script to precompute harmonized data for all CCHS cycles.
Run this once or when crosswalk/categories change.

Usage:
    python scripts/precompute_cycles.py
    
Optional arguments:
    --cycles 2021 2022 2023    Specify which cycles to precompute (default: all)
    --data-path data           Path to raw data files (default: data)
    --output-path data/precomputed    Path for precomputed outputs (default: data/precomputed)
"""

import sys
import argparse
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from config.settings import AVAILABLE_CYCLES
from src.data.precompute import (
    precompute_all_cycles,
    create_variable_availability_index,
    validate_precomputed_data,
    PRECOMPUTE_DIR
)
from src.data.loader import load_crosswalk, load_categories


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Precompute harmonized CCHS data for multi-cycle analysis"
    )
    
    parser.add_argument(
        '--cycles',
        nargs='+',
        default=AVAILABLE_CYCLES,
        help=f'Cycles to precompute (default: {" ".join(AVAILABLE_CYCLES)})'
    )
    
    parser.add_argument(
        '--data-path',
        type=str,
        default='data',
        help='Path to raw data files (default: data)'
    )
    
    parser.add_argument(
        '--output-path',
        type=str,
        default=str(PRECOMPUTE_DIR),
        help=f'Path for precomputed outputs (default: {PRECOMPUTE_DIR})'
    )
    
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate existing precomputed data, do not recompute'
    )
    
    return parser.parse_args()


def main():
    """Main precomputation routine."""
    args = parse_args()
    
    print("=" * 80)
    print("CCHS Multi-Cycle Data Precomputation")
    print("=" * 80)
    print(f"Cycles: {', '.join(args.cycles)}")
    print(f"Data path: {args.data_path}")
    print(f"Output path: {args.output_path}")
    print("=" * 80)
    
    output_dir = Path(args.output_path)
    
    # Validation mode
    if args.validate_only:
        print("\n🔍 Validating precomputed data...")
        validation = validate_precomputed_data(args.cycles, output_dir)
        
        all_valid = all(validation.values())
        if all_valid:
            print("\n✅ All precomputed data is valid!")
            return 0
        else:
            print("\n❌ Some precomputed data is invalid or missing")
            invalid_cycles = [c for c, v in validation.items() if not v]
            print(f"   Invalid/missing: {', '.join(invalid_cycles)}")
            return 1
    
    # Load crosswalk and categories
    print("\n📋 Loading crosswalk and categories...")
    try:
        crosswalk = load_crosswalk()
        print(f"✅ Loaded crosswalk: {len(crosswalk)} harmonized variables")
    except Exception as e:
        print(f"❌ Failed to load crosswalk: {e}")
        return 1
    
    try:
        categories = load_categories()
        print(f"✅ Loaded categories: {len(categories)} variables with mappings")
    except Exception as e:
        print(f"❌ Failed to load categories: {e}")
        return 1
    
    # Precompute all cycles
    print(f"\n🔄 Precomputing {len(args.cycles)} cycle(s)...")
    print("-" * 80)
    
    results = precompute_all_cycles(
        cycles=args.cycles,
        crosswalk=crosswalk,
        categories=categories,
        data_path=args.data_path,
        save_dir=output_dir
    )
    
    # Check results
    if not results:
        print("\n❌ No cycles were successfully precomputed")
        return 1
    
    # Create variable availability index
    print("\n📊 Creating variable availability index...")
    try:
        availability_index = create_variable_availability_index(
            cycles=list(results.keys()),
            save_dir=output_dir
        )
    except Exception as e:
        print(f"⚠️ Failed to create availability index: {e}")
    
    # Summary
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    
    total_vars = 0
    total_records = 0
    
    for cycle, result in results.items():
        meta = result['metadata']
        records = meta['record_count']
        vars_count = len(meta['available_vars'])
        
        print(f"{cycle}:")
        print(f"  ✅ {records:,} records")
        print(f"  ✅ {vars_count} harmonized variables")
        print(f"  📁 harmonized_data_{cycle}.parquet")
        print(f"  📁 harmonized_bootstrap_{cycle}.parquet")
        print(f"  📁 metadata_{cycle}.pkl")
        
        total_vars += vars_count
        total_records += records
    
    print("-" * 80)
    print(f"Total: {len(results)} cycle(s), {total_records:,} records")
    
    if availability_index:
        common_vars = [v for v, cycles in availability_index.items() if len(cycles) == len(results)]
        print(f"Common variables across all cycles: {len(common_vars)}")
    
    print("\n✅ Precomputation complete!")
    print(f"💾 Data saved to: {output_dir}/")
    print("\n💡 Next steps:")
    print("   1. Restart your Streamlit app to use precomputed data")
    print("   2. Multi-cycle analysis will now be much faster!")
    
    # Validate the precomputed data
    print("\n🔍 Running validation...")
    validation = validate_precomputed_data(list(results.keys()), output_dir)
    
    if all(validation.values()):
        print("✅ All precomputed data validated successfully!")
        return 0
    else:
        print("⚠️ Some validation checks failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
