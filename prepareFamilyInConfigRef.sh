#!/bin/bash

# create families folder
mkdir families

# Copy all the families to the families folder
ls | grep "uni.ref" | xargs -I {} mkdir families/{}

# Copy pom.properties files as pom-temp.properties in order to have a backup for variant specific information
ls | grep "uni.ref" | xargs -I {} cp {}/pom.properties {}/pom-temp.properties

# Move all the setup files to the families folder
ls | grep "uni.ref" | xargs -I {} bash -c 'git mv "{}/setup/"* "families/{}"'

# Copy all the pom.properties files to the families folder
ls | grep "uni.ref" | xargs -I {} git mv {}/pom.properties families/{}/pom-family.properties

# Remove variant specific information from pom-family.properties
ls ./families | grep "uni.ref" | xargs -I {} sed -i '/^artifact.meta.ttnr/d' ./families/{}/pom-family.properties
ls ./families | grep "uni.ref" | xargs -I {} sed -i -e ':a' -e 'N' -e '$!ba' -e 's/\n\n\+/\n\n/g' ./families/{}/pom-family.properties

# Remove family specific information from pom-variant.properties
ls ./families | grep "uni.ref" | xargs -I {} sed -i '/^$\|^artifact.meta.ttnr/!d' ./{}/pom-temp.properties

# copy the content from pom-temp.properties to pom-variant.properties
function alignPomVarianProperties()
{
    for folder in $(ls | grep "uni.ref"); do
        local pomTemp=./$folder/pom-temp.properties
        touch ./$folder/pom-variant.properties
        > ./"$folder"/pom-variant.properties
        local flagInclude
        flagInclude=false
        local prevAppMatch=""
        local currAppMatch=""
        while IFS= read -r line; do
            local ttnrMatch=$( echo "$line" | awk '/artifact.meta.ttnr.[0-9]+/' | tr -d '\r\n' )
            if [[ -n "$ttnrMatch" ]]; then
                echo "Log $folder :: $ttnrMatch "
                currAppMatch=$( echo "$ttnrMatch" | cut -d'.' -f4 )
                # File match for artifact.meta.ttnr.[0-9]+
                if [[ -z "$prevAppMatch" ]]; then 
                    echo "$ttnrMatch" >> ./$folder/pom-variant.properties
                elif [[ "$prevAppMatch" == "$currAppMatch" ]]; then
                    echo "$ttnrMatch" >> ./$folder/pom-variant.properties
                elif [[ "$prevAppMatch" != "$currAppMatch" ]]; then
                    echo "" >> ./$folder/pom-variant.properties
                    echo "$ttnrMatch" >> ./$folder/pom-variant.properties
                fi
                prevAppMatch="$currAppMatch"
            fi
            prevLine=$line
        done < "$pomTemp"
        echo "" >> ./$folder/pom-variant.properties
    done
}
alignPomVarianProperties

# Remove pom-temp.properties
ls | grep "uni.ref" | xargs -I {} rm ./{}/pom-temp.properties
