#!/bin/bash

# create families folder
mkdir families

# Copy all the families to the families folder
ls | grep "[a-z]*.hyd" | xargs -I {} mkdir families/{}

# Copy pom.properties files as pom-temp.properties in order to have a backup for variant specific information
ls | grep "[a-z]*.hyd" | xargs -I {} cp {}/pom.properties {}/pom-temp.properties

# Move all the setup files to the families folder
ls | grep "[a-z]*.hyd" | xargs -I {} bash -c 'git mv "{}/setup/"* "families/{}"'

# Copy all the pom.properties files to the families folder
ls | grep "[a-z]*.hyd" | xargs -I {} git mv {}/pom.properties families/{}/pom-family.properties

# Remove variant specific information from pom-family.properties
ls ./families | grep "[a-z]*.hyd" | xargs -I {} sed -i '/^artifact.meta.ttnr/d' ./families/{}/pom-family.properties
ls ./families | grep "[a-z]*.hyd" | xargs -I {} sed -i -e ':a' -e 'N' -e '$!ba' -e 's/\n\n\+/\n\n/g' ./families/{}/pom-family.properties

# Remove family specific information from pom-variant.properties
ls ./families | grep "[a-z]*.hyd" | xargs -I {} sed -i '/^$\|^artifact.meta.ttnr/!d' ./{}/pom-temp.properties

# copy the content from pom-temp.properties to pom-variant.properties
function alignPomVarianProperties()
{
    for folder in $(ls | grep "[a-z]*.hyd"); do
        local pomTemp=./$folder/pom-temp.properties
        touch ./$folder/pom-variant.properties
        local flagInclude
        flagInclude=false
        local prevAppMatch
        local currAppMatch
        while IFS= read -r line; do
            local ttnrMatch=$( echo "$line" | awk '/artifact.meta.ttnr.[0-9]+/' )
            if [[ -n "$ttnrMatch" ]]; then
                currAppMatch=$( echo "$ttnrMatch" | cut -d'.' -f4 )
                # File match for artifact.meta.ttnr.[0-9]+
                if [[ -z "$prevAppMatch" ]]; then 
                    echo "$line" >> ./$folder/pom-variant.properties
                elif [[ "$prevAppMatch" == "$currAppMatch" ]]; then
                    echo "$line" >> ./$folder/pom-variant.properties
                elif [[ "$prevAppMatch" != "$currAppMatch" ]]; then
                    echo "" >> ./$folder/pom-variant.properties
                    echo "$line" >> ./$folder/pom-variant.properties
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
ls | grep "[a-z]*.hyd" | xargs -I {} rm ./{}/pom-temp.properties
