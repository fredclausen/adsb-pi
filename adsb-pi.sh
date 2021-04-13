#!/bin/bash
#shellcheck disable=SC2128,SC1102

# sudo /bin/bash -c "$(curl -fsSL http://adsb-pi.com/install-script)"

INSTALL_SCRIPT="http://adsb-pi.com/system-install-script"
INSTALL_YAML="http://adsb-pi.com/yaml-generator"
PLUGIN="http://adsb-pi.com/plugin"

TERM=ansi whiptail --title "Working" --infobox "Downloading Install Files!" 8 78

if [[ -e "adsb-pi-installer.sh" ]]; then
    rm adsb-pi-installer.sh 2>&1 || exit
fi

if [[ -e "sdr-docker-config.sh" ]]; then
    rm sdr-docker-config.py 2>&1 || exit
fi

if [[ -e "plugin.json" ]]; then
    rm plugin.json 2>&1 || exit
fi

curl -fsSL "$INSTALL_SCRIPT" -o adsb-pi.sh 2>&1  || exit
curl -fsSL "$INSTALL_YAML" -o sdr-docker-config.py 2>&1 || exit
curl -fsSL "$PLUGIN" -o plugin.json 2>&1 || exit

chmod +x adsb-pi-installer.sh 2>&1 || exit
sudo ./adsb-pi-installer.sh 2>&1 || exit