import os

filepath = r'c:\Projeto\ControlValue\database.py'
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

target = """    rows = cursor.fetchall()
        
    allocations = {"""

replacement = """    rows = cursor.fetchall()
        
    if not rows:
        return {
            'Ações': 20.0,
            'Fiis': 20.0,
            'Ativos Internacionais': 20.0,
            'Criptos': 20.0,
            'Renda Fixa': 20.0
        }

    allocations = {"""

if target in content:
    new_content = content.replace(target, replacement)
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Success")
else:
    # Try without the blank line spaces
    target_alt = """    rows = cursor.fetchall()
    
    allocations = {"""
    if target_alt in content:
        new_content = content.replace(target_alt, replacement)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Success (alt)")
    else:
        print("Target not found")
        # Let's print a slice of content to see what's wrong
        idx = content.find("def get_user_allocations")
        if idx != -1:
            print("Context found:")
            print(repr(content[idx:idx+200]))
