#!/bin/bash

declare -a repos
declare -a branches

repos=( "hp-hyd-config" "hp-ref-config" )
branches=( "release-9" "release-12" "release-14" )

# Clone hyd config repo
git clone https://sourcecode.socialcoding.bosch.com/scm/rhp/hp-hyd-config.git ./external/hp-hyd-config

# Clone ref config repo
git clone https://sourcecode.socialcoding.bosch.com/scm/rhp/hp-ref-config.git ./external/hp-ref-config

for repo in "${repos[@]}"; do
    cd ./external/"$repo"
    for branch in "${branches[@]}"; do
        git pull

        git push origin --delete feature/HPSOFT-12372-metadata-for-ncsu-automatic-"$branch"
    done
    cd ../..
done

