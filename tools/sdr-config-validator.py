#!/usr/bin/env python3

import sys

import json
import argparse
import re
import validators
from typing import Any, Dict, Hashable, List, Tuple

# Function to validate a container


def validate_container(container_name=None, value=None):
    # List of keys that are required to be in the container definition
    required_keys = ["container_name", "container_display_name", "container_image", "container_config"]

    print(f"Linting {attribute}")
    for key, items in value.items():
        if key == "container_name":
            required_keys.remove("container_name")
            if not isinstance(items, str) or len(re.findall(r"(\s|[A-Z0-9]|(?!(_|-))\W)", items)) > 0:
                raise ValueError(f"Invalid container_name for {container_name}")
        elif key == "container_display_name":
            if not isinstance(items, str):
                raise ValueError(f"Invalid container_display_name for {container_name}")
            required_keys.remove("container_display_name")
        elif key == "container_image":
            required_keys.remove("container_image")
            if not isinstance(items, str) or len(re.findall(r"^(?:(?=[^:\/]{1,253})(?!-)[a-zA-Z0-9-]{1,63}(?<!-)(?:\.(?!-)[a-zA-Z0-9-]{1,63}(?<!-))*(?::[0-9]{1,5})?\/)?((?![._-])(?:[a-z0-9._-]*)(?<![._-])(?:\/(?![._-])[a-z0-9._-]*(?<![._-]))*)(?::(?![.-])[a-zA-Z0-9_.-]{1,128})?$", items)) == 0:
                raise ValueError("Invalid image URL")
        elif key == "container_website":
            if not isinstance(items, str) or not validators.url(items):
                raise ValueError("Invalid container website")
        elif key == "container_config":
            required_keys.remove("container_config")
            validate_container_config(container_name=container_name, values=items)
        elif key == "requires":
            validate_req_and_recommends(container_name=container_name, section="requires", values=items)
        elif key == "recommends":
            validate_req_and_recommends(container_name=container_name, section="recommends", values=items)
        elif key == "config_version":
            if not isinstance(items, float):
                raise ValueError(f"Invalid confign_version for {container_name}")
        else:
            print(f"Unknown key: {key} in {container_name}")

    # Run through all keys that weren't present in the container definition
    if len(required_keys) != 0:
        missing_keys = ", ".join(item for item in required_keys)
        raise ValueError(f"Missing keys: {missing_keys}")


# Function to validate each container's config


def validate_container_config(container_name=None, values=None):
    required_keys = ["user_description"]
    if values is not None and len(values) == 0:
        print(f"WARNING: {container_name} has port section that is empty. Please remove")
        return
    else:
        for key, items in values.items():
            if key == "user_description":
                required_keys.remove("user_description")
                if isinstance(items, str):
                    # this is valid
                    pass
                else:
                    raise ValueError(f"{container_name} key user_description has an invalid value '{items}'. Should be a string")
            elif key == "ports":
                validate_ports(container_name=container_name, values=items)
            elif key == "network_mode":
                if isinstance(key, str) and (items == "host" or items == "bridged"):
                    # this is valid
                    pass
                else:
                    raise ValueError(f"{container_name} key network_mode has an invalid value '{items}'. Should be 'bridged' or 'host'")
            elif key == "privileged":
                if isinstance(items, bool):
                    # this is valid
                    pass
                else:
                    raise ValueError(f"{container_name} key privileged has an invalid value '{items}'. Should be a boolean value")
            elif key == "volumes":
                validate_volumes(container_name=container_name, values=items)
            elif key == "devices":
                validate_devices(container_name=container_name, values=items)
            elif len(re.findall(r"^section_\d+", key)):
                validate_sections(container_name=container_name, values=items)
            else:
                raise ValueError(f"{container_name} has key ({key}) that is invalid")
        
        # Run through all keys that weren't present in the container definition
        if len(required_keys) != 0:
            missing_keys = ", ".join(item for item in required_keys)
            raise ValueError(f"Missing keys: {missing_keys}")


# Function to validate the sections


def validate_sections(container_name=None, values=None):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has section that is empty. Please remove")
        return


# Function to validate the devices


