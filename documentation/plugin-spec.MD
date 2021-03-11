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
| `container_name` | This is the the internal name of the container and will be used by the web front-end as an internal value to reference the container. | Yes | `lower-case, ASCII letters, - and _` |
| `container_display_name` | The friendly name of the container displayed to the user | Yes | `Upper and lower case, ASCII, _ - and spaces` | Yes | `lower-case, ASCII letters, - and _` |
| `container_image` | The dockerhub, or applicable, path to the image | Yes | `standard formatting for docker-images` |
| `container_config` | The section where you will define the configuration parameters for the container. Described [below](#container-config) | Yes | None |

### Container Config

#### Recommends and Requirements

This section of the configuration file is used to define the parameters of a container.

Example:

```
{
    <snip>
        "container_config": {
            "description: "value",
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
| `description` | This value is used to inform the user what the next steps of configuration are. | Yes | `lower-case, ASCII letters, - and _` |
|`requires` | This section describes the containers that are **REQUIRED** to be also installed to run the container being configured. This is used by the web front-end to inform the user about requirements. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the required container |
|`recommends` | This section describes the containers that are **RECOMMENDED**, but not required, to run the container being configured. This is used by the web front-end to inform the user about suggestion(s) they may also want to install to enhance or improve the container being configured. | No | `JSON list of container(s). Use the same name as supplied in the container_name configuration of the recommended container |

##### Sections

The next part we'll define sections of the configuration. This is used to define cohesive container ENV elements that should be grouped together. General useage of this would be to define "global" type configuration options for the container, a group of options that is optional and/or required based on other options configured, a group of options that may be repeated based on user selections, etc.

Sections are executed in order, and depend on the previous section for certain things.

Example:

```
<snip>
                "section1": {
                    "description": "value",
                    "depends_on": {
                        "option": "env_name",
                        "option_value": "value",
                    },
                    "run_if": {
                        "user_question": "question",
                        "user_question_after": "question"
                    },
                    "loops": {
                            "max_loops": 10,
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
| `description` | This value is used to inform the user what the next steps of configuration are. | Yes | `lower-case, ASCII letters, - and _` |

You have two options to conditionally run a section. Neither is required, but if you want to run a section conditonally you cannot choose both `depends_on` or and `run_if` - it is one or the other.

The first conditional execution section is `depends_on`. `depends_on` is used if you want to run a section based a previous user response to an ENV variable. An example useage of this would be if the user selected a non-default value for an ENV variable and now the container requires additional configuration options. `env_name` and `env_name_value` are dependent on those values existing in a previous section.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `depends_on` | Used to indicate if the section is dependent on previous user responses | No | None | Blank |
| `env_name` | The name of the option that will trigger this section being included in the docker-compose | Yes, if `depends_on` is included in the section configuraton AND `run_if` is not included | `ENV name of the value being checked to see if the section should be run` | Blank |
| `env_name_value` | The value that will trigger the section to be run | No | `container's variable spec` | Not `default_value` of the `env_name` variable being checked |

The next conditional execution is the `run_if`, and if `run_if` is included, it is recommended to include the `loops` section. This section will ask the user a question, and then based on their response will configure the options in this section. After that is done, the user is asked the `user_question_after` and based on their response, will run the section again based on the configuration options in the loop section.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `run_ if` | If this section should be run based on a user's response to a question (ie, "Do you have another SDR you'd like to set up?"), include this. | Yes, if `run_if` is included and `depends_on` is not included. | None | Blank |
| `user_question` | The first question that is asked of a user. IE "Would you like to set up an SDR now?" | Yes, if `run_if` section is included | `ASCII text` | Blank |
| `user_question_after` | The subsequent question asked to the user. IE "Do you have another SDR you'd like to set up?" | No | `ASCII text` | Set to the same value as `user_question` |

`loops` configures how each run of the section is handled and is **recommended** if `run_if` is included. This section is ignored if `run_if` is excluded. The idea here is that the variable names in this section should change in some way, and potentially have a maximum number of times the loop should execute.

| Variable | Description | Required | Formatting | Default |
| -------- | ----------- | -------- | ---------- | ------- |
| `max_loops` | The maximum number of times the loop should be run | No | `Integer` | `Infinity` |
| `starting_value` | Each ENV variable/option that is included in the section should include a placeholder (`[]`) that will be incremented for each iteration of the loop. This sets the default value. | No | `Integer` | `0` |

#### Options

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
| `default_value` | The default value of the enviornment variable. Will (potentially) be used if the user provides no change to the option. Is displayed to the user. | Yes | `Formatting per container spec for the variable` | None |
| `variable_type` | This sets the type of variable. | No | `boolean` or `string` | `string` |
| `boolean_override_true` and `boolean_override_false` | By default the output for any variable set to boolean will be `TRUE` or `FALSE` depending on what is appropriate. However, if your container uses a different value (ie, a blank string) to represent the `TRUE` and/or `FALSE` state, you can override the output for that selection type. | No | `Formatting per container spec for the variable` | `true` and `false` respectively |
| `user_required` | This is used to indicate the user is required to provide unique input. | No | `true` or `false` | `false` |
| `compose-required` | This is used to indicate that writing the variable, even if the default value is used, should be included in the docker-compose file. Note: if the user provides input on the value the variable will always be included in the output | `true` or `false` | `false` |