import re
from pathlib import Path

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
        # Convert web-style path to local path
        local_path = Path(link)
        
        if local_path.exists():
            print(f"Processing: {local_path}")
            file_text = local_path.read_text(encoding='utf-8')
            # Format follows the llms-ctx standard: 
            # File path as header, then content, then separator
            ctx_output.append(f"FILE: {link}\n")
            ctx_output.append(file_text)
            ctx_output.append("\n" + "="*40 + "\n")
        else:
            print(f"Skipping: {local_path} (File not found)")

    Path(output_file).write_text("\n".join(ctx_output), encoding='utf-8')
    print(f"\nDone! Created {output_file}")

if __name__ == "__main__":
    generate_local_ctx()