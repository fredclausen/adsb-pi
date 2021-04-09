#!/usr/bin/env bash
# shellcheck disable=SC2028,SC1090,SC2016

# Disabled shellcheck check notes:
#   - SC1090: Can't follow non-constant source. Use a directive to specify location.
#       - There are files that are sourced that don't yet exist until runtime.
#   - SC2028: Echo may not expand escape sequences. Use printf.
#       - The way we write out the FR24 / Piaware expect script logs a tonne of these.
#       - We don't want the escape sequences expanded in this instance.
#       - There's probably a better way to write out the expect script (heredoc?)
#   - SC2016: Expressions don't expand in single quotes, use double quotes for that.
#       - This is by design when we're making the docker-compose.yml file

# TODOs
#  - support local RTLSDR
#  - support feeding from radarcape (need to update adsbx image)
#  - if compose file exists, use yq (in helper container) to modify the file in place - this prevents clobbering user customisations
#  - any inline TODOs
#
#----------------------------------------------------------------------------

# Original by github.com/mikenye
# Thanks Mike!

# Get PID of running instance of this script
export TOP_PID=$$

# Declar traps
trap cleanup EXIT
trap "exit 1" TERM

##### DEFINE GLOBALS #####

# Bash CLI Colors
NOCOLOR='\033[0m'
LIGHTRED='\033[1;31m'
LIGHTGREEN='\033[1;32m'
LIGHTBLUE='\033[1;34m'
WHITE='\033[1;37m'

# Version of this script's schema
CURRENT_SCHEMA_VERSION=1

# Regular Expressions
REGEX_PATTERN_RTLSDR_RULES_IDVENDOR='ATTRS\{idVendor\}=="\K[0-9a-f]{4}'
REGEX_PATTERN_RTLSDR_RULES_IDPRODUCT='ATTRS\{idProduct\}=="\K[0-9a-f]{4}'
REGEX_PATTERN_LSUSB_BUSNUMBER='^Bus \K\d{3}'
REGEX_PATTERN_LSUSB_DEVICENUMBER='^Bus \d{3} Device \K\d{3}'
REGEX_PATTERN_COMPOSEFILE_SCHEMA_HEADER='^\s*#\s*ADSB_DOCKER_INSTALL_ENVFILE_SCHEMA=\K\d+\s*$'

# File/dir locations
LOGFILE="/tmp/adsb_docker_install.$(date -Iseconds).log"

# Whiptail dialog globals
WHIPTAIL_BACKTITLE="ADS-B Docker Easy Install"

# Temp files - created in one dir
TMPDIR_ADSB_DOCKER_INSTALL="$(mktemp -d --suffix=.adsb_docker_install.TMPDIR_ADSB_DOCKER_INSTALL)"
TMPFILE_DOCKER_COMPOSE_SCRATCH="$TMPDIR_ADSB_DOCKER_INSTALL/TMPFILE_DOCKER_COMPOSE_SCRATCH"
# TMPFILE_NEWPREFS will be defined later
TMPFILE_NEWPREFS=

# Temp dirs - created in above main temp dir
TMPDIR_REPO_DOCKER_COMPOSE="$TMPDIR_ADSB_DOCKER_INSTALL/TMPDIR_REPO_DOCKER_COMPOSE"
mkdir -p "$TMPDIR_REPO_DOCKER_COMPOSE"
TMPDIR_REPO_RTLSDR="$TMPDIR_ADSB_DOCKER_INSTALL/TMPDIR_REPO_RTLSDR"
mkdir -p "$TMPDIR_ADSB_DOCKER_INSTALL"
mkdir -p "$TMPDIR_ADSB_DOCKER_INSTALL"

# Container Images
IMAGE_DOCKER_COMPOSE="linuxserver/docker-compose:latest"

# URLs
URL_REPO_RTLSDR="git://git.osmocom.org/rtl-sdr"

# List of RTL-SRD devices (will be populated by script)
RTLSDR_DEVICES=()

# List of kernel modules to blacklist on the host
RTLSDR_MODULES_TO_BLACKLIST=()
RTLSDR_MODULES_TO_BLACKLIST+=(rtl2832_sdr)
RTLSDR_MODULES_TO_BLACKLIST+=(dvb_usb_rtl28xxu)
RTLSDR_MODULES_TO_BLACKLIST+=(rtl2832)

# Default settings for .env file
DATASOURCE_TYPE=
FEED_ADSBX=
FEED_FLIGHTAWARE=
FEED_FLIGHTRADAR24=
FEED_OPENSKY=
FEED_PLANEFINDER=
FEED_RADARBOX=

# Cleanup function run on script exit (via trap)
function cleanup() {
    # NOTE: everything in this script should end with ' > /dev/null 2>&1 || true'
    #       this ensures any errors during cleanup are suppressed

    # Cleanup of temp files/dirs
    rm -r "$TMPDIR_ADSB_DOCKER_INSTALL" > /dev/null 2>&1 || true
}


