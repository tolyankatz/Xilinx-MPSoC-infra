#!/bin/sh
# Get crumb
CRUMB=$(curl -u admin:admin -s 'http://localhost:8080/crumbIssuer/api/json' | grep -oP '(?<="crumb":")[^"]*')
echo "Crumb: $CRUMB"

# Trigger build
curl -X POST -u admin:admin -H "Jenkins-Crumb:$CRUMB" http://localhost:8080/job/bsp-build-pipeline/build
echo ""
echo "Build triggered!"
