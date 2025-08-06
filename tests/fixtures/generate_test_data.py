#!/usr/bin/env python3
"""Generate test JSON files for testing json-lite components."""

import json
import random
import string
import pathlib
from typing import Any, Dict, List, Optional


def generate_flat_json(size_mb: int, records: int, output_path: Optional[str] = None) -> str:
    """
    Generate a flat JSON file with specified size and number of records.
    
    Args:
        size_mb: Target file size in megabytes
        records: Number of records to generate
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    target_bytes = size_mb * 1024 * 1024
    record_size = max(10, target_bytes // records)  # Bytes per record
    
    data = []
    for i in range(records):
        # Calculate padding needed for target size
        base_record = {
            "id": i,
            "timestamp": f"2024-01-{(i % 28) + 1:02d}T{(i % 24):02d}:00:00Z",
            "status": random.choice(["active", "inactive", "pending"]),
            "value": random.uniform(0, 1000)
        }
        
        # Add padding to reach target record size
        base_size = len(json.dumps(base_record))
        if base_size < record_size:
            padding_size = record_size - base_size - 20  # Account for JSON overhead
            base_record["data"] = ''.join(random.choices(string.ascii_letters, k=max(0, padding_size)))
        
        data.append(base_record)
    
    json_str = json.dumps(data, indent=2)
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str)
        return output_path
    
    return json_str


def generate_nested_json(depth: int, width: int, output_path: Optional[str] = None) -> str:
    """
    Generate deeply nested JSON with specified depth and width.
    
    Args:
        depth: Maximum nesting depth
        width: Number of keys/elements at each level
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    def create_nested_structure(current_depth: int, max_depth: int, width: int) -> Any:
        if current_depth >= max_depth:
            # Leaf node - return primitive value
            return random.choice([
                f"value_{current_depth}",
                random.randint(0, 1000),
                random.random(),
                random.choice([True, False]),
                None
            ])
        
        # Randomly choose between object and array
        if random.random() < 0.5:
            # Create object
            obj = {}
            for i in range(width):
                key = f"key_{current_depth}_{i}"
                obj[key] = create_nested_structure(current_depth + 1, max_depth, max(1, width - 1))
            return obj
        else:
            # Create array
            arr = []
            for i in range(width):
                arr.append(create_nested_structure(current_depth + 1, max_depth, max(1, width - 1)))
            return arr
    
    data = create_nested_structure(0, depth, width)
    json_str = json.dumps(data, indent=2)
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str)
        return output_path
    
    return json_str


def generate_corrupted_json(valid_records: int, corruption_point: int, output_path: Optional[str] = None) -> str:
    """
    Generate a JSON file that becomes corrupted at a specific point.
    
    Args:
        valid_records: Number of valid records before corruption
        corruption_point: Byte position where corruption occurs
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or corrupted JSON string
    """
    # Generate valid JSON first
    data = []
    for i in range(valid_records):
        data.append({
            "id": i,
            "valid": True,
            "data": f"record_{i}"
        })
    
    json_str = json.dumps(data, indent=2)
    
    # Introduce corruption at specified point
    if corruption_point < len(json_str):
        # Truncate the JSON at corruption point
        corrupted = json_str[:corruption_point]
        
        # Add some garbage data
        garbage = ''.join(random.choices(string.printable, k=50))
        corrupted += garbage
    else:
        # If corruption point is beyond file, just truncate
        corrupted = json_str[:-10]  # Remove last 10 characters
    
    if output_path:
        pathlib.Path(output_path).write_text(corrupted)
        return output_path
    
    return corrupted


def generate_mixed_json(array_ratio: float, object_ratio: float, records: int = 1000, output_path: Optional[str] = None) -> str:
    """
    Generate JSON with mixed arrays and objects.
    
    Args:
        array_ratio: Ratio of array elements (0.0 to 1.0)
        object_ratio: Ratio of object elements (0.0 to 1.0)
        records: Total number of records
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    if array_ratio + object_ratio > 1.0:
        raise ValueError("array_ratio + object_ratio cannot exceed 1.0")
    
    data = []
    array_count = int(records * array_ratio)
    object_count = int(records * object_ratio)
    primitive_count = records - array_count - object_count
    
    # Generate arrays
    for i in range(array_count):
        arr = [random.randint(0, 100) for _ in range(random.randint(1, 10))]
        data.append(arr)
    
    # Generate objects
    for i in range(object_count):
        obj = {
            f"field_{j}": random.choice([
                f"value_{j}",
                random.randint(0, 100),
                random.random(),
                random.choice([True, False])
            ])
            for j in range(random.randint(1, 5))
        }
        data.append(obj)
    
    # Generate primitives
    for i in range(primitive_count):
        data.append(random.choice([
            f"string_{i}",
            random.randint(0, 1000),
            random.random(),
            random.choice([True, False]),
            None
        ]))
    
    # Shuffle to mix the types
    random.shuffle(data)
    
    json_str = json.dumps(data, indent=2)
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str)
        return output_path
    
    return json_str


def generate_wide_json(width: int, output_path: Optional[str] = None) -> str:
    """
    Generate JSON with very wide objects (many keys).
    
    Args:
        width: Number of keys in the object
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    data = {}
    for i in range(width):
        key = f"field_{i:06d}"  # Pad with zeros for consistent key length
        data[key] = {
            "index": i,
            "value": f"value_{i}",
            "timestamp": f"2024-01-01T{(i % 24):02d}:{(i % 60):02d}:00Z",
            "active": i % 2 == 0
        }
    
    json_str = json.dumps(data, indent=2)
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str)
        return output_path
    
    return json_str


