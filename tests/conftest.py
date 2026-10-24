import io
import pytest
from PIL import Image
from openpklab.storage import Notebook
from openpklab.service import Lab

@pytest.fixture
def lab(tmp_path):
    return Lab(Notebook(tmp_path / 'notebook'))

@pytest.fixture
def exp(lab):
    return lab.notebook.create('Synthetic PK experiment', 'pharmacokinetic', objective='Measure synthetic concentrations')['id']

@pytest.fixture
def png():
    out = io.BytesIO()
    Image.new('RGB', (8, 8), 'white').save(out, format='PNG')
    return out.getvalue()

@pytest.fixture
def pkfile(lab, exp):
    return lab.upload(exp, 'pk.csv', b'time,concentration\n0,16\n1,8\n2,4\n3,2\n4,1\n')['file']
