#!/bin/bash
#shellcheck disable=SC2128,SC1102

# sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/sdr-installer.sh)"
command_line="$(printf %q "$BASH_SOURCE")$((($#)) && printf ' %q' "$@")"

if [[ $EUID -ne 0 ]]; then
   echo "This script must be run as root! Try 'sudo $command_line'"
   exit 1
fi

INSTALL_SCRIPT="https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/sdr-easy-install.sh"
INSTALL_YAML="https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/sdr-docker-config.py"

TERM=ansi whiptail --title "Working" --infobox "Downloading Install Files!" 8 78

if [[ -e "sdr-easy-install.sh" ]]; then
    rm sdr-easy-install.sh 2>&1 || exit
fi

if [[ -e "sdr-easy-install.sh" ]]; then
    rm sdr-docker-config.py 2>&1 || exit
fi

curl -fsSL "$INSTALL_SCRIPT" -o sdr-easy-install.sh 2>&1  || exit
curl -fsSL "$INSTALL_YAML" -o sdr-docker-config.py 2>&1 || exit

chmod +x sdr-easy-install.sh 2>&1 || exit
sudo ./sdr-easy-install.sh 2>&1 || exit