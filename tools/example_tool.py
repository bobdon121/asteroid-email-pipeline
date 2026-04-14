#!/usr/bin/env python3
"""
Example Tool - Template for WAT Framework Tools

This tool demonstrates the standard pattern for building deterministic
execution scripts in the WAT framework.
"""

import os
import sys
import argparse
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
PROJECT_ROOT = Path(__file__).parent.parent
TMP_DIR = PROJECT_ROOT / ".tmp"


def setup_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Example tool that demonstrates the standard pattern"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Input data or file path"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=str(TMP_DIR / "example_output.json"),
        help="Output file path (default: .tmp/example_output.json)"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    return parser.parse_args()


def validate_inputs(args):
    """Validate that all required inputs are present and valid."""
    if not args.input:
        raise ValueError("Input cannot be empty")

    # Ensure .tmp directory exists
    TMP_DIR.mkdir(exist_ok=True)

    if args.verbose:
        print(f"✓ Input validated: {args.input}")

    return True


def process_data(input_data, verbose=False):
    """
    Main processing logic.

    This is where the actual work happens. Keep this function:
    - Deterministic: same input = same output
    - Focused: does one thing well
    - Testable: easy to verify correctness
    """
    if verbose:
        print(f"Processing: {input_data}")

    # Example processing
    result = {
        "input": input_data,
        "processed": input_data.upper(),
        "length": len(input_data),
        "status": "success"
    }

    return result


def save_output(data, output_path, verbose=False):
    """Save processed data to output file."""
    output_file = Path(output_path)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    with open(output_file, 'w') as f:
        json.dump(data, f, indent=2)

    if verbose:
        print(f"✓ Output saved to: {output_file}")

    return output_file


def main():
    """Main execution flow."""
    try:
        # 1. Parse arguments
        args = setup_args()

        # 2. Validate inputs
        validate_inputs(args)

        # 3. Process data
        result = process_data(args.input, verbose=args.verbose)

        # 4. Save output
        output_file = save_output(result, args.output, verbose=args.verbose)

        # 5. Return success
        print(f"SUCCESS: Output saved to {output_file}")
        return 0

    except Exception as e:
        print(f"ERROR: {str(e)}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
