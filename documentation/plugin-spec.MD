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
    docker_config_version: 1.0,
    container {
        config_version: 1.0,
        container_name: "name_of_container",
        container_display_name: "Name of Container",
        container_image: "image",
        container_config {

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

This section of the configuration file is used to define the configuration parameters of the 