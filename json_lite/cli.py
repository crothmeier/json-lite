#!/usr/bin/env python3
"""CLI for JSON Lite tools."""

import sys
import argparse
from pathlib import Path
from typing import Optional

from tools.process_chatgpt_export import process_chatgpt_export


def main():
    """Main CLI entry point for jsonlite-extract."""
    parser = argparse.ArgumentParser(
        prog='jsonlite-extract',
        description='Memory-efficient ChatGPT export extractor'
    )
    
    parser.add_argument(
        'input_json',
        type=Path,
        help='Path to ChatGPT export JSON file'
    )
    
    parser.add_argument(
        '-o', '--output',
        type=Path,
        required=True,
        help='Output directory for markdown files'
    )
    
    parser.add_argument(
        '--split-conversations',
        action='store_true',
        help='Split conversations into separate files (default behavior)'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        metavar='N',
        help='Limit number of conversations to process'
    )
    
    parser.add_argument(
        '--progress',
        action='store_true',
        help='Show progress during processing'
    )
    
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose output'
    )
    
    args = parser.parse_args()
    
    try:
        count = process_chatgpt_export(
            input_json=args.input_json,
            output_dir=args.output,
            limit=args.limit,
            progress=args.progress,
            verbose=args.verbose
        )
        
        if not args.progress:
            print(f"Successfully processed {count} conversations")
            
        return 0
        
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error processing export: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())