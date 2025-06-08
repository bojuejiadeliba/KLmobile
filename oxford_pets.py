"""
@author: Preprocessing script for Oxford-IIIT Pets dataset
Date: 2025-06-09
Based on the pattern from format_animals_151.py
"""

import numpy as np
import pandas as pd
import os
import argparse
import json
import torchvision.datasets
from collections import defaultdict


def format_oxford_pets_dataset(data_dir="./eval_datasets", save_dir="./eval_datasets"):
    """
    Format Oxford-IIIT Pets dataset similar to the animals_151 preprocessing
    Creates the missing oxford_pets_labels.json file
    """
    print("🐱 Formatting Oxford-IIIT Pets dataset...")

    # Download the dataset using torchvision to get proper class structure
    try:
        dataset = torchvision.datasets.OxfordIIITPet(
            root=data_dir,
            split="test",
            target_types="category",
            download=True
        )

        print(f"✅ Dataset downloaded to: {data_dir}")
        print(f"📊 Found {len(dataset.classes)} pet breeds")

    except Exception as e:
        print(f"❌ Error downloading dataset: {e}")
        return False

    # Create label mapping (similar to animals_151 format)
    mapping_label = {}

    # Method 1: Use torchvision's class names (cleaner approach)
    for idx, class_name in enumerate(dataset.classes):
        # Clean up class names (remove underscores, proper capitalization)
        clean_name = class_name.replace('_', ' ').title()
        mapping_label[class_name] = clean_name

    # Alternative Method 2: Scan actual folder structure (if needed)
    pets_data_dir = os.path.join(data_dir, "oxford-iiit-pet")
    if os.path.exists(pets_data_dir):
        print(f"📁 Found pets data directory: {pets_data_dir}")

    # Save the JSON mapping file (this is what was missing!)
    json_path = os.path.join(data_dir, "oxford-iiit-pet", "oxford_pets_labels.json")
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    with open(json_path, "w") as fp:
        json.dump(mapping_label, fp, indent=2)

    print(f"✅ Created: {json_path}")
    print(f"📋 Label mapping contains {len(mapping_label)} breeds:")

    # Show some examples
    for i, (original, clean) in enumerate(list(mapping_label.items())[:10]):
        print(f"  {original} → {clean}")

    if len(mapping_label) > 10:
        print(f"  ... and {len(mapping_label) - 10} more breeds")

    # Optional: Create a CSV file similar to animals_151 format
    create_optional_csv = False
    if create_optional_csv:
        print("\n📊 Creating optional CSV file...")
        data = defaultdict(list)

        # This would scan actual image files if needed
        # For now, we just create the JSON which is what's required

    print("\n🎉 Oxford Pets preprocessing complete!")
    print(f"📁 JSON file saved to: {json_path}")

    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        prog="format_oxford_pets",
        description="Preprocessing script for Oxford-IIIT Pets dataset (creates missing JSON labels)"
    )

    parser.add_argument(
        "--data_dir",
        "-D",
        required=False,
        type=str,
        default="./eval_datasets",
        help="Directory where the dataset will be downloaded/stored"
    )

    parser.add_argument(
        "--save_dir",
        "-s",
        required=False,
        type=str,
        default="./eval_datasets",
        help="Directory to save the processed files"
    )

    args = parser.parse_args()

    success = format_oxford_pets_dataset(args.data_dir, args.save_dir)

    if success:
        print("\n✅ Ready to run Oxford Pets evaluation!")
        print("   You can now use: --dataset oxford_pets")
    else:
        print("\n❌ Preprocessing failed!")