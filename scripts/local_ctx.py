import re
import os
from pathlib import Path

# Navigate to project root (parent of scripts folder)
script_dir = Path(__file__).parent
project_root = script_dir.parent
os.chdir(project_root)

def generate_local_ctx(llms_file='llms.txt', output_file='llms-ctx.txt'):
    llms_path = Path(llms_file)
    if not llms_path.exists():
        print(f"Error: {llms_file} not found.")
        return

    content = llms_path.read_text()
    # Find all links in the format [title](url)
    links = re.findall(r'\[.*?\]\((.*?)\)', content)
    
    ctx_output = []
    
    for link in links:
        # Convert _proc/ paths to _docs/ paths
        # _proc/00_db_host.html.md -> _docs/db_host.html.md
        local_path = Path(link)
        
        # Check if path starts with _proc (works on both Windows and Unix)
        if local_path.parts and local_path.parts[0] == '_proc':
            # Extract filename, strip number prefix
            filename = local_path.name
            # Remove leading digits and underscore (e.g., "00_", "01_", "15_")
            if len(filename) > 3 and filename[:2].isdigit() and filename[2] == '_':
                filename = filename[3:]
            elif len(filename) > 2 and filename[:1].isdigit() and filename[1] == '_':
                filename = filename[2:]
            local_path = Path('_docs') / filename
        
        if local_path.exists():
            print(f"Processing: {local_path}")
            file_text = local_path.read_text(encoding='utf-8')
            ctx_output.append(f"FILE: {link}\n")
            ctx_output.append(file_text)
            ctx_output.append("\n" + "="*40 + "\n")
        else:
            print(f"Skipping: {local_path} (File not found)")

    Path(output_file).write_text("\n".join(ctx_output), encoding='utf-8')
    print(f"\nDone! Created {output_file}")

if __name__ == "__main__":
    generate_local_ctx()