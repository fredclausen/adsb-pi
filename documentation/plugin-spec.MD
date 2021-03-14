# **Plugin v1 Specs**

**DRAFT**

This document is designed to go over the Version 1 spec of the docker-file plugin used by the SDR Docker config project.

## **Table of Contents**

* [Overview](#overview)
* [Best Practices](best-practices)
* [General Structure of the file](#general-structure)
* [Container Config](#container-config)
  * [Recommends and Requirements](#recommends-and-requirements)
  * [Volumes](#volumes)
  * [Ports](#ports)
  * [Sections](#sections)
    * [Conditional Execution of a Section](#conditional-execution-of-a-section)
    * [Depends On](#depends-on)
    * [Run If](#run-if)
    * [Loops](#loops)
    * [Groups](#groups)
  * [Validating User Input](#validating-user-input)
* [Sample Configuration](#sample-config)

## **Overview and Best Practices**

The goal of this project is to provide an easy to use, extensible website that an end user can use to quickly and seamlessly generate docker-compose files that they can use in their infrastructure. The idea is to provide the user a functional docker-compose file, built on their responses to questions, that should deploy a workable container.

In order to facilitate this, and to make the project scalable and usable far in to the future, the "brain" of this is going to be author-provided plugin(s) for their containers that describe how the user needs to configure their container. The thought process behind the plugin architecture is to allow a docker container author to specify the configuration options for a container that the web front end can use to assist the user in generating docker-compose files.

The plugin file is set up in JSON format and uses JSON conventions. Many containers can be defined in the plugin file.

## Best Practices

For best practices, it is best to design your plugins to cover only the really necessary configuration items. The term `sections` and `options` will be defined below in more detail, but if your container requires any default ENV variables that have to be set, but not specified by the user, it would be best to include them in their own section and set the appropriate flag so that the web front end includes them without asking the user to configure the option. It is best to leave "advanced" configuration for the user to do outside of the tool. The objective is to create a workable compose file that meets most user's needs.

Addtionally, while not required, it is best practice for any free-text inputs the user is required to use to provide a regex string to validate the input. This is covered below.

Anywhere you see `description` as a setting, this will be displayed to the user on the website. Use this to inform them about what that step is and/or what value(s) they are expected to provide.

## **General Structure**

This section is used to define the plugin and any container config(s) that are available.

The plugin file will start out with the following items:

```json
{
    "docker_config_version": 1.0,
    "container_1": {
        "config_version": 1.0,
        "container_name": "name_of_container",
        "container_display_name": "Name of Container",
        "container_image": "image",
        "container_website": "url",
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

## **Container Config**

### **Recommends and Requirements**

This section of the configuration file is used to define the parameters of a container.

Example:

```json
{
    "container_1": {
        <snip>
        "container_config": {
            "description": "value",
            "requires": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            },
            "recommends": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            },
            "volumes": {
                "usb": true,
                "volume1": {
                    "docker_volume_name": "path",
                    "container_path": "path"
                }
            },
            "ports": {
                "port1": {
                    "host_port": port,
                    "container_port": port
                }
            }
            "section1": {
                <snip>
            }     
        }
    }
}
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `description` | This value is used to inform the user what the next steps of configuration are. | Yes | `lower-case, ASCII letters, - and _` |
|`requires` | This section describes the containers that are **REQUIRED** to be also installed to run the container being configured. This is used by the web front-end to inform the user about requirements. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the required container |
|`recommends` | This section describes the containers that are **RECOMMENDED**, but not required, to run the container being configured. This is used by the web front-end to inform the user about suggestion(s) they may also want to install to enhance and/or improve the container being configured. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the recommended container |

### **Volumes**

If your container requires volumes, include this configuration in the plugin.

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `usb` | Pass in the host USB bus to the container. Default is `false` | No | `boolean` |
| `docker_volume_name` | The name of the docker volume for the container | No | `Standard docker volume naming` |
| `container_path` | The path the `docker_volume_name` should be mapped to in the container | Yes, if `docker_volume_name` is included | `Standard unix path naming` |

### **Ports**

If your container requires port mapping, include this section. By default, the `container_port` is mapped to the Host Port as well in the docker-compose file, but the user will be given an option to change this. Also, the front end will check for duplicate host ports and require the user to change mappings, so there is no requirement for plugin developers to ensure their port mappings are unique.

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `container_port` | The container port that will be mapped to the `host_port` | No | `Integer` |


### **Sections**

The next part we'll define sections of the configuration. This is used to define cohesive container ENV elements that should be grouped together. General useage of this would be to define "global" type configuration options for the container, a group of options that is optional and/or required based on other options configured, a group of options that may be repeated based on user selections, etc.

Sections are executed in order, and depend on the previous section for certain things.

Example:

```json
<snip>
                "section1": {
                    "description": "value",
                    "user_skip": "true",
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
                        <snip>
                    }
                }
<snip>
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `description` | This value is used to inform the user what the next steps of configuration are. | No | `lower-case, ASCII letters, - and _` |
| `user_skip` | If set, this value skips asking the user about the `options` in this section and will just write the default values set for the `options` in this section in to the final docker-compose. This over-rides `user_required`, `loops`, `run_if` and `depends_on` | No | `boolean` |

#### **Conditional Execution of a Section**

You have two options to conditionally run a section. Neither is required, but if you want to run a section conditonally you cannot choose both `depends_on` or and `run_if` - it is one or the other.

#### **Depends On**

The first conditional execution section is `depends_on`. `depends_on` is used if you want to run a section based a previous user response to an ENV variable. An example useage of this would be if the user selected a non-default value for an ENV variable and now the container requires additional configuration options. `env_name` and `env_name_value` are dependent on those values existing in a previous section.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `depends_on` | Used to indicate if the section is dependent on previous user responses | No | None | Blank |
| `env_name` | The name of the option that will trigger this section being included in the docker-compose | Yes, if `depends_on` is included in the section configuraton AND `run_if` is not included | `ENV name of the value being checked to see if the section should be run` | Blank |
| `env_name_value` | The value that will trigger the section to be run | No | `container's variable spec` | Not `default_value` of the `env_name` variable being checked |

#### **Run If**

The next conditional execution is the `run_if`, and if `run_if` is included, it is recommended to include the `loops` section. This section will ask the user a question, and then based on their response will configure the options in this section. After that is done, the user is asked the `user_question_after` and based on their response, will run the section again based on the configuration options in the loop section.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `run_ if` | If this section should be run based on a user's response to a question (ie, "Do you have another SDR you'd like to set up?"), include this. | Yes, if `run_if` is included and `depends_on` is not included. | None | Blank |
| `user_question` | The first question that is asked of a user. IE "Would you like to set up an SDR now?" | Yes, if `run_if` section is included | `ASCII text` | Blank |
| `user_question_after` | The subsequent question asked to the user. IE "Do you have another SDR you'd like to set up?" | No | `ASCII text` | Set to the same value as `user_question` |

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
                        "Would you like to add more options?"
                    },
                    "group:" {
                        "env_name": "variable",
                        "field_combine": ",",
                        "option1": {
                            "display_name": "display_name",
                            "description": "description",
                            "default_value": "default",
                            "user_required": "true",
                        },
                        "option2": {
                            "display_name": "display_name",
                            "description": "description",
                            "default_value": "default",
                            "user_required": "true",
                        }
                    }
                }
```

In the example above, the ENV variable would end up looking like this:

```shell

variable=loop1_response_to_option1,loop1_response_to_option2;loop2_response_to_option1,loop2_response_to_option2

```

#### Options

Below is the configuration for an environment variable in a section, also known as `options`.

```json
<snip>
                "section1": {
                    "option1": {
                        "display_name": "display_name",
                        "description": "description",
                        "env_name": "environment_variable",
                        "default_value": "default",
                        "variable_type": "boolean",
                        "boolean_override_true": "value",
                        "boolean_override_false": "false",
                        "user_required": "true",
                        "compose-required": "true"
                    }
                }
<snip>
```

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `display_name` | The name of the configuration option displayed to the user | Yes | `ASCII characters` | None |
| `description` | Description of what this variable does and any information needed for the user to provide their own value. | Yes | `ASCII Characters` | None |
| `env_name` | The name of the ENV variable that will be in the docker-compose file. If the variable is used for looping (see [section](#section) above), the placeholder `[]` is used for the incrementing character in the variable name. | Yes | `Standard docker ENV naming conventions` | None |
| `disable_user_set` | Set this option to disable allowing the user to change this variable. Use of this means the variable, with it's default value, will be included in the docker-compose output. | No | `false` |
| `default_value` | The default value of the enviornment variable. Will (potentially) be used if the user provides no change to the option. Is displayed to the user. | Yes | `Formatting per container spec for the variable` | None |
| `variable_type` | This sets the type of variable. | No | `boolean` or `string` | `string` |
| `boolean_override_true` and `boolean_override_false` | By default the output for any variable set to boolean will be `TRUE` or `FALSE` depending on what is appropriate. However, if your container uses a different value (ie, a blank string) to represent the `TRUE` and/or `FALSE` state, you can override the output for that selection type. | No | `Formatting per container spec for the variable` | `true` and `false` respectively |
| `user_required` | This is used to indicate the user is required to provide unique input. | No | `true` or `false` | `false` |
| `compose-required` | This is used to indicate that writing the variable, even if the default value is used, should be included in the docker-compose file. Note: if the user provides input on the value the variable will always be included in the output | `true` or `false` | `false` |

### **Groups**

If you wish to combine several questions in to a ENV variable, use the `group` option.

Example

```json
<snip>
                    "group:" {
                        "env_name": "environment_variable",
                        "field_combine": ",",
                        "option1": {
                            "display_name": "display_name",
                            "description": "description",
                            "default_value": "default",
                            "user_required": "true",
                        },
                        "option2": {
                            "display_name": "display_name",
                            "description": "description",
                            "default_value": "default",
                            "user_required": "true",
                        }
                    }
<snip>
```

All of the settings under `option` in a `group` are the same as if they were not in a group, with the exception of `boolean` is not a valid type in this section. All response types are assumed to be `string`.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `env_name` | In this section, the `env_name` is moved from the option to the `group`, and sets the output enviornment variable that all of the options in the `group` section will be applied to. | Yes, if `group` is used. | `docker ENV variable naming convention` | Blank |
| `field_combine` | All of the option responses will be combined together and separated with the character(s) in the `field_combine` variable | Yes, if `group` is being used. | `ASCII characters, - _` | Blank |

### Validating User Input

By default, all `string` based user-inputs are considered valid. However, any place that a user input can have the field `validator` applied to it.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `validator` | A regex string that will be used by the front-end to validate that the user input is in the format required for the ENV vairable. With out specifying this option, all input is considered valid. | No | `/regex string/` | Blank |

## **Sample Config**

Putting it all together, we have a sample configuration file that will define three containers

