#!/usr/bin/env python3

import sys

import json
import argparse
import re
import validators
from typing import Any, Dict, Hashable, List, Tuple

containers = []
recs_req = []

# Function to validate a container


def validate_container(container_name=None, value=None):
    # List of keys that are required to be in the container definition
    required_keys = ["container_name", "container_display_name", "container_image", "container_config", "user_full_description"]

    print(f"Linting {container_name} / {value['container_display_name']}")
    for key, items in value.items():
        if key == "container_name":
            required_keys.remove("container_name")
            containers.append(items)
            if not isinstance(items, str) or len(re.findall(r"(\s|[A-Z]|(?!(_|-))\W)", items)) > 0:
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
        elif key == "user_full_description":
            required_keys.remove("user_full_description")
            if not isinstance(items, str):
                raise ValueError(f"Invalid user_full_description for {container_name}")
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
            elif len(re.findall(r"^template_\d+", key)):
                validate_template(container_name=container_name, values=items)
            else:
                raise ValueError(f"{container_name} has key ({key}) that is invalid")
        
        # Run through all keys that weren't present in the container definition
        if len(required_keys) != 0:
            missing_keys = ", ".join(item for item in required_keys)
            raise ValueError(f"Missing keys: {missing_keys}")


# Function to validate templates

def validate_template(container_name=None, values=None):
    required_keys = ['env_name_out']
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has template that is empty. Please remove")
        return

    for key, item in values.items():
        if 'separator' == key:
            if isinstance(item, str) and len(item) > 0:
            # this is valid
                pass
            else:
                raise ValueError(f"{container_name} has template with seperator that is invalid. Should be a non-blank string")
    
        elif 'env_name_out' == key:
            if isinstance(item, str) and len(item) > 0:
                required_keys.remove("env_name_out")
            else:
                raise ValueError(f"{container_name} has template with env_name_out that is invalid. Should be a non-blank string")
        elif len(re.findall(r"^include_\d+", key)) > 0:
            template_valid_keys = ['value', 'separator']
            template_required_keys = ['container', 'env_name']
            template_optional_keys = ['value_is_not', 'value_is', 'port']
            for template_key, template_item in item.items():
                if template_key in template_required_keys:
                    template_required_keys.remove(template_key)
                    if isinstance(template_item, str):
                        # this is valid
                        pass
                    else:
                        raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. Should be a non-blank string")
                elif template_key in template_optional_keys:
                    if isinstance(template_item, str):
                        if template_key == 'value_is_not':
                            if 'value_is' in item or 'port' in item:
                                raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. value_is and port cannot be in this section")
                        elif template_key == 'value_is':
                            if 'value_is_not' in item or 'port' in item:
                                raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. value_is and port cannot be in this section")
                        elif template_key == 'port':
                            if len(template_item) == 0:
                                raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. Should be a non-blank string")
                            if 'value_is' in item or 'value_is_not' in item:
                                raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. value_is and port cannot be in this section")
                    else:
                        raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. Should be a non-blank string")
                elif template_key in template_valid_keys:
                    if isinstance(template_item, str):
                        # this is valid
                        pass
                    else:
                        raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid. Should be a non-blank string")
                else:
                    raise ValueError(f"{container_name} has template with {key}/{template_key} that is invalid.")
            
            if len(template_required_keys) != 0:
                missing_keys = ", ".join(item for item in template_required_keys)
                raise ValueError(f"Missing keys: {missing_keys}")
        else:
            raise ValueError(f"{container_name} has template with {key} that is invalids.")
    # Run through all keys that weren't present in the container definition
    if len(required_keys) != 0:
        missing_keys = ", ".join(item for item in required_keys)
        raise ValueError(f"Missing keys: {missing_keys}")
# Function to validate the sections