##### DEFINE FUNCTIONS #####

function is_X_in_list_Y() {
    local list="$2"
    local item="$1"
    if [[ "$list" =~ (^|[[:space:]])"$item"($|[[:space:]]) ]] ; then
        # yes, list include item
        result=0
    else
        result=1
    fi
    return $result
}

function logger() {
    # Logs messages to the console
    # $1 = stage (string in square brackets at the beginning)
    # $2 = the message to log
    # ----------------------------
    echo "$(date -Iseconds) [$1] $2" >> "$LOGFILE"
}

function exit_failure() {
    echo ""
    echo "Installation has failed. A log file containing troubleshooting information is located at:"
    echo "$LOGFILE"
    echo "If opening a GitHub issue for assistance, be prepared to send this file in. however:"
    echo -e "${LIGHTRED}Please remember to remove any:"
    echo "  - email addresses"
    echo "  - usernames/passwords"
    echo "  - API keys / sharing keys / UUIDs"
    echo "  - your exact location in lat/long"
    echo -e "...and any other sensitive data before posting in a public forum!${NOCOLOR}"
    echo ""
    kill -s TERM $TOP_PID
}

function exit_user_cancelled() {
    echo ""
    echo "Installation has been cancelled. A log file containing troubleshooting information is located at:"
    echo "$LOGFILE"
    echo "If opening a GitHub issue for assistance, be prepared to send this file in. however:"
    echo -e "${LIGHTRED}Please remember to remove any:"
    echo "  - email addresses"
    echo "  - usernames/passwords"
    echo "  - API keys / sharing keys / UUIDs"
    echo "  - your exact location in lat/long"
    echo -e "...and any other sensitive data before posting in a public forum!${NOCOLOR}"
    echo ""
    kill -s TERM $TOP_PID
}

function welcome_msg() {
    msg=$(cat << "EOM"
  __
  \  \     _ _            _    ____  ____        ____
   \**\ ___\/ \          / \  |  _ \/ ___|      | __ )
  X*#####*+^^\_\        / _ \ | | | \___ \ _____|  _ \
   o/\  \              / ___ \| |_| |___) |_____| |_) |
      \__\            /_/   \_\____/|____/      |____/

Welcome to the SDR Easy Install Script! This will:

  1. Configure a source of ADS-B data (SDR or network)
  2. Install docker & docker-compose
  3. Prompt you for your feeder settings
  4. Create docker-compose.yml & .env files with your settings
  5. Deploy containers for feeding services you choose
     (and supporting containers)

Do you wish to continue?
EOM
)
    title="Welcome!"
    if whiptail \
        --backtitle "$WHIPTAIL_BACKTITLE" \
        --title "$title" \
        --yesno "$msg" \
        23 78; then
        :
        # user wants to proceed
    else
        exit_user_cancelled
    fi
}

function update_apt_repos() {
    logger "update_apt_repos" "Performing 'apt-get update'..."
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Performing 'apt-get update'..." 8 78
    if apt-get update -y >> "$LOGFILE" 2>&1; then
        logger "update_apt_repos" "'apt-get update' was successful!"
    fi
}

function install_with_apt() {
    # $1 = package name
    logger "install_with_apt" "Installing package $1..."
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Installing package '$1'..." 8 78
    # Attempt download of docker script
    if apt-get install -y "$1" >> "$LOGFILE" 2>&1; then
        logger "install_with_apt" "Package $1 installed successfully!"
    else
        logger "install_with_apt" "ERROR: Could not install package $1 via apt-get :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Could not install package $1 via apt-get :-(" 8 78
        exit_failure
    fi
}

function is_binary_installed() {
    # $1 = binary name
    # Check if binary is installed
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Checking if '$1' is installed..." 8 78
    logger "is_binary_installed" "Checking if $1 is installed"
    if which "$1" >> "$LOGFILE" 2>&1; then
        # binary is already installed
        logger "is_binary_installed" "$1 is already installed!"
    else
        return 1
    fi
}

