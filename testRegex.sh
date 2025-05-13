#!/bin/bash

testString=$1
regexPattern=$2

if [[ $testString =~ $regexPattern ]]; then
    echo "Match found :)"
else
    echo "No match found :("
fi