def validate_sections(container_name=None, values=None):
    required_keys = ['user_description']
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has section that is empty. Please remove")
        return
    
    # we need to figure out what kind of section it is
    # and validate if it's a special section

    if "depends_on" in values:
        if "run_if" in values:
            raise ValueError(f"{container_name} has depends_on AND run_if. Can only have one")
        valid_keys = ['env_name', 'env_name_value']
        depends_on_values = values['depends_on']

        if 'env_name' not in depends_on_values and not isinstance(depends_on_values['env_name'], str) and len(depends_on_values['env_name']) == 0:
            raise ValueError(f"{container_name} has depends_on without env_name")
        
        if 'env_name_value' in depends_on_values:
            # do nothing for now. Will eventually need to check and see if the env variable has been previously declared
            pass
        
        for key in depends_on_values:
            if key not in valid_keys:
                raise ValueError(f"{container_name} depends_on has invalid key {key}")
    elif "run_if" in values:
        if "depends_on" in values:
            raise ValueError(f"{container_name} has depends_on AND run_if. Can only have one")
        
        valid_keys = ['user_question', 'user_question_after']
        run_if_values = values['run_if']

        if 'user_question' not in run_if_values and not isinstance(run_if_values['user_question'], str) and len(run_if_values['user_question']) == 0:
            raise ValueError(f"{container_name} has run_if without user_question")

        if 'user_question_after' in run_if_values and (not isinstance(run_if_values['user_question_after'], str) or len(run_if_values['user_question_after']) == 0):
            raise ValueError(f"{container_name} run_if user_question_after should be a string")

        for key in run_if_values:
            if key not in run_if_values:
                raise ValueError(f"{container_name} run_if has invalid key {key}")
    if 'loops' in values:
        loops_values = values['loops']
        valid_keys = ['max_loops', 'min_loops', 'starting_value']

        if 'max_loops' in loops_values and not isinstance(loops_values['max_loops'], int) and loops_values['max_loops'] == 0:
            raise ValueError(f"{container_name} max_loops should be a non-zero int")
        
        if 'min_loops' in loops_values and not isinstance(loops_values['min_loops'], int):
            raise ValueError(f"{container_name} min_loops should be an int")
        
        if 'starting_value' in loops_values and not isinstance(loops_values['starting_value'], int):
            raise ValueError(f"{container_name} starting_value should be anint")

        for key in loops_values:
            if key not in valid_keys:
                raise ValueError(f"{container_name} loops has invalid key {key}")

    for key, items in values.items():
        if len(re.findall(r"^option_\d+", key)) == 1:
            validate_option(container_name=container_name, values=items)
        if len(re.findall(r"^group_\d+", key)) == 1:
            validate_group(container_name=container_name, values=items)


def validate_group(container_name=None, values=None):
        if values is None or len(values) == 0:
            print(f"WARNING: {container_name} has section that is empty. Please remove")
            return
        
        required_keys = ['env_name', 'field_combine']

        for key, item in values.items():
            if key not in required_keys and not len(re.findall(r"^group_\d+", key)) == 1 and not len(re.findall(r"^option_\d+", key)) == 1:
                raise ValueError(f"{container_name} group has group invalid key {key}")
            elif len(re.findall(r"^group_\d+", key)) == 1:
                validate_group(container_name=container_name, values=item)
            elif len(re.findall(r"^option_\d+", key)) == 1:
                validate_option(container_name=container_name, values=item, as_group=True)
            elif not len(re.findall(r"^group_\d+", key)) == 1 and key in required_keys:
                required_keys.remove(key)
                if not isinstance(item, str):
                    raise ValueError(f"{container_name} group has group invalid key {key}")
            else:
                raise ValueError(f"{container_name} group has group invalid key {key}")


