# **Plugin v1 Specs**

**DRAFT**

This document is designed to go over the Version 1 spec of the docker-file plugin used by the SDR Docker config project.

## **Table of Contents**

* [Overview](#overview)
* [Best Practices](best-practices)
* [General Structure of the file](#general-structure)
* [Categories](#categories)
* [Global Variables](#global-variables)
* [Container Config](#container-config)
  * [Recommends and Requirements](#recommends-and-requirements)
  * [Volumes](#volumes)
  * [Ports](#ports)
  * [Devices](#devices)
  * [Sections](#sections)
    * [Conditional Execution of a Section](#conditional-execution-of-a-section)
    * [Depends On](#depends-on)
    * [Run If](#run-if)
    * [Loops](#loops)
    * [Groups](#groups)
  * [Template Variables](#template-variables)
  * [Validating User Input](#validating-user-input)
  * [Special YAML Cases](#special-yaml-cases)
  * [Beautifying Text Displayed to User](#beautifying-text-displayed-to-user)
  * [Post Install Actions](#post-install-actions)
* [Sample Configuration](#sample-config)

## **Overview and Best Practices**

The goal of this project is to provide an easy to use, highly configurable set of tools that an end user can use to quickly and seamlessly set up a system to use their SDR dongles.

To this end, part of the tool set required is a tool to generate docker-compose files that they can use in their infrastructure. The idea is to provide the user a functional docker-compose file, built on their responses to questions, that should deploy a workable container.

In order to facilitate this, and to make the project scalable and usable far in to the future, the "brain" of this is going to be author-provided plugin(s) for their containers that describe how the user needs to configure their container. The thought process behind the plugin architecture is to allow a docker container author to specify the configuration options for a container that allows any tool that uses this plugin spec to assist the user in generating docker-compose files.

The plugin file is set up in `JSON` format and uses `JSON` conventions. Many containers can be defined in the plugin file. In general, all containers in a plugin file should be presented in alphabetical order as not all clients using the plugins will sort the containers before presenting them to the user.

## Best Practices

It is best to design your plugins to cover only the really necessary configuration items. The term `sections` and `options` will be defined [below](#sections) in more detail, but if your container requires any default ENV variables that have to be set, but not specified by the user, it would be best to include them in their own section and set the appropriate flag so that the web front end includes them without asking the user to configure the option.

The primary mode of operation for this tool should be to set up a basic configuration of your container that works for most users. As such, more advanced configuration settings should either be not included, included but set as `disable_user_set` (which allows for writing of the default value specified in the `option` configuration for the variable in to the docker-compose file), or should be exposed with `advanced` (which hides the option from the user unless they choose to configure advanced options, and also allows writing the default value if the flag is specified in the `option` configuration and the user is not using `advanced` config), and not required to be configured by default.

If you wish to expose options to the user, but only for `advanced` users, please set the appropriate flag on the option. This is covered in more detail [below](#sections).

Addtionally, while not required, it is best practice for any free-text inputs the user is required to use to provide a regex string to validate the input. This is covered [below](#validating-user-input).

Anywhere you see `user_description`, `user_required_formatting`, `user_question`, or `user_question_after` as a setting, this will be displayed to the user on the website. Use this to inform them about what that step is and/or what value(s) they are expected to provide. For formatting options, please see [below](#beautifying-text-displayed-to-user)

## **General Structure**

This section is used to define the plugin and any container config(s) that are available.

The plugin file will start out with the following items:

```json
{
    "docker_config_version": 1.0,
    "global_vars": {

    },
    "container_1": {
        "config_version": 1.0,
        "container_name": "name_of_container",
        "container_display_name": "Name of Container",
        "container_image": "image",
        "container_website": "url",
        "user_full_description": "text",
        "advanced": true,
        "container_config": {

        }
    }
}
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `docker_config_version` | This variable sets the plugin spec version number. For now, only `1.0` is an acceptable value, but in the future if the spec document is changed, this will be used by the parser to determine how to process the plugin | Yes | `Float` |
| `config_version` | This sets the configuration version of the plugin itself. This is not used for anything in the parser, but can be used by the plugin developer to track additions/changes to their container. | No | `Float`
| `container_name` | This is the the name of the container that will be used in the compose file. | Yes | `lower-case, ASCII letters, - and _` |
| `container_display_name` | The friendly name of the container displayed to the user | Yes | `Upper and lower case, ASCII, _ - and spaces` | Yes | `lower-case, ASCII letters, - and _` |
| `container_image` | The dockerhub, or applicable, path to the image | Yes | `standard formatting for docker-images` |
| `container_website` | The URL for the container's website | No | `standard URL formatting` |
| `container_config` | The section where you will define the configuration parameters for the container. Described [below](#container-config) | Yes | None |
| `user_full_description` | This will provide a long form, more complete description of what the container does, requirements, etc. | Yes | `String` |
| `advanced` | If your container has ONLY options that a user will be setting if they've selected `advanced` for the options then you can set this flag to bypass displaying configuration screens to the user and the default values will be written | No | `boolean` |

Addtionally, in this top level you will have `global_vars` and `categories`.

## Categories

Containers are required to be grouped in to categories. To define the categories for the plugin, use the structure:

```json
    "categories": {
        "required": "Required ADSB",
        "recommended": "Recommended ADSB SDR",
        "feeders": "ADSB Feeders",
        "misc": "Miscellancious Non-ADSB SDR receivers",
        "support": "Docker Support Tools"
    }
```

The key is the name of a category that the container will refer to, and the key value is the string that will be displayed to the user.

Under a container it is requisite to include the key `category` which refers to a key name defined in this section.

## Global Variables

Variables are covered more in depth in the [section](#sections), but at the top level of the json file you can define global variables that container's can grab a value from. This is useful for variables that should be globally applied such as `time zones`.

The global variable declaration follows the syntax of the `sections` with the exception that only the `options` can be used. There is no looping, groups, or anything else. Addtionally, there is one other kind of variable type not available to the container sections, which is `timezone`

The parser will attempt to grab the user's IANA timezone (aka standard Unix timezone format) from `/etc/localtime` or `/etc/timezone`. If neither can be found, the default value will be either `Etc/UTC`.

To apply a global variable in a container, for the default value use the following syntax:

```json
"global_vars": {
    # normal var options
    "env_name": "USER_TZ"
}
"container_1":
    "section_1":
        "option_1": {
            "env_name": "TZ",
            "default_value": "${USER_TZ}"
        }
    }
}
```

Where the value between the `{}` is the `env_name` present in the global_vars section.

The values set in the global section will be be written to a `.env` file.

## **Container Config**

### **Recommends and Requirements**

This section of the configuration file is used to define the parameters of a container.

Example:

```json
{
    "container_1": {
        "container_config": {
            "user_description": "value",
            "privileged": true,
            "network_mode": "host",
            "requires": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            },
            "recommends": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            },
            "volumes": {
                "volume_1": {
                    "docker_volume_name": "path",
                    "container_path": "path"
                }
            },
            "ports": {
                "port_1": {
                    "container_port": 000
                }
            },
            "devices": {
                "usb": true,
                "device_1": {
                    "host_device_path": "device_path",
                    "container_device_path": "path_in_container"
                }
            },
            "section1": {
            }
        }
    }
}
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `user_description` | This value is used to inform the user what the next steps of configuration are. | Yes | `lower-case, ASCII letters, markdown` |
| `privileged` | If your container requires the docker mode `privileged` to run, set this to `true`. Default is `false` | `boolean` |
| `network_mode` | If your container requires `host` network mode to run, set this to host. Default is `bridged` | No | `host` or `bridged` |
|`requires` | This section describes the containers that are **REQUIRED** to be also installed to run the container being configured. This is used by the web front-end to inform the user about requirements. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the required container |
|`recommends` | This section describes the containers that are **RECOMMENDED**, but not required, to run the container being configured. This is used by the web front-end to inform the user about suggestion(s) they may also want to install to enhance and/or improve the container being configured. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the recommended container |

### **Volumes**

If your container requires volumes, include this configuration in the plugin. You have two options for volumes in the container: `docker volume` and `tmpfs`.

To set up a `docker_volume` include the following under `volumes`

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `volume_x`| For each docker volume you want to create, include `volume_x`, , where x is an incremented number of devices you are passing in. | No | |
| `docker_volume_name` | The name of the docker volume for the container | No | `Standard docker volume naming` |
| `container_path` | The path the `docker_volume_name` should be mapped to in the container | Yes, if `docker_volume_name` is included | `Standard unix path naming` |
| `volume_options` | If you wish to specify options for the volume, ie to set a volume as local storage, include the YAML here. The parser does not format the data, so it should be correctly formatted YAML | No | `String/YAML` |
| `volume_override` | If set, the volume will not be created as a docker volume. Instead, whatever text is in this field will be set to the host path and mounted to the `container_path` | No | `String` |

If you wish to create a `tmpfs` volume, specify the following under `volumes`

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `tmpfs_x`| For each tmpfs volume you want to create, include `tmpfs_x`, , where x is an incremented number of devices you are passing in. | No | |
| `container_path` | The path in the container the `tmpfs` volume will be mapped to | Yes, if `tmpfs_x` is included |
| `tmpfs_options` | A string of options for creation of the tmpfs volume | Yes, `tmpfs_x` is included | `standard docker compose tmpfs options` |

Example

```json
"tmpfs_1": {
    "container_path": "/run",
    "tmpfs_options": "rw,nosuid,nodev,exec,relatime,size=64M,uid=1000,gid=1000"
}
```

Will produce the following in a docker-compose file

```yaml
tmpfs:
      - /run:rw,nosuid,nodev,exec,relatime,size=64M,uid=1000,gid=1000
```

### **Ports**

If your container requires port mapping, include this section. By default, the `container_port` is mapped to the Host Port as well in the docker-compose file, but the user will be given an option to change this. Also, the front end will check for duplicate host ports and require the user to change mappings, so there is no requirement for plugin developers to ensure their port mappings are unique.

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `container_port` | The container port that will be mapped to the `host_port` | No | `Integer` |
| `description` | Description of the port's useage. Will be displayed to the user | No | `string` |
| `exclude` | Do not include this port unless the user overrides it | No | `boolean` |

### **Devices**

If you need to pass any system hardware to the container, include this section.

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `usb` | Pass in the host USB bus to the container. Will map `- /dev/bus/usb:/dev/bus/usb/`. If you need another USB path, specify that via "device_x" option. Default is `false` | No | `boolean` |

For passing in a device path, specify the following

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `device_x` | For each hardware device you are passing in, us `device_x`, where x is an incremented number of devices you are passing in. | No | `JSON list` |
| `host_device_path` | The path on the host of the device you want to pass in | Yes, if `device_x` is included | `unix device path` |
| `container_device_path` | The path for the device in the container | Yes, if `device_x` is included | `unix device path` |

### **Sections**

The next part we'll define sections of the configuration. This is used to define cohesive container ENV elements that should be grouped together. General useage of this would be to define "global" type configuration options for the container, a group of options that is optional and/or required based on other options configured, a group of options that may be repeated based on user selections, etc.

Sections are executed in order, and depend on the previous section for certain things.

Example:

```json
                "section1": {
                    "user_description": "value",
                    "user_skip": true,
                    "depends_on": {
                        "option": "env_name",
                        "option_value": "value",
                    },
                    "run_if": {
                        "user_question": "question",
                        "user_question_after": "question",
                    },
                    "loops": {
                            "max_loops": 10,
                            "min_loops": 1,
                            "starting_value": 0,
                    },
                    "option1": {
                    }
                }
<snip>
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `user_description` | This value is used to inform the user what the next steps of configuration are. | No | `lower-case, ASCII letters, - and _` |
| `user_skip` | If set, this value skips asking the user about the `options` in this section and will just write the default values set for the `options` in this section in to the final docker-compose. This over-rides `user_required`, `loops`, `run_if` and `depends_on` | No | `boolean` |

#### **Conditional Execution of a Section**

You have two options to conditionally run a section. Neither is required, but if you want to run a section conditonally you cannot choose both `depends_on` or and `run_if` - it is one or the other.

#### **Depends On**

The first conditional execution section is `depends_on`. `depends_on` is used if you want to run a section based a previous user response to an ENV variable. The section will be run only once. An example useage of this would be if the user selected a non-default value for an ENV variable and now the container requires additional configuration options. `env_name` and `env_name_value` are dependent on those values existing in a previous section. This check for a user response only applies to the current container - it does not look at other container's values.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `depends_on` | Used to indicate if the section is dependent on previous user responses | No | None | Blank |
| `env_name` | The name of the option that will trigger this section being included in the docker-compose | Yes, if `depends_on` is included in the section configuraton | `ENV name of the value being checked to see if the section should be run` | Blank |
| `env_name_value` | The value that will trigger the section to be run | No | `container's variable spec` | Not `default_value` of the `env_name` variable being checked |

#### **Run If**

The next conditional execution is the `run_if`, and if `run_if` is included, it is recommended to include the `loops` section. This section will ask the user a question, and then based on their response will configure the options in this section. After that is done, the user is asked the `user_question_after` or `user_question` if `_after` is not included, and based on their response, will run the section again based on the configuration options in the loop section.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `run_ if` | If this section should be run based on a user's response to a question (ie, "Do you have another SDR you'd like to set up?"), include this. | Yes, if `run_if` is included and `depends_on` is not included. | None | Blank |
| `user_question` | The first question that is asked of a user. IE "Would you like to set up an SDR now?" | Yes, if `run_if` section is included | `ASCII text and markdown` | Blank |
| `user_question_after` | The subsequent question asked to the user. IE "Do you have another SDR you'd like to set up?" | No | `ASCII text and markdown` | Set to the same value as `user_question` |

#### **Loops**

`loops` configures how each run of the section is handled and is **recommended** if `run_if` is included. This section is ignored if `run_if` is excluded. The idea here is that the variable names in this section should change in some way if the loop is going to iterate more than once, and potentially have a maximum number of times the loop should execute.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `max_loops` | The maximum number of times the loop should be run | No | `Integer` | `Infinity` |
| `min_loops` | The minimum number of times the loop should be run | No | `Integer` | `0` |
| `starting_value` | Each ENV variable/option that is included in the section should include a placeholder (`[]`) that will be incremented for each iteration of the loop. This sets the default value. | No | `Integer` | `0` |

Additionally, it may be required for a container to save the value of user responses to a variable. If you set `env_name` under a section, user responses for all options in the section will be saved to the variabled named in `env_name` and each response will be separated with the `field_combine`. Can also be used in conjunction with `group` (see [below](#groups)) to create nested responses.

Example below:

```json
<snip>
                "section1": {
                    "env_name": "variable",
                    "field_combine": ";",
                    "run_if": {
                        "user_question": "Would you like to add more options?"
                    },
                    "group_1": {
                        "env_name": "variable",
                        "field_combine": ",",
                        "option_1": {
                            "display_name": "display_name",
                            "user_description": "description",
                            "default_value": "default",
                            "user_required": true,
                        },
                        "option_2": {
                            "display_name": "display_name",
                            "user_description": "description",
                            "default_value": "default",
                            "user_required": true,
                        }
                    }
                }
```

In the example above, the ENV variable would end up looking like this:

```yaml
- variable=loop1_response_to_option1,loop1_response_to_option2;loop2_response_to_option1,loop2_response_to_option2
```

#### **Options**

Below is the configuration for an environment variable in a section, also known as `options`.

```json
<snip>
                "section1": {
                    "option_1": {
                        "display_name": "display_name",
                        "user_description": "description",
                        "env_name": "environment_variable",
                        "default_value": "default",
                        "variable_type": "boolean",
                        "boolean_override_true": "value",
                        "boolean_override_false": "value",
                        "user_required": true,
                        "compose_required": true,
                        "advanced": true
                    }
                }
<snip>
```

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `display_name` | The name of the configuration option displayed to the user | Yes | `ASCII characters` | None |
| `user_description` | Description of what this variable does and any information needed for the user to provide their own value. | Yes | `ASCII Characters and markdown` | None |
| `env_name` | The name of the ENV variable that will be in the docker-compose file. If the variable is used for looping (see [section](#section) above), the placeholder `[]` is used for the incrementing character in the variable name. | Yes | `Standard docker ENV naming conventions` | None |
| `disable_user_set` | Set this option to disable allowing the user to change this variable. Use of this means the variable, with it's default value, will be included in the docker-compose output. | No | `boolean` | `false` |
| `default_value` | The default value of the enviornment variable. Will (potentially) be used if the user provides no change to the option. Is displayed to the user. | Yes, `variable_type` is not `multi_choice_options` | `Formatting per container spec for the variable` | None |
| `variable_type` | This sets the type of variable. | No | `boolean`, `string`, `serial` (see notes below) or `multi-choice` (see notes below) | `string` |
| `boolean_override_true` and `boolean_override_false` | By default the output for any variable set to boolean will be `TRUE` or `FALSE` depending on what is appropriate. However, if your container uses a different value (ie, a blank string) to represent the `TRUE` and/or `FALSE` state, you can override the output for that selection type. | No | `Formatting per container spec for the variable` | `true` and `false` respectively |
| `multi_choice_options` | A JSON list of user options that can be selected for the variable. Will be presented to the user via a dropdown menu. See below for formatting of the variable. | Yes, if `variable_type` is set to `multi-choice` | `JSON List` | Blank |
| `user_required` | This is used to indicate the user is required to provide unique input. If `advanced` is set to `true` the user will be required to provide input **ONLY** if the user is in `advanced` configuration mode. | No | `true` or `false` | `false` |
| `compose_required` | This is used to indicate that writing the variable, even if the default value is used, should be included in the docker-compose file. Note: if the user provides input on the value the variable will always be included in the output | No | `boolean` | `false` |
| `advanced` | If this flag is set, the option will be presented to the user only if they've selected advanced configuration mode. | No | `boolean` | `false` |
| `additional_setup_required` | If this is set, and the user inputs the default value, the user will be informed that the container requires additional setup | No | `boolean` | `false` |
| `env` | If this flag is set the variable will be written to the .env file with the appropriate formatting of the variable in the `yaml` file and the name of the variable will have the container name prepended to it. | No | `boolean` | `false` |

If variable type is `serial` and the program has been provided with a list of serials available, the user will be shown those options. Once the user has selected a serial, any subsequent variables that are also `serial` will not have that number available to them.

If no serials have been made available the user will be prompted to enter a serial number.

The `multi_choice_options` list should be formatted as follows

```json
"multi_choice_options": {
    "option_1": { "user_text": "Text displayed to the user",
                  "env_text": "value_written_to_env_file" },
    "option_2": { "user_text": "Second option text displayed to the user",
                  "env_text": "alternative_value_written_to_env_file" },
}
```

### **Groups**

If you wish to combine several questions in to a ENV variable, use the `group` option.

Example

```json
<snip>
                    "group_1:" {
                        "env_name": "environment_variable",
                        "field_combine": ",",
                        "option1": {
                            "display_name": "display_name",
                            "user_description": "description",
                            "default_value": "default",
                            "user_required": true,
                        },
                        "option2": {
                            "display_name": "display_name",
                            "user_description": "description",
                            "default_value": "default",
                            "user_required": true,
                        }
                    }
<snip>
```

All of the settings under `option` in a `group` are the same as if they were not in a group, with the exception of `boolean` is not a valid type in this section. All response types are assumed to be `string`. The name of the group needs to be appended with a unique `integer`.

Groups can be nested.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `env_name` | In this section, the `env_name` is moved from the option to the `group`, and sets the output enviornment variable that all of the options in the `group` section will be applied to. | Yes, if `group` is used. | `docker ENV variable naming convention` | Blank |
| `field_combine` | All of the option responses will be combined together and separated with the character(s) in the `field_combine` variable | Yes, if `group` is being used. | `ASCII characters, - _` | Blank |

### Template Variables

If you have a variable that needs to be composed of values from different places you can use a template variable. These variables are never user-configurable and will be filled in when the config file is written.

Some situations you might want to use these include if a container was included and if a certain value in that container is set to a value. The basic idea is that you declare a template, and then set one or more includes. For each include that is found to be true, it will get added to the output variable.

```json

template_01: {
    "env_name_out": "name_out",
    "separator": ":",
    "include_01": {
        "container": "containername",
        "env_name": "name",
        "port": "port_number", # One of this line or the next two lines, but only one
        "value_is": "value", # include this
        "value_is_not": "" # or include this
    },
    "include_02": {
        "container": "containername",
        "env_name": "name",
        "port": "port_number", # One of this line or the next two lines, but only one
        "value_is": "value", # include this
        "value_is_not": "" # or include this,
        "value": "test"
    }
}
```

In the example above, `containername` has `name` set to `value` the output would be

```yaml
    - name_out: value:test
```

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `env_name_out` | The value that `template` will be written to | Yes | `string` | Blank |
| `separator` | If you need to separate the include fields with a delimiter include this. The seperator will **ONLY** be included between include elements, and will not preceed or end the variable.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `container` | The container where the `env_name` can be found | Yes | `string` | Blank |
| `env_name` | The name of the `env_variable` to check | Yes | `string` | Blank |
| `port` | If this is included the **container** port will be included in the `template` | No | `port_x` where `x` is the number of the port in the container | Blank |
| `value_is` | If included if the set value of the `env_name` is the value set here | `string` | Blank |
| `value_is_not` | Same as `value_is`, but the value has to be NOT what the value set here | `string` | Blank |
| `value` | If included, the value that will be written to the template will be the value set here. Only valid for `value_is(_not)` | No | `string` | Blank |

### **Validating User Input**

By default, all `string` based user-inputs are considered valid. However, any place that requires user input can have the field `validator` applied to it.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `validator` | A regex string that will be used by the front-end to validate that the user input is in the format required for the ENV vairable. With out specifying this option, all input is considered valid. | No | `/regex string/` | Blank |
| `user_required_description` | This field will be displayed to the user, if present, to inform the user how the data should be formatted for that `option` | No | `ASCII text and markdown` | Blank |

### Special YAML Cases

If your output variable would cause issues in YAML decoding because of special characters, or you want to byass YAML decoding you can include the following syntax to change out the variable is written to the docker-compose file.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `bypass_yaml` | Will set the output variable to by byassed | No | `Boolean` | `False` |
| `replace_characters` | List of characters that will be duplicated so that YAML parsing will work | No | `JSON Array of characters` | Blank |

Example

```json
{
    "option_1": {
        "env_name": "TEST",
        "bypass_yaml": true,
        "replace_characters": ["@", "$"]
    }
}

If the user inputs the value `test@$` the following will be written to docker-compose:

```yaml
-'TEST=test@@$$'
```

### **Beautifying Text Displayed to User**

For the following fields

* `user_question`
* `user_question_after`
* `user_description`
* `user_required_formatting`
* `user_full_description`

It may be desirable to apply text-formatting to enhance the readability of the text. Standard markdown syntax can be applied in the text strings of these fields. Not all clients that use the plugins will support the use of markdown, so any field that uses markdown should have `_markdown` appended to the field name, such as `user_question_markdown`. You should **always** include the non-markdown field, and if you want markdown, also include the markdown version of that setting. The client will choose the correct field to use. If no markdown field is present, the client will always use the appropriate non-markdown field.

### Post Install Actions

If your container requires any post installation commands to be run, ie create a directory, or a file, etc, you can input the command line terms to run in the `post_install_actions` keyword under the `container_X`. Addtionally, if you use `{path}` in the command list that will fill in the installation path. The `path` keyword should always end in the file system path folder delimiter.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `post_install_actions` | List of *nix commands that should be run post installation | No | `String` | Blank |
| `post_install_user_description` | By default the user will be asked if they want to run the command. This will variable will describe the actions about to be performed | Yes, if `post_install_actions` is included | `String` | Blank |

## **Sample Config**

Putting it all together, we have a sample configuration file that will define three containers
