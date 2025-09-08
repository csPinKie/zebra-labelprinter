#!/bin/bash

MYPATH="/var/www/labels"

# DEBUG add --foreground
inoticoming ${MYPATH}/incoming ${MYPATH}/incoming_label.py {} ${MYPATH} \;