def validate_option(container_name=None, values=None, as_group=False):
    if values is None or len(values) == 0:
        print(f"WARNING: {container_name} has section that is empty. Please remove")
        return
     # now run through all keys
    required_keys = ['display_name', 'user_description', 'env_name', 'default_value']
    valid_keys = ['addtional_setup_required', 'bypass_yaml', 'replace_character', 'display_name', 'user_description', 'env_name', 'disable_user_set', 'default_value', 'variable_type', 'boolean_override_true', 'boolean_override_false', 'multi_choice_options', 'user_required', 'compose_required', 'advanced', 'validator', 'user_required_description', 'bypass_yaml', 'replace_characters']
    # now lets add in all of the additional required keys based on certian options

    if 'variable_type' in values and values['variable_type'] == "multi-choice":
        required_keys.append('multi_choice_options')
        required_keys.remove('default_value')
    if 'variable_type' not in values or values['variable_type'] == "string":
        valid_keys.remove('boolean_override_true')
        valid_keys.remove('boolean_override_false')

    if as_group:
        required_keys.remove("env_name")

    for option_key, option_items in values.items():
        if option_key not in valid_keys:
           raise ValueError(f"{container_name} options has option invalid key {option_key}")

        if option_key == "loops" or option_key == "run_if" or option_key == "depends_on":
            # we've already validated these
            pass
        elif option_key == 'display_name':
            required_keys.remove('display_name')

            if not isinstance(option_items, str) and len(option_items) == 0:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        
        elif option_key == 'user_description':
            required_keys.remove('user_description')

            if not isinstance(option_items, str) and len(option_items) == 0:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        
        elif option_key == 'env_name':
            required_keys.remove('env_name')

            if not isinstance(option_items, str) and len(option_items) == 0:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")

        elif option_key == 'disable_user_set':
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a boolean")
        
        elif option_key == 'default_value':
            required_keys.remove('default_value')
            if 'variable_type' in values and values['variable_type'] == "multi-choice":
                raise ValueError(f"{container_name} options has option key {option_key} with 'variable_type' set to 'multi-choice'")
            elif 'variable_type' in values:
                option_variable_type = values['variable_type']
            else:
                option_variable_type = "string"
            if (option_variable_type and isinstance(option_items, str)) or (option_variable_type == "boolean" and isinstance(option_items, bool)):
                # this is valid
                pass
            else:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string or boolean")
        
        elif option_key == 'variable_type':
            if not isinstance(option_items, str) and (option_items == "boolean" or option_items == "string" or option_items == "multi-choice"):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        
        elif option_key.startswith('boolean_override_'):
            if not isinstance(option_items, str):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        
        elif option_key == 'multi_choice_options':
            if 'variable_type' not in values or values['variable_type'] != "multi-choice":
                raise ValueError(f"{container_name} options has option invalid key {option_key}. multi_choice_options included but variable_type is not multi-choice")
            required_keys.remove("multi_choice_options")
            for sub_key, sub_items in option_items.items():
                if len(re.findall(r"^option_\d+", sub_key)):
                    if "user_text" not in sub_items and "env_text" not in sub_items:
                        raise ValueError(f"{container_name} {sub_key} is invalid. Should contain user_text and env_text.")
                    for multi_option_key, multi_option_items in sub_items.items():
                        if multi_option_key != "user_text" and multi_option_key != "env_text":
                            raise ValueError(f"{container_name} has invalid key {sub_key}/{multi_option_key}")
                        elif not isinstance(multi_option_items, str) and len(multi_option_items) == 0:
                            raise ValueError(f"{container_name} {multi_option_key} should be a non-blank string")
                else:
                    raise ValueError(f"{container_name} has option invalid key {sub_key}.")
        
        elif option_key == "user_required":
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a boolean")
        
        elif option_key == "compose_required":
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} optionshas option invalid key {option_key}. Should be a boolean")
        
        elif option_key == "advanced":
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a boolean")
        
        elif option_key == "validator":
            if not isinstance(option_items, str) and len(option_items) == 0:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        
        elif option_key == "user_required_description":
            if not isinstance(option_items, str) and len(option_items) == 0:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a non-blank string")
        elif option_key == "bypass_yaml":
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a boolean")
        elif option_key == "replace_characters":
            if isinstance(option_items, list):
                for item in option_items:
                    if not isinstance(item, str):
                        raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a JSON array of strings")
            else:
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a JSON array")
        elif option_key == "addtional_setup_required":
            if not isinstance(option_items, bool):
                raise ValueError(f"{container_name} options has option invalid key {option_key}. Should be a boolean")
        elif re.findall(r"^group_\d+", option_key):
            if 'field_combine' in option_items:
                validate_group(container_name, option_items)
            else:
                validate_option(container_name=container_name, values=option_items)
        else:
            raise ValueError(f"{container_name} options has option invalid key {option_key}.")

    # Function to validate the devices
    if len(required_keys) != 0:
        missing_keys = ", ".join(item for item in required_keys)
        raise ValueError(f"Missing keys: {missing_keys}")


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
                elif key_port == "description" and isinstance(key_items, str):
                    # this is valid
                    pass
                elif key_port == "exclude" and isinstance(key_items, bool):
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
            recs_req.append(items)
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
            for a in recs_req:
                if a not in containers:
                    print(f"****WARNING: container {a} was recommended/required but not found in config file")
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
