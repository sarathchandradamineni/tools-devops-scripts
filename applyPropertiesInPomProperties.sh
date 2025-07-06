#!/bin/bash

declare -a repos
declare -a branches

repos=( "hp-hyd-config" "hp-ref-config" )
branches=( "release-9" "release-12" "release-14" )

# Clone hyd config repo
git clone https://sourcecode.socialcoding.bosch.com/scm/rhp/hp-hyd-config.git ./external/hp-hyd-config

# Clone ref config repo
git clone https://sourcecode.socialcoding.bosch.com/scm/rhp/hp-ref-config.git ./external/hp-ref-config

for repo in "{$repos[@]}"; do
    cd ./external/"$repo"
    for branch in "${branches[@]}"; do
        git checkout "$branch"
        git pull

        git branch feature/HPSOFT-12372-metadata-for-ncsu
        git checkout feature/HPSOFT-12372-metadata-for-ncsu
        
        ../../updatePomFamilyProperties.exe display.reboot.time=1000 display.transfer.time=2000 parameter.mode=retain

        git add .
        git commit -m "HPSOFT-12372: Update pom-family.properties with metadata for NCSU"
        git push --set-upstream origin feature/HPSOFT-12372-metadata-for-ncsu
    done
done