def validate_devices(container_name=None, values=None):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has devices section that is empty. Please remove")
        return

    for key, items in values.items():
        if key == "usb":
            if isinstance(items, bool):
                # this is valid
                pass
            else:
                raise ValueError(f"{container_name} key usb has an invalid value '{items}'. Should be a boolean value")
        elif len(re.findall(r"^device_\d+", key)) == 1:
            required_keys = ['container_device_path', 'host_device_path']
            for sub_key, sub_items in items.items():
                if sub_key == "host_device_path":
                    required_keys.remove('host_device_path')
                    if isinstance(sub_items, str) and len(re.findall(r"^(/)?([^/\0]+(/)?)+$", sub_items)) == 1:
                        # this is valid
                        pass
                    else:
                        ValueError(f"{container_name} has key ({sub_key}) in section devices that is invalid")

                elif sub_key == "container_device_path":
                    if not isinstance(sub_items, str):
                        ValueError(f"{container_name} has key ({sub_key}) in section devices that is invalid")
                    required_keys.remove('container_device_path')
                else:
                    ValueError(f"{container_name} has key ({sub_key}) in section devices that is invalid")
            
            if len(required_keys) != 0:
                missing_keys = ", ".join(item for item in required_keys)
                raise ValueError(f"Missing keys: {missing_keys}")
        else:
            raise ValueError(f"{container_name} has key ({key}) in section devices that is invalid")  


# Function to validate the volumes


def validate_volumes(container_name=None, values=None):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has volume section that is empty. Please remove")
        return

    for key, items in values.items():
        if len(re.findall(r"^volume_\d+", key)) == 1:
            # this is valid key naming
            required_keys = ['docker_volume_name', 'container_path']
            for sub_key, sub_items in items.items():
                # check for unix path
                if isinstance(sub_items, str) and len(re.findall(r"^(/)?([^/\0]+(/)?)+$", sub_items)) == 1 and sub_key == "container_path":
                    # this is valid 
                    required_keys.remove("container_path")
                elif sub_key == "docker_volume_name" and isinstance(sub_items, str):
                    required_keys.remove("docker_volume_name")
                else:
                    raise ValueError(f"{container_name} has key ({sub_key}) in section volume that is invalid")
                
            if len(required_keys) != 0:
                missing_keys = ", ".join(item for item in required_keys)
                raise ValueError(f"Missing keys: {missing_keys}")
        elif len(re.findall(r"^tmpfs_\d+", key)) == 1:
            # this is a valid key name
            required_keys = ['container_path', 'tmpfs_options']
            for sub_key, sub_items in items.items():
                if isinstance(sub_items, str) and sub_key == "container_path" and len(re.findall(r"^(/)?([^/\0]+(/)?)+$", sub_items)) == 1:
                    # this is valid
                    required_keys.remove("container_path")
                elif sub_key == "tmpfs_options" and isinstance(sub_items, str):  # not sure how to check if the formatting is good...I suppose leave it be?
                    required_keys.remove("tmpfs_options")
                else:
                    ValueError(f"{container_name} has key ({sub_key}) in section volume that is invalid")
            
            if len(required_keys) != 0:
                missing_keys = ", ".join(item for item in required_keys)
                raise ValueError(f"Missing keys: {missing_keys}")
        else:
            raise ValueError(f"{container_name} has key ({key}) in section volume that is invalid")  


# Function to validate the ports section


def validate_ports(container_name=None, values=None):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has port section that is empty. Please remove")
        return
    
    for key, items in values.items():
        if len(re.findall(r"^port_\d+", key)) == 1:
            for key_port, key_items in items.items():
                if key_port == "container_port" and isinstance(key_items, int):
                    # this is valid
                    pass
                else:
                    raise ValueError(f"{container_name} has key ({key_port}) in section ports that is invalid")
        else:
            raise ValueError(f"{container_name} has key ({key}) in section ports that is invalid")


# Function to validate the requires section


def validate_req_and_recommends(container_name=None, section=None, values=None):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has {section} that is empty. Please remove")
        return
    for key, items in values.items():
        # check for valid key name
        if len(re.findall(r"^container_\d+", key)) == 1 and isinstance(items, str):
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
                    if not isinstance(value, float):
                        raise ValueError(f"docker_config_version should be a float")
                    if value == 1.0:
                        print("Using version 1.0 specification")
                    else:
                        print (f"Unknown spec version {value}. Unexpected results may happen")
                elif attribute.startswith("container_"):
                    validate_container(container_name=attribute, value=value)
                else:
                    raise ValueError(f"Unknown element {attribute}")

            if len(required_keys) != 0:
                missing_keys = ", ".join(item for item in required_keys)
                raise ValueError(f"Missing keys: {missing_keys}")

            # We made it here. Should be all good
            print("**********VALID CONFIG FILE**********")
        except ValueError as e:
            print(f"ERROR: JSON linting failed: {e}")
            sys.exit(1)
        except TypeError as e:
            print(f"ERROR: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"ERROR: Linting failed with unspecified error: {e}")
            sys.exit(1)
