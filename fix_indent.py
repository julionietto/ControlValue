def fix_app():
    with open('app.py', 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    for i in range(1922 - 1, 1976):
        if lines[i].strip():
            lines[i] = '    ' + lines[i]
            
    with open('app.py', 'w', encoding='utf-8') as f:
        f.writelines(lines)
        
if __name__ == '__main__':
    fix_app()
    print("Indentation fixed.")