def generate_unicode_json(records: int = 100, output_path: Optional[str] = None) -> str:
    """
    Generate JSON with Unicode characters from various languages.
    
    Args:
        records: Number of records to generate
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    unicode_samples = [
        "Hello World",  # English
        "你好世界",  # Chinese
        "مرحبا بالعالم",  # Arabic
        "Здравствуй мир",  # Russian
        "こんにちは世界",  # Japanese
        "안녕하세요 세계",  # Korean
        "Olá Mundo",  # Portuguese
        "Γεια σου κόσμε",  # Greek
        "שלום עולם",  # Hebrew
        "สวัสดีชาวโลก",  # Thai
        "🌍🌎🌏",  # Emojis
        "∑∏∫∂∇",  # Math symbols
        "€£¥₹₽",  # Currency symbols
        "♠♣♥♦",  # Card suits
        "☀☁☂☃☄",  # Weather symbols
    ]
    
    data = []
    for i in range(records):
        record = {
            "id": i,
            "text": random.choice(unicode_samples),
            "mixed": ''.join(random.sample(unicode_samples, k=3)),
            "emoji": ''.join(random.choices("🎉🎊🎈🎁🎂🍰🍕🍔🌮🌯", k=5))
        }
        data.append(record)
    
    json_str = json.dumps(data, ensure_ascii=False, indent=2)
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str, encoding='utf-8')
        return output_path
    
    return json_str


def generate_streaming_json(records: int = 10000, output_path: Optional[str] = None) -> str:
    """
    Generate JSON optimized for streaming (array of uniform objects).
    
    Args:
        records: Number of records to generate
        output_path: Optional path to save the file
    
    Returns:
        Path to the generated file or JSON string
    """
    # Generate uniform records for predictable streaming
    data = []
    for i in range(records):
        record = {
            "id": f"ID{i:08d}",
            "timestamp": 1704067200 + i,  # Unix timestamp
            "metric_1": random.uniform(0, 100),
            "metric_2": random.uniform(0, 100),
            "metric_3": random.uniform(0, 100),
            "status": (i % 10) < 8,  # 80% true
            "category": f"CAT{i % 100:03d}",
            "tags": [f"tag{j}" for j in range(i % 5)]
        }
        data.append(record)
    
    json_str = json.dumps(data)  # No indent for more compact streaming
    
    if output_path:
        pathlib.Path(output_path).write_text(json_str)
        return output_path
    
    return json_str


def generate_benchmark_suite(output_dir: str = "test_data"):
    """
    Generate a complete suite of benchmark files.
    
    Args:
        output_dir: Directory to save the benchmark files
    """
    output_path = pathlib.Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    print("Generating benchmark suite...")
    
    # Small files (< 1MB)
    print("- Generating small files...")
    generate_flat_json(1, 1000, output_path / "small_flat.json")
    generate_nested_json(5, 3, output_path / "small_nested.json")
    generate_wide_json(1000, output_path / "small_wide.json")
    
    # Medium files (1-10MB)
    print("- Generating medium files...")
    generate_flat_json(5, 10000, output_path / "medium_flat.json")
    generate_nested_json(10, 5, output_path / "medium_nested.json")
    generate_streaming_json(50000, output_path / "medium_streaming.json")
    
    # Large files (10-100MB)
    print("- Generating large files...")
    generate_flat_json(50, 100000, output_path / "large_flat.json")
    generate_mixed_json(0.3, 0.3, 100000, output_path / "large_mixed.json")
    
    # Special cases
    print("- Generating special case files...")
    generate_unicode_json(1000, output_path / "unicode.json")
    generate_corrupted_json(100, 5000, output_path / "corrupted.json")
    
    # Edge cases
    print("- Generating edge case files...")
    generate_nested_json(50, 2, output_path / "extremely_deep.json")
    generate_wide_json(10000, output_path / "extremely_wide.json")
    
    print(f"Benchmark suite generated in {output_path}")


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Generate test JSON files")
    parser.add_argument("--type", choices=["flat", "nested", "corrupted", "mixed", "wide", "unicode", "streaming", "suite"],
                       default="suite", help="Type of JSON to generate")
    parser.add_argument("--output", default="test_data", help="Output directory or file")
    parser.add_argument("--size-mb", type=int, default=1, help="File size in MB (for flat)")
    parser.add_argument("--records", type=int, default=1000, help="Number of records")
    parser.add_argument("--depth", type=int, default=5, help="Nesting depth (for nested)")
    parser.add_argument("--width", type=int, default=3, help="Width at each level (for nested/wide)")
    
    args = parser.parse_args()
    
    if args.type == "suite":
        generate_benchmark_suite(args.output)
    elif args.type == "flat":
        result = generate_flat_json(args.size_mb, args.records, args.output)
        print(f"Generated flat JSON: {result}")
    elif args.type == "nested":
        result = generate_nested_json(args.depth, args.width, args.output)
        print(f"Generated nested JSON: {result}")
    elif args.type == "corrupted":
        result = generate_corrupted_json(args.records, args.size_mb * 1024, args.output)
        print(f"Generated corrupted JSON: {result}")
    elif args.type == "mixed":
        result = generate_mixed_json(0.4, 0.4, args.records, args.output)
        print(f"Generated mixed JSON: {result}")
    elif args.type == "wide":
        result = generate_wide_json(args.width, args.output)
        print(f"Generated wide JSON: {result}")
    elif args.type == "unicode":
        result = generate_unicode_json(args.records, args.output)
        print(f"Generated Unicode JSON: {result}")
    elif args.type == "streaming":
        result = generate_streaming_json(args.records, args.output)
        print(f"Generated streaming JSON: {result}")