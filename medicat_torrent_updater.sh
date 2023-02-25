#!/usr/bin/env bash

SCRIPTDIR="$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")"
cd "${SCRIPTDIR}"

(echo -n "---- Running at: "
date --iso-8601=seconds

if ! [[ -d "${SCRIPTDIR}/venv" ]]
then
  python3 -m venv venv
fi

source venv/bin/activate
pip install -U -r ./requirements.txt

python3 "${SCRIPTDIR}/main.py"

echo "---- End of run.") &>> "${SCRIPTDIR}/log.log"
