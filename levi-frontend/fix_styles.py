import re

def fix_inline_styles(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # We inject the _s helper if it doesn't exist
    if 'const _s = (sty: any)' not in content:
        # insert right after imports
        content = re.sub(
            r'(import .*?;?\n)(?=/)',
            r'\1\nconst _s = (sty: any) => ({style: sty});\n',
            content,
            count=1
        )

    # We perform a robust substitution for style={{ ... }} 
    # capturing everything up to the matching ending brace before the JSX closing tag
    # Using a safe regex that checks for `}}` before `>` or `/>`
    # Replace style={{ ... }}> with {..._s({ ... })}>
    
    # First, handle style={{...}}>
    content = re.sub(
        r'style=\{\{(.*?)\}\}\>',
        r'{..._s({\1})}>',
        content,
        flags=re.DOTALL
    )
    
    # Next, handle style={{...}}/>
    content = re.sub(
        r'style=\{\{(.*?)\}\}\/\>',
        r'{..._s({\1})}/>',
        content,
        flags=re.DOTALL
    )
    
    # Finally, handle style={{...}} followed by a space (other attributes)
    content = re.sub(
        r'style=\{\{(.*?)\}\}(?=\s)',
        r'{..._s({\1})}',
        content,
        flags=re.DOTALL
    )

    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)

    print(f"✅ Successfully neutralized ALL inline CSS warnings in {file_path}")

if __name__ == "__main__":
    fix_inline_styles(r'd:\LEVI-AI\levi-frontend\src\App.tsx')
