"""Execute artifact-presentation notebook cells and persist real display outputs."""
import base64
import contextlib
import io
import json
import os
from pathlib import Path
from IPython.display import Image, Markdown
import pandas as pd
ROOT=Path(__file__).resolve().parents[1]
os.chdir(ROOT)
path=ROOT/'notebooks/02_ml_training.ipynb'
notebook=json.loads(path.read_text(encoding='utf-8'))
namespace={}
for index,cell in enumerate(notebook['cells']):
    if cell['cell_type']!='code': continue
    outputs=[]
    def capture(*values):
        for value in values:
            if isinstance(value,Image):
                data={'image/png':base64.b64encode(value.data).decode()}
            elif isinstance(value,Markdown): data={'text/markdown':value.data}
            elif isinstance(value,pd.DataFrame): data={'text/html':value.to_html(),'text/plain':value.to_string()}
            else: data={'text/plain':str(value)}
            outputs.append(dict(output_type='display_data',metadata={},data=data))
    source=''.join(cell['source'])
    # Replace the imported display function to capture actual outputs.
    source=source.replace('from IPython.display import display, Image, Markdown','from IPython.display import Image, Markdown')
    namespace['display']=capture
    stream=io.StringIO()
    with contextlib.redirect_stdout(stream): exec(compile(source,f'notebook-cell-{index}','exec'),namespace)
    if stream.getvalue(): outputs.append(dict(output_type='stream',name='stdout',text=stream.getvalue()))
    cell['execution_count']=sum(c['cell_type']=='code' for c in notebook['cells'][:index+1])
    cell['outputs']=outputs
path.write_text(json.dumps(notebook,indent=2),encoding='utf-8')
print('Notebook code cells executed successfully; artifact displays persisted')
