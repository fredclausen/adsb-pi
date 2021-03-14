#!/usr/bin/env python3

import json
import argparse
import re
import validators
from typing import Any, Dict, Hashable, List, Tuple

# Function to validate a container

def validate_container(container_name=None, value=None):
    # List of keys that are required to be in the container definition
    required_keys = ["container_name", "container_display_name", "container_image", "container_config"]

    print(f"Linting container {attribute}")
    for key, items in value.items():
        if key == "container_name":
            required_keys.remove("container_name")
            if len(re.findall(r"(\s|[A-Z]|(?!(_|-))\W)", items)) > 0:
                raise ValueError(f"Invalid container_name for {container_name}")
        elif key == "container_display_name":
            required_keys.remove("container_display_name")
        elif key == "container_image":
            required_keys.remove("container_image")
            if len(re.findall(r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$", items)) == 0:
                raise ValueError("Invalid image URL")
        elif key == "container_website":
            if not validators.url(items):
                raise ValueError("Invalid container website")
        elif key == "container_config":
            required_keys.remove("container_config")
        elif key == "requires":
            validate_req_and_recommends(container_name=container_name, section="requires", values=items)
        elif key == "recommends":
            validate_req_and_recommends(container_name=container_name, section="recommends", values=items)
        elif key == "config_version":
            pass
        else:
            print(f"Unknown key: {key} in {container_name}")

    # Run through all keys that weren't present in the container definition
    if len(required_keys) != 0:
        for item in required_keys:
            print(f"ERROR: missing key(s) {item} in {container_name}")


# Function to validate the requires section

def validate_req_and_recommends(container_name=None, section=None, values=None):
    if len(values) == 0:
        print(f"WARNING: {container_name} has {section} that is empty. Please remove")
        return
    for key, items in values.items():
        # check for valid key name
        if len(re.findall(r"^container_\d+", key)) == 1:
            pass
        else:
            raise ValueError(f"{container_name} has key ({key}) in section {section} that is invalid")

# Function used by JSON loads to ensure all keys are unique
# which strangely isn't an exception in the default parser


def raise_on_duplicate_keys(ordered_pairs: List[Tuple[Hashable, Any]]) -> Dict:
    """Raise ValueError if a duplicate key exists in provided ordered list of pairs, otherwise return a dict."""
    dict_out = {}
    for key, val in ordered_pairs:
        if key in dict_out:
            raise ValueError(f'Duplicate key: {key}')
        else:
            dict_out[key] = val
    return dict_out

if __name__ == "__main__":
    required_keys = ['docker_config_version']
    parser = argparse.ArgumentParser(description='Validate SDR Docker Config JSON File')

    parser.add_argument(
        '--files', '-f',
        type=str,
        help='List of json files to validate. Separate each with a space',
        nargs='+',
        required=True,
    )

    args = parser.parse_args()

    for json_file in args.files:
        try:
            print(f"Loading file: {json_file}")
            file_to_validate = json.load(open(json_file), object_pairs_hook=raise_on_duplicate_keys)
            print(f"File has valid JSON. Attempting to lint v1 spec")
            for attribute, value in file_to_validate.items():
                if attribute == "docker_config_version":
                    required_keys.remove('docker_config_version')
                    if value == 1.0:
                        print("Using version 1.0 specification")
                    else:
                        print (f"Unknown spec version {value}. Unexpected results may happen")
                elif attribute.startswith("container_"):
                    validate_container(container_name=attribute, value=value)
                else:
                    raise ValueError(f"Unknown element {attribute}")

        except ValueError as e:
            print(f"ERROR: JSON linting failed: {e}")
        except TypeError as e:
            print(f"ERROR: {e}")
        except Exception as e:
            print(f"ERROR: Linting failed with unspecified error: {e}")

    if len(required_keys) != 0:
        for item in required_keys:
            print(f"ERROR: missing key(s) {item}")