function update_docker() {
    # Check to see if docker requires an update
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Checking if docker components require an update..." 8 78
    logger "update_docker" "Checking to see if docker components require an update"
    if [[ "$(apt-get -u --just-print upgrade | grep -c docker-ce)" -gt "0" ]]; then
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Docker components require an update..." 8 78
        logger "update_docker" "Docker components DO require an update"
        # Check if containers are running, if not, attempt to upgrade to latest version
        logger "update_docker" "Checking if containers are running"
        if [[ "$(docker ps -q)" -gt "0" ]]; then
            # Containers running, don't update
            logger "update_docker" "WARNING: Docker components require updating, but you have running containers. Not updating docker, you will need to do this manually."
            NEWT_COLORS='root=,yellow' \
                whiptail \
                    --backtitle "$WHIPTAIL_BACKTITLE" \
                    --title "Warning" \
                    --msgbox "Performing 'apt-get update'..." \
                    8 78

        else

            # Containers not running, do update
            logger "update_docker" "Docker components require an update. Performing update..."
            whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Docker components require an update. Performing update..." 8 78
            if apt-get upgrade -y docker-ce >> "$LOGFILE" 2>&1; then

                # Docker upgraded OK!
                logger "update_docker" "Docker upgraded successfully!"
                whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Docker upgraded successfully!" 8 78

            else

                # Docker upgrade failed
                logger "update_docker" "ERROR: Problem updating docker :-("
                NEWT_COLORS='root=,red' \
                whiptail \
                    --title "Error" \
                    --msgbox "Problem updating docker :-(" 8 78
                exit_failure

            fi
        fi

    else
        logger "update_docker" "Docker components are up-to-date!"
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Docker components are up-to-date!" 8 78
    fi
}

function install_docker() {

    # Docker is not installed
    logger "install_docker" "Installing docker..."
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Installing docker..." 8 78

    # Attempt download of docker script
    logger "install_docker" "Attempt download of get-docker.sh script"
    if curl -o /tmp/get-docker.sh -fsSL https://get.docker.com >> "$LOGFILE" 2>&1; then
        logger "install_docker" "get-docker.sh script downloaded OK"
    else
        logger "install_docker" "ERROR: Could not download get-docker.sh script from https://get.docker.com :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Could not download get-docker.sh script from https://get.docker.com :-(" 8 78
        exit_failure
    fi

    # Attempt to run docker script
    logger "install_docker" "Attempt to run get-docker.sh script"
    if sh /tmp/get-docker.sh >> "$LOGFILE" 2>&1; then
        logger "install_docker" "Docker installed successfully!"
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Docker installed successfully!" 8 78
    else
        logger "install_docker" "ERROR: Problem running get-docker.sh installation script :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Problem running get-docker.sh installation script :-(" 8 78
        exit_failure
    fi
}

