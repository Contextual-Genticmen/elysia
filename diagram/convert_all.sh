#!/bin/bash
# Extract and convert mermaid diagrams from markdown files

extract_and_convert() {
    local md_file="$1"
    local base_name=$(basename "$md_file" .md)
    local counter=1
    local in_mermaid=false
    local mermaid_content=""
    local diagram_name=""
    
    while IFS= read -r line; do
        if [[ "$line" == '```mermaid' ]]; then
            in_mermaid=true
            mermaid_content=""
            diagram_name="${base_name}_diagram_${counter}"
            continue
        fi
        
        if [[ "$in_mermaid" == true ]]; then
            if [[ "$line" == '```' ]]; then
                # Save mermaid content to file
                echo "$mermaid_content" > "${diagram_name}.mmd"
                echo "Creating ${diagram_name}.png..."
                mmdc -i "${diagram_name}.mmd" -o "${diagram_name}.png" -b transparent 2>/dev/null
                counter=$((counter + 1))
                in_mermaid=false
            else
                mermaid_content="${mermaid_content}${line}"$'\n'
            fi
        fi
    done < "$md_file"
}

# Process implementation_details.md
echo "Processing implementation_details.md..."
extract_and_convert "../MCP/implementation_details.md"

# Process interaction_model.md
echo "Processing interaction_model.md..."
extract_and_convert "../MCP/interaction_model.md"

echo "Done! Generated PNG files in $(pwd)"
ls -lh *.png
