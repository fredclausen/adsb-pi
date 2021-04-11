#!/bin/bash
#shellcheck disable=SC2128,SC1102

# sudo /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/adsb-pi.sh)"

INSTALL_SCRIPT="https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/adsb-pi.sh"
INSTALL_YAML="https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/sdr-docker-config.py"
PLUGIN="https://raw.githubusercontent.com/fredclausen/sdr-docker-config/install-script/plugins/plugin.json"

TERM=ansi whiptail --title "Working" --infobox "Downloading Install Files!" 8 78

if [[ -e "sdr-easy-install.sh" ]]; then
    rm sdr-easy-install.sh 2>&1 || exit
fi

if [[ -e "sdr-easy-install.sh" ]]; then
    rm sdr-docker-config.py 2>&1 || exit
fi

if [[ -e "plugin.json" ]]; then
    rm plugin.json 2>&1 || exit
fi

curl -fsSL "$INSTALL_SCRIPT" -o adsb-pi.sh 2>&1  || exit
curl -fsSL "$INSTALL_YAML" -o sdr-docker-config.py 2>&1 || exit
curl -fsSL "$PLUGIN" -o plugin.json 2>&1 || exit

chmod +x adsb-pi.sh 2>&1 || exit
sudo ./adsb-pi.sh 2>&1 || exit