function get_latest_docker_compose_version() {

    # get latest version of docker-compose
    logger "get_latest_docker_compose_version" "Querying for latest version of docker-compose..."
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Finding latest version of docker-compose..." 8 78

    if docker pull "$IMAGE_DOCKER_COMPOSE" >> "$LOGFILE" 2>&1; then
    :
    else
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Failed to pull (download) $IMAGE_DOCKER_COMPOSE :-(" 8 78
        exit_failure
    fi

    # get latest tag version from image
    logger "get_latest_docker_compose_version" "Attempting to get latest tag from cloned docker-compose git repo"
    if docker_compose_version_latest=$(docker run --rm -it "$IMAGE_DOCKER_COMPOSE" -version | cut -d ',' -f 1 | rev | cut -d ' ' -f 1 | rev); then
        # do nothing
        :
    else
        logger "get_latest_docker_compose_version" "ERROR: Problem getting latest docker-compose version :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Problem getting latest docker-compose version :-(" 8 78
        exit_failure
    fi

    export docker_compose_version_latest

}

function update_docker_compose() {
    local docker_compose_version

    # docker_compose is already installed
    logger "update_docker_compose" "docker-compose is already installed, attempting to get version information:"
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "docker-compose is already installed, attempting to get version..." 8 78
    if docker-compose version >> "$LOGFILE" 2>&1; then
        # do nothing
        :
    else
        logger "update_docker_compose" "ERROR: Problem getting docker-compose version :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Problem getting docker-compose version :-(" 8 78
        exit_failure
    fi
    docker_compose_version=$(docker-compose version | grep docker-compose | cut -d ',' -f 1 | rev | cut -d ' ' -f 1 | rev)

    # check version of docker-compose vs latest
    logger "update_docker_compose" "Checking version of installed docker-compose vs latest docker-compose"
    if [[ "$docker_compose_version" == "$docker_compose_version_latest" ]]; then
        logger "update_docker_compose" "docker-compose is the latest version!"
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "docker-compose is the latest version!" 8 78
    else

        # remove old versions of docker-compose
        logger "update_docker_compose" "Attempting to remove previous outdated versions of docker-compose..."
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Attempting to remove previous outdated versions of docker-compose..." 8 78
        while which docker-compose >> "$LOGFILE" 2>&1; do

            # if docker-compose was installed via apt-get
            if [[ $(dpkg --list | grep -c docker-compose) -gt "0" ]]; then
                logger "update_docker_compose" "Attempting 'apt-get remove -y docker-compose'..."
                if apt-get remove -y docker-compose >> "$LOGFILE" 2>&1; then
                    # do nothing
                    :
                else
                    logger "update_docker_compose" "ERROR: Problem uninstalling outdated docker-compose :-("
                    NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Problem uninstalling outdated docker-compose :-(" 8 78
                    exit_failure
                fi
            elif which pip >> "$LOGFILE" 2>&1; then
                if [[ $(pip list | grep -c docker-compose) -gt "0" ]]; then
                    logger "update_docker_compose" "Attempting 'pip uninstall -y docker-compose'..."
                    if pip uninstall -y docker-compose >> "$LOGFILE" 2>&1; then
                        # do nothing
                        :
                    else
                        logger "update_docker_compose" "ERROR: Problem uninstalling outdated docker-compose :-("
                        NEWT_COLORS='root=,red' \
                        whiptail \
                            --title "Error" \
                            --msgbox "Problem uninstalling outdated docker-compose :-(" 8 78
                        exit_failure
                    fi
                fi
            elif [[ -f "/usr/local/bin/docker-compose" ]]; then
                logger "update_docker_compose" "Attempting 'mv /usr/local/bin/docker-compose /usr/local/bin/docker-compose.oldversion'..."
                if mv -v "/usr/local/bin/docker-compose" "/usr/local/bin/docker-compose.oldversion.$(date +%s)" >> "$LOGFILE" 2>&1; then
                    # do nothing
                    :
                else
                    logger "update_docker_compose" "ERROR: Problem uninstalling outdated docker-compose :-("
                    NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Problem uninstalling outdated docker-compose :-(" 8 78
                    exit_failure
                fi
            else
                logger "update_docker_compose" "Unsupported docker-compose installation method detected."
                NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Problem uninstalling outdated docker-compose :-(" 8 78
                exit_failure
            fi
        done

        # Install current version of docker-compose as a container
        logger "update_docker_compose" "Installing docker-compose..."
        logger "update_docker_compose" "Attempting download of latest docker-compose container wrapper script"
        whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Attempting installation of docker-compose container wrapper..." 8 78

        # TODO - Change to official installer once it supports multi-arch
        # see: https://github.com/docker/compose/issues/6831
        #URL_DOCKER_COMPOSE_INSTALLER="https://github.com/docker/compose/releases/download/$docker_compose_version_latest/run.sh"
        URL_DOCKER_COMPOSE_INSTALLER="https://raw.githubusercontent.com/linuxserver/docker-docker-compose/master/run.sh"

        if curl -L --fail "$URL_DOCKER_COMPOSE_INSTALLER" -o /usr/local/bin/docker-compose >> "$LOGFILE" 2>&1; then
            logger "update_docker_compose" "Download of latest docker-compose container wrapper script was OK"

            # Make executable
            logger "update_docker_compose" "Attempting 'chmod a+x /usr/local/bin/docker-compose'..."
            if chmod -v a+x /usr/local/bin/docker-compose >> "$LOGFILE" 2>&1; then
                logger "update_docker_compose" "'chmod a+x /usr/local/bin/docker-compose' was successful"

                # Make sure we can now run docker-compose and it is the latest version
                docker_compose_version=$(docker-compose version | grep docker-compose | cut -d ',' -f 1 | rev | cut -d ' ' -f 1 | rev)
                if [[ "$docker_compose_version" == "$docker_compose_version_latest" ]]; then
                    logger "update_docker_compose" "docker-compose installed successfully!"
                    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "docker-compose installed successfully!" 8 78
                else
                    logger "update_docker_compose" "ERROR: Issue running newly installed docker-compose :-("
                    NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Issue running newly installed docker-compose :-(" 8 78
                    exit_failure
                fi
            else
                logger "update_docker_compose" "ERROR: Problem chmodding docker-compose container wrapper script :-("
                NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Problem chmodding docker-compose container wrapper script :-(" 8 78
                exit_failure
            fi
        else
            logger "update_docker_compose" "ERROR: Problem downloading docker-compose container wrapper script :-("
            NEWT_COLORS='root=,red' \
                whiptail \
                    --title "Error" \
                    --msgbox "Problem downloading docker-compose container wrapper script :-(" 8 78
            exit_failure
        fi
    fi
}

function install_docker_compose() {

    # Install current version of docker-compose as a container
    logger "install_docker_compose" "Installing docker-compose..."
    logger "install_docker_compose" "Attempting download of latest docker-compose container wrapper script"
    whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Attempting installation of docker-compose container wrapper..." 8 78

    # TODO - Change to official installer once it supports multi-arch
    # see: https://github.com/docker/compose/issues/6831
    #URL_DOCKER_COMPOSE_INSTALLER="https://github.com/docker/compose/releases/download/$docker_compose_version_latest/run.sh"
    URL_DOCKER_COMPOSE_INSTALLER="https://raw.githubusercontent.com/linuxserver/docker-docker-compose/master/run.sh"

    if curl -L --fail "$URL_DOCKER_COMPOSE_INSTALLER" -o /usr/local/bin/docker-compose >> "$LOGFILE" 2>&1; then
        logger "install_docker_compose" "Download of latest docker-compose container wrapper script was OK"

        # Make executable
        logger "install_docker_compose" "Attempting 'chmod a+x /usr/local/bin/docker-compose'..."
        if chmod -v a+x /usr/local/bin/docker-compose >> "$LOGFILE" 2>&1; then
            logger "install_docker_compose" "'chmod a+x /usr/local/bin/docker-compose' was successful"

            # Make sure we can now run docker-compose and it is the latest version
            if docker-compose version >> "$LOGFILE" 2>&1; then
                logger "install_docker_compose" "docker-compose installed successfully!"
                whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "docker-compose installed successfully!" 8 78
            else
                logger "install_docker_compose" "ERROR: Issue running newly installed docker-compose :-("
                NEWT_COLORS='root=,red' \
                    whiptail \
                        --title "Error" \
                        --msgbox "Issue running newly installed docker-compose :-(" 8 78
                exit_failure
            fi
        else
            logger "install_docker_compose" "ERROR: Problem chmodding docker-compose container wrapper script :-("
            NEWT_COLORS='root=,red' \
                whiptail \
                    --title "Error" \
                    --msgbox "Problem chmodding docker-compose container wrapper script :-(" 8 78
            exit_failure
        fi
    else
        logger "install_docker_compose" "ERROR: Problem downloading docker-compose container wrapper script :-("
        NEWT_COLORS='root=,red' \
            whiptail \
                --title "Error" \
                --msgbox "Problem downloading docker-compose container wrapper script :-(" 8 78
        exit_failure
    fi
}

function find_rtlsdr_devices() {

    # clone rtl-sdr repo
    logger "find_rtlsdr_devices" "Attempting to clone RTL-SDR repo..."
    if git clone --depth 1 "$URL_REPO_RTLSDR" "$TMPDIR_REPO_RTLSDR" >> "$LOGFILE" 2>&1; then
        logger "find_rtlsdr_devices" "Clone of RTL-SDR repo OK"
    else
        logger "find_rtlsdr_devices" "ERROR: Problem cloneing RTL-SDR repo :-(" "$LIGHTRED"
        exit_failure
    fi

    # ensure the rtl-sdr.rules file exists
    if [[ -e "$TMPDIR_REPO_RTLSDR/rtl-sdr.rules" ]]; then

        # loop through each line of rtl-sdr.rules and look for radio
        while read -r line; do

            # only care about lines with radio info
            if echo "$line" | grep 'SUBSYSTEMS=="usb"' > /dev/null 2>&1; then

                # get idVendor & idProduct to look for
                idVendor=$(echo "$line" | grep -oP "$REGEX_PATTERN_RTLSDR_RULES_IDVENDOR")
                idProduct=$(echo "$line" | grep -oP "$REGEX_PATTERN_RTLSDR_RULES_IDPRODUCT")

                # look for the USB devices
                for lsusbline in $(lsusb -d "$idVendor:$idProduct"); do

                    # get bus & device number
                    usb_bus=$(echo "$lsusbline" | grep -oP "$REGEX_PATTERN_LSUSB_BUSNUMBER")
                    usb_device=$(echo "$lsusbline" | grep -oP "$REGEX_PATTERN_LSUSB_DEVICENUMBER")

                    # add to list of radios
                    if [[ -c "/dev/bus/usb/$usb_bus/$usb_device" ]]; then
                        echo " * Found RTL-SDR device at /dev/bus/usb/$usb_bus/$usb_device"
                        RTLSDR_DEVICES+=("/dev/bus/usb/$usb_bus/$usb_device")
                    fi

                done
            fi

        done < "$TMPDIR_REPO_RTLSDR/rtl-sdr.rules"

    else
        logger "find_rtlsdr_devices" "ERROR: Could not find rtl-sdr.rules :-(" "$LIGHTRED"
        exit_failure
    fi

}

function get_rtlsdr_preferences() {

    source "$TMPFILE_NEWPREFS"

    echo ""
    echo -e "${WHITE}===== RTL-SDR Preferences =====${NOCOLOR}"
    echo ""
    if input_yes_or_no "Do you wish to use an RTL-SDR device attached to this machine to receive ADS-B ES (1090MHz) traffic?"; then

        # Look for RTL-SDR radios
        find_rtlsdr_devices
        echo -n "Found ${#RTLSDR_DEVICES[@]} "
        if [[ "${#RTLSDR_DEVICES[@]}" -gt 1 ]]; then
            echo "radios."
        elif [[ "${#RTLSDR_DEVICES[@]}" -eq 0 ]]; then
            echo "radios."
        else
            echo "radio."
        fi

        # TODO if radios already have 00001090 and 00000978 serials, then
        #   - let user know radios already have serials set
        #   - assume 00001090 and 00000978 are for ADS-B and
        # Example wording:
        #   "Found RTL-SDR with serial number '00001090'. Will assume this device should be used for ADS-B ES (1090MHz) reception."
        #   "Found RTL-SDR with serial number '00000978'. Will assume this device should be used for ADS-B UAT (978MHz) reception."
        # press any key to continue

        logger "TODO!" "NEED TO DO RTL-SDR SERIAL STUFF!!!"

        # only_one_radio_attached=0
        # while [[ "$only_one_radio_attached" -eq 0 ]]; do

        #     # Ask the user to unplug all but one RTL-SDR
        #     echo ""
        #     echo -e "${YELLOW}Please ensure the only RTL-SDR device connected to this machine is the one to be used for ADS-B ES (1090MHz) reception!${NOCOLOR}"
        #     echo -e "${YELLOW}Disconnect all other RTL-SDR devices!${NOCOLOR}"
        #     read -p "Press any key to continue" -sn1
        #     echo ""

        #     # Look for RTL-SDR radios
        #     find_rtlsdr_devices
        #     echo -n "Found ${#RTLSDR_DEVICES[@]} "
        #     if [[ "${#RTLSDR_DEVICES[@]}" -gt 1 ]]; then
        #         echo "radios."
        #     elif [[ "${#RTLSDR_DEVICES[@]}" -eq 0 ]]; then
        #         echo "radios."
        #     else
        #         echo "radio."
        #     fi

        #     # If more than one radio is detected, then ask the user to unplug all other radios except the one they wish to use for ADSB 1090MHz reception.
        #     if [[ "${#RTLSDR_DEVICES[@]}" -gt 1 ]]; then
        #         echo ""
        #         logger "get_preferences" "More than one RTL-SDR device was found. Please un-plug all RTL-SDR devices, except the device you wish to use for ADS-B ES (1090MHz) reception." "$LIGHTRED"
        #         echo ""
        #     elif [[ "${#RTLSDR_DEVICES[@]}" -eq 1 ]]; then
        #         only_one_radio_attached=1
        #     else
        #         logger "get_preferences" "No RTL-SDR devices found. Please connect the RTL-SDR device that will be used for ADS-B ES (1090MHz) reception."
        #     fi
        # done

        # # If only one radio present, check serial. If not 00001090 then change to this
        # RTLSDR_ADSB_

    fi
}

function unload_rtlsdr_kernel_modules() {
    for modulename in "${RTLSDR_MODULES_TO_BLACKLIST[@]}"; do
        if lsmod | grep -i "$modulename" > /dev/null 2>&1; then

            msg="Module '$modulename' must be unloaded to continue. Is this OK?"
            title="Unload of kernel modules required"
            if whiptail --backtitle "$WHIPTAIL_BACKTITLEBACKTITLE" --title "$title" --yesno "$msg" 7 80; then
                if rmmod "$modulename"; then
                    logger "unload_rtlsdr_kernel_modules" "Module '$modulename' unloaded successfully!"
                else
                    logger "unload_rtlsdr_kernel_modules" "ERROR: Could not unload module '$modulename' :-("
                    NEWT_COLORS='root=,red' \
                        whiptail \
                            --title "Error" \
                            --msgbox "Could not unload module '$modulename' :-(" 8 78
                    exit_failure
                fi
            else
                exit_user_cancelled
            fi
        else
            logger "unload_rtlsdr_kernel_modules" "Module '$modulename' is not loaded!"
        fi
    done
}

function set_rtlsdr_serial_to_00001090() {
    echo ""
    echo -e "${WHITE}===== RTL-SDR Serial ===== ${NOCOLOR}"
    echo ""

    # get current serial number of radio
    docker run --rm -it --device="${RTLSDR_DEVICES[0]}":"${RTLSDR_DEVICES[0]}" --entrypoint rtl_eeprom mikenye/readsb # TODO: greppage

    # set current serial number of radio
    docker run --rm -it --device="${RTLSDR_DEVICES[0]}":"${RTLSDR_DEVICES[0]}" --entrypoint rtl_eeprom mikenye/readsb -s 00001090 # TODO: yessage

}

function create_docker_compose_yml_file() {

    logger "create_docker_compose_yml_file" "Creating docker_compose.yml file"

    if is_binary_installed python3; then
        python3 sdr-docker-config.py -i "$PROJECTDIR"
    elif is_binary_installed python; then
        python sdr-docker-config.py -i "$PROJECTDIR"
    fi
    logger "create_docker_compose_yml_file" "Adding definition to docker-compose.yml"
}

function show_post_deploy_help() {

    echo -e "\n\n"
    echo -e "${LIGHTGREEN}Congratulations on your new Docker-based ADS-B deployment!${NOCOLOR}"
    echo ""
    echo -e "${LIGHTBLUE}Deployment Info:${NOCOLOR}"
    echo -e " - The ${WHITE}project directory${NOCOLOR} is '${WHITE}$PROJECTDIR${NOCOLOR}'. You should cd into this directory before running any 'docker-compose' commands for your ADS-B containers."
    echo -e " - The ${WHITE}compose file${NOCOLOR} is '${WHITE}$PROJECTDIR/docker-compose.yml${NOCOLOR}'."
    echo -e " - The ${WHITE}environment file${NOCOLOR} is '${WHITE}$PROJECTDIR/.env${NOCOLOR}'."
    echo -e " - The ${WHITE}container data${NOCOLOR} is stored under '${WHITE}$PROJECTDIR/data/${NOCOLOR}'."
    echo ""
    echo -e "${LIGHTBLUE}Basic Help:${NOCOLOR}"
    echo -e " - To bring the environment up: ${WHITE}cd $PROJECTDIR; docker-compose up -d${NOCOLOR}"
    echo -e " - To bring the environment down: ${WHITE}cd $PROJECTDIR; docker-compose down${NOCOLOR}"
    echo -e " - To view the environment logs: ${WHITE}cd $PROJECTDIR; docker-compose logs -f${NOCOLOR}"
    echo -e " - To view the logs for an individual container: ${WHITE}docker logs -f <container>${NOCOLOR}"
    echo -e " - To view running containers: ${WHITE}docker ps${NOCOLOR}"
    echo ""
    echo -e "${LIGHTBLUE}Next steps for you (yes you reading this!):${NOCOLOR}"
    echo " - Wait for 5-10 minutes for some data to be sent..."
    if [[ "$FEED_ADSBX" == "ON" ]]; then
        echo -e " - Go to ${WHITE}https://adsbexchange.com/myip/${NOCOLOR} to check the status of your feeder."
    fi
    if [[ "$FEED_FLIGHTAWARE" == "ON" ]]; then
        echo -e " - If you haven't already, go to ${WHITE}https://flightaware.com/adsb/piaware/claim${NOCOLOR} and claim your receiver."
    fi
    if [[ "$FEED_FLIGHTRADAR24" == "ON" ]]; then
        echo -e " - If you haven't already, go to ${WHITE}https://www.flightradar24.com${NOCOLOR} and create your account."
    fi
    if [[ "$FEED_RADARBOX" == "ON" ]]; then
        echo -e " - If you haven't already, go to ${WHITE}https://www.radarbox.com/raspberry-pi/claim${NOCOLOR} and claim your receiver."
    fi
    if [[ "$FEED_PLANEFINDER" == "ON" ]]; then
        echo -e " - If you haven't already, go to ${WHITE}https://www.planefinder.net/${NOCOLOR} 'Account' > 'Manage Receivers' and press 'Add receiver' to claim your receiver."
    fi
    echo ""
    echo "If you need to reconfigure the environment, just run this script again."
    echo "Thanks!"
    echo -e "\n"
}

function add_user_to_docker() {
    CURRENT_USER=$(sudo who am i | awk '{print $1}')
    logger "Adding user $CURRENT_USER to the docker user group"
    usermod -aG docker "$CURRENT_USER"
}

##### MAIN SCRIPT #####

# Initialise log file
rm "$LOGFILE" > /dev/null 2>&1 || true
logger "main" "Script started"
#shellcheck disable=SC2128,SC1102
command_line="$(printf %q "$BASH_SOURCE")$((($#)) && printf ' %q' "$@")"
logger "main" "Full command line: $command_line"

# Make sure the script is being run as root
if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root! Try 'sudo $command_line'"
   exit 1
fi

# Display welcome message
welcome_msg

# Configure project directory
msg="Please enter a path for the ADS-B docker project.\n"
msg+="This is where the docker-compose.yml and .env file will be stored,\n"
msg+="as well as all application data."
title="Project Path"
if PROJECTDIR=$(whiptail --backtitle "$WHIPTAIL_BACKTITLE" --inputbox "$msg" --title "$title" 9 78 "/opt/adsb" 3>&1 1>&2 2>&3); then
    if [[ -d "$PROJECTDIR" ]]; then
        logger "main" "Project directory $PROJECTDIR already exists!"
    else
        logger "main" "Creating project directory $PROJECTDIR..."
        mkdir -p "$PROJECTDIR" || exit 1
    fi
else
    exit_user_cancelled
fi

# Update & export variables based on $PROJECTDIR
PREFSFILE="$PROJECTDIR/.env"
COMPOSEFILE="$PROJECTDIR/docker-compose.yml"
TMPFILE_NEWPREFS="$PROJECTDIR/.env.new_from_adsb_docker_install"
export PROJECTDIR PREFSFILE COMPOSEFILE TMPFILE_NEWPREFS

# Check if "$PREFSFILE" exists
if [[ -e "$PREFSFILE" ]]; then
    logger "main" "Environment variables file $PREFSFILE already exists."
    source "$PREFSFILE"
    if [[ "$ADSB_DOCKER_INSTALL_ENVFILE_SCHEMA" -ne "$CURRENT_SCHEMA_VERSION" ]]; then
        logger "main" "Environment variable file $PREFSFILE was not created by this script!"
        if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Environment variable file already exists!" --yesno "Existing environment variables file $PREFSFILE was not created by this script! Do you want this script to take a backup of this file and continue?" 10 78; then
            BACKUPFILE="$PREFSFILE.backup.$(date -Iseconds)"
            cp -v "$PREFSFILE" "$BACKUPFILE" >> "$LOGFILE" 2>&1 || exit 1
            logger "main" "Backup of $PREFSFILE to $BACKUPFILE completed!"
        else
            exit_user_cancelled
        fi
    fi
fi

# Check if "$COMPOSEFILE" exists
if [[ -e "$COMPOSEFILE" ]]; then
    logger "main" "Compose file $COMPOSEFILE already exists."
    source "$PREFSFILE"
    if ! grep -oP "$REGEX_PATTERN_COMPOSEFILE_SCHEMA_HEADER" "$COMPOSEFILE"; then
        logger "main" "Existing compose file $COMPOSEFILE was not created by this script!"
        echo ""
        if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Existing compose file found" --yesno "Existing compose file $COMPOSEFILE was not created by this script! Do you want this script to backup the file and continue?" 10 78; then
            BACKUPFILE="$COMPOSEFILE.backup.$(date -Iseconds)"
            cp -v "$COMPOSEFILE" "$BACKUPFILE" || exit 1
            logger "main" "Backup of $COMPOSEFILE to $BACKUPFILE completed!"
        else
            exit_user_cancelled
        fi
    fi
fi

# Ensure apt-get update has been run
update_apt_repos

# Install required packages / prerequisites (curl, docker, temp container, docker-compose)
# Get curl
if ! is_binary_installed curl; then
    msg="This script needs to install the 'curl' utility, which is used for:\n"
    msg+=" * Automatic submission of Planefinder sign-up form\n"
    msg+="Is it ok to install curl?"
    if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Package installation" --yesno "$msg" 12 80; then
        install_with_apt curl
    else
        exit_user_cancelled
    fi
fi
# Get expect
if ! is_binary_installed python && ! is_binary_installed python3; then
    msg="This script needs to install python, which is used for:\n"
    msg+=" * Generate the docker-compose configuration files\n"
    msg+="Is it ok to install python?"
    if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Package installation" --yesno "$msg" 12 80; then
        install_with_apt python3
    else
        exit_user_cancelled
    fi
fi
# Deploy docker
if ! is_binary_installed docker; then
    msg="This script needs to install docker, which is used for:\n"
    msg+=" * Running the containers!\n"
    msg+="Is it ok to install docker?"
    if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Package docker" --yesno "$msg" 12 80; then
        install_docker
    else
        exit_user_cancelled
    fi
else
    update_docker
fi
# Deploy docker compose
get_latest_docker_compose_version
if ! is_binary_installed docker-compose; then
    msg="This script needs to install docker-compose, which is used for:\n"
    msg+=" * Management and orchestration of containers!\n"
    msg+="Is it ok to install docker-compose?"
    if whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "docker-compose" --yesno "$msg" 12 80; then
        install_docker_compose
    else
        exit_user_cancelled
    fi
else
    update_docker_compose
fi

add_user_to_docker

unload_rtlsdr_kernel_modules

create_docker_compose_yml_file

# start containers
pushd "$PROJECTDIR" >> "$LOGFILE" 2>&1 || exit_user_cancelled
whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Pulling (downloading) images..." 8 78
if docker-compose pull >> "$LOGFILE" 2>&1; then
    :
else
    docker-compose down >> "$LOGFILE" 2>&1 || true
    NEWT_COLORS='root=,red' \
        whiptail \
            --title "Error" \
            --msgbox "Failed to pull (download) images :-(" 8 78
    exit_failure
fi
whiptail --backtitle "$WHIPTAIL_BACKTITLE" --title "Working..." --infobox "Starting containers..." 8 78
if docker-compose up -d --remove-orphans >> "$LOGFILE" 2>&1; then
    whiptail \
        --clear \
        --backtitle "$WHIPTAIL_BACKTITLE" \
        --msgbox "Containers have been started!" \
        --title "Containers started!" \
        8 40
else
    docker-compose down >> "$LOGFILE" 2>&1 || true
    NEWT_COLORS='root=,red' \
        whiptail \
            --title "Error" \
            --msgbox "Failed to start containers :-(" 8 78
    exit_failure
fi
popd  >> "$LOGFILE" 2>&1 || exit_user_cancelled

# If we're here, then everything should've gone ok, so we can delete the temp prefs file

# print some help
show_post_deploy_help

# FINISHED!
