content = open('whisper.html', 'r', encoding='utf-8').read()
old = "const API = 'http://127.0.0.1:8000';"
new = "const API = window.location.origin;"
if old in content:
    open('whisper.html', 'w', encoding='utf-8').write(content.replace(old, new))
    print('FIXED successfully')
else:
    print('NOT FOUND - searching...')
    idx = content.find('const API')
    print(content[idx:idx+80])