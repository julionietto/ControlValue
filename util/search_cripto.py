with open('app.py', 'r', encoding='utf-8') as f:
    lines = [f"{i}: {line.strip()}" for i, line in enumerate(f, 1) if 'Cripto' in line]

with open('cripto_lines.txt', 'w', encoding='utf-8') as fh:
    fh.write('\\n'.join(lines))
