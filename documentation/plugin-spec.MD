# Plugin v1 Specs

This document is designed to go over the Version 1 spec of the docker-file plugin used by the SDR Docker config project.

## Table of Contents

* [Overview](#overview)
  * [General Structure of the file](#general-structure
)
  * [Container Config](#container-config)

### Overview

The thought process beind the plugin architecture is to allow a docker container author to specify the configuration options for a container that the web front end can use to assist the user in generating docker-compose files.

The file is set up in JSON format and uses JSON conventions. Many containers can be defined in the plugin file.

### The File

#### General Structure

This section is used to define the plugin and any container config(s) that are available.

The plugin file will start out with the following items:

```
{
    "docker_config_version": 1.0,
    "container": {
        "config_version": 1.0,
        "container_name": "name_of_container",
        "container_display_name": "Name of Container",
        "container_image": "image",
        "container_config": {

        }
    }
}
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
| `docker_config_version` | This variable sets the plugin spec version number. For now, only `1.0` is an acceptable value, but in the future if the spec document is changed, this will be used by the parser to determine how to process the plugin | Yes | `Float` |
| `config_version` | This sets the configuration version of the plugin itself. This is not used for anything in the parser, but can be used by the plugin developer to track additions/changes to their container. | No | `Float`
| `container_name` | This is the the internal name of the container and will be used by the web front-end as an internal value to reference the container. |
| `container_display_name` | The friendly name of the container displayed to the user | Yes | `Upper and lower case, ASCII, _ - and spaces` |
| Yes | `lower-case, ASCII letters, - and _` |
| `container_image` | The dockerhub, or applicable, path to the image | Yes | `standard formatting for docker-images` |
| `container_config` | The section where you will define the configuration parameters for the container. Described [below](#container-config) | Yes | None |

#### Container Config

##### Recommends and Requirements

This section of the configuration file is used to define the configuration parameters of a container.

Example:

```
{
    <snip>
        "container_config": {
            "requires": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            },
            "recommends": {
                "container_1": { "container_name": "name_of_container" },
                "container_2": { "container_name": "name_of_second_container" }
            }
            <snip>
        }
    }
}
```

| Variable | Description | Required | Formatting |
| -------- | ----------- | -------- | ---------- |
|`requires` | This section describes the containers that are **REQUIRED** to be also installed to run the container being configured. This is used by the web front-end to inform the user about requirements. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the required container |
|`recommends` | This section describes the containers that are **RECOMMENDED**, but not required, to run the container being configured. This is used by the web front-end to inform the user about suggestion(s) they may also want to install to enhance or improve the container being configured. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the recommended container |

##### Sections

The next part we'll define sections of the configuration. This is used to define cohesive container ENV elements that should be grouped together. General useage of this would be to define "global" type configuration options for the container, a group of options that is optional or required based on other options configured, a group of options that may be repeated based on user selections, etc.

Example:

```
<snip>
                "section1": {
                    "depends_on": {
                        "section": "section2",
                        "option": "env_name",
                        "loops": {
                            "should_loop": "true",
                            
                        }
                    }
                    "option1": {
                        <snip>
                    }
                }
<snip>
```



##### Options

Below is the configuration for an environment variable in a section.

```
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
| `default_value` | The default value of the enviornment variable. Will (potentially) be used if the user provides no change to the option | Yes | `Formatting per container spec for the variable` | None |
| `variable_type` | This sets the type of variable. | No | `boolean` or `string` | `string` |
| `boolean_override_true` and `boolean_override_false` | By default the output for any variable set to boolean will be `TRUE` or `FALSE` depending on what is appropriate. However, if your container uses a different value (ie, a blank string) to represent the `TRUE` and/or `FALSE` state, you can override the output for that selection type. | No | `Formatting per container spec for the variable` | `true` and `false` respectively |
| `user_required` | This is used to indicate the user is required to provide unique input. | No | `true` or `false` | `false` |
| `compose-required` | This is used to indicate that writing the variable, even if the default value is used, should be included in the docker-compose file. Note: if the user provides input on the value the variable will always be included in the output | `true` or `false` | `false` |