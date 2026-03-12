# Backend package for Flask API

with open('backend/app.py', 'r', encoding='utf-8') as f:
    content = f.read()
content = content.rstrip()
with open('backend/app.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('Done')
