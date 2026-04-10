import os

with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_app = []
dialogs = []
visao_geral = []
imports = []

for i, line in enumerate(lines):
    if i < 14:
        imports.append(line)

    if 17 <= i <= 504: # Lines 18 to 505 are dialogs
        dialogs.append(line)
    elif i >= 617: # Line 618 onwards is Visão Geral
        if 'if current_view == "Visão Geral":' in line:
            visao_geral.append('    # Renderiza Visão Geral\n')
        elif i >= 627: # from 628 (if assets_df.empty) downwards
            visao_geral.append('    ' + line)
        else:
            visao_geral.append(line)
    else:
        new_app.append(line)
        
with open('views/geral.py', 'w', encoding='utf-8') as f:
    f.writelines(imports)
    f.write('\n\n')
    f.writelines('import datetime\n')
    f.writelines(dialogs)
    f.write('\ndef render_visao_geral_view():\n')
    f.writelines(visao_geral)
    
# Now fix app.py missing the call
for i, line in enumerate(new_app):
    if 'from views.proventos import render_proventos_view' in line:
        new_app.insert(i+1, 'from views.geral import render_visao_geral_view\n')
        break

new_app.append('\nif current_view == "Visão Geral":\n    render_visao_geral_view()\n')

with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_app)

print('SUCCESS')
