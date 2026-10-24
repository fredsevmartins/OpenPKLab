import hashlib
import io
import json
import zipfile
from concurrent.futures import ThreadPoolExecutor

import pytest
from openpyxl import Workbook
from openpklab.datasets import read_table
from openpklab.reports import export, export_file, report
from openpklab.storage import CATEGORIES, SECTIONS, Notebook

@pytest.mark.parametrize('category', sorted(CATEGORIES))
def test_create_categories_persist(lab, category):
    e = lab.notebook.create('Experiment', category, hypothesis='Unconfirmed', conditions={'temperature': '37 C'})
    restored = Notebook(lab.notebook.root).get(e['id'])
    assert restored['hypothesis'] == 'Unconfirmed'
    assert restored['events'][0]['action'] == 'experiment_created'
    assert restored['conditions'] == {'temperature': '37 C'}

@pytest.mark.parametrize('bad', ['../escape', '', 'a/b', 'a\\b', 'a'*81, "x'; DROP TABLE experiments;"])
def test_invalid_ids(lab, bad):
    with pytest.raises(ValueError): lab.notebook.create('Title', 'in_vitro', experiment_id=bad)


def test_duplicate_and_invalid_category(lab, exp):
    with pytest.raises(ValueError): lab.notebook.create('Other', 'in_vitro', experiment_id=exp)
    with pytest.raises(ValueError): lab.notebook.create('Title', 'invented')
    with pytest.raises(ValueError): lab.notebook.create('', 'in_vitro')


def test_records_revisions_search_progress(lab, exp):
    a = lab.add_record(exp, 'Initial result', metadata={'endpoint':'clearance'})['record']
    b = lab.add_record(exp, 'Corrected result', revises=a['id'])['record']
    assert b['revision'] == 2 and b['revises'] == a['id']
    assert lab.notebook.list('Corrected')[0]['id'] == exp
    assert lab.notebook.list("' OR 1=1 --") == []
    lab.notebook.update(exp, 'active')
    e = Notebook(lab.notebook.root).get(exp)
    assert len(e['records']) == 2 and e['status'] == 'active' and e['revision'] == 2
    assert e['records'][0]['content'] == 'Initial result'
    assert all('timestamp' in event for event in e['events'])

@pytest.mark.parametrize('section', SECTIONS)
def test_methodology_sections(lab, exp, section):
    a = lab.add_record(exp, 'First method', 'methodology', {'section':section})['record']
    lab.add_record(exp, 'Revised method', 'methodology', {'section':section}, revises=a['id'])
    o = lab.organize(exp)
    assert len(o['methodology'][section]) == 1
    assert o['methodology'][section][0]['content'] == 'Revised method'
    assert section not in o['missing_methodology']


def test_ai_method_is_not_measured_evidence(lab, exp):
    lab.add_record(exp, 'Proposed protocol only', 'methodology', {'section':'protocol'}, provenance='ai_suggestion')
    assert 'protocol' in lab.organize(exp)['missing_methodology']


def test_isolated_revisions_and_files(lab, exp, png):
    other = lab.notebook.create('Other', 'in_vitro')['id']
    rec = lab.add_record(exp, 'Observation')['record']
    f = lab.upload(exp, 'photo.png', png)['file']
    with pytest.raises(ValueError): lab.notebook.add_record(other, 'Try revision', revises=rec['id'])
    with pytest.raises(ValueError): lab.notebook.file(other, f['id'])
    with pytest.raises(ValueError): lab.notebook.annotate_file(other, f['id'], title='Stolen')
    with pytest.raises(ValueError): lab.notebook.add_record(exp, 'Wrong', 'methodology', {'section':'protocol'}, revises=rec['id'])
    with pytest.raises(ValueError): lab.notebook.add_record(exp, 'Wrong', 'methodology', {'section':'invented'})


def test_originals_figures_tables_metadata(lab, exp, png, pkfile):
    a = lab.upload(exp, 'photo.png', png)['file']
    b = lab.upload(exp, 'microscope.png', png)['file']
    assert (a['number'], b['number']) == (1, 2)
    assert a['sha256'] == b['sha256'] == hashlib.sha256(png).hexdigest()
    lab.notebook.annotate_file(exp, a['id'], title='Microscopy', caption='Researcher supplied', metadata={'conditions': {'temperature':'37 C'}})
    assert len(lab.organize(exp)['figures']) == 2
    assert lab.organize(exp)['tables'][0]['id'] == pkfile['id']
    item, path = lab.notebook.file(exp, a['id'])
    assert path.read_bytes() == png and item['revision'] == 2
    events = lab.notebook.get(exp)['events']
    assert any(e['action'] == 'file_metadata_revised' for e in events)


def test_integrity_detection(lab, exp, pkfile):
    _, path = lab.notebook.file(exp, pkfile['id'])
    path.chmod(0o600)
    path.write_bytes(b'changed')
    with pytest.raises(ValueError, match='integrity'): lab.notebook.file(exp, pkfile['id'])


def test_xlsx_values(lab, exp):
    b = Workbook(); s = b.active; s.append(['time','concentration']); s.append([0,4]); s.append([1,2])
    out = io.BytesIO(); b.save(out)
    f = lab.upload(exp, 'values.xlsx', out.getvalue())['file']
    assert lab.analyze(exp, f['id'])['rows'] == 2


def test_report_and_export(lab, exp, pkfile, png):
    lab.upload(exp, 'photo.png', png)
    lab.add_record(exp, 'Observed a decrease', 'conclusion')
    lab.add_record(exp, 'Possibly metabolism', 'hypothesis', provenance='ai_suggestion')
    lab.add_record(exp, 'Unverified fake citation', 'reference')
    md = report(lab, exp)
    for section in ['Objective','Experimental design','Materials and methods','Results','Tables','Figures','Discussion','Limitations','Conclusions','References']:
        assert f'## {section}' in md
    assert 'No verified references supplied' in md and 'Unverified fake citation' not in md
    assert 'ai_suggestion' in md
    artifact = export(lab, exp)
    path = export_file(lab.notebook, exp, artifact['id'])
    assert hashlib.sha256(path.read_bytes()).hexdigest() == artifact['sha256']
    with zipfile.ZipFile(path) as z:
        original, src = lab.notebook.file(exp, pkfile['id'])
        assert z.read(f"files/{original['id']}/{original['filename']}") == src.read_bytes()
        assert json.loads(z.read('notebook.json'))['id'] == exp
        assert 'report.md' in z.namelist()
    other = lab.notebook.create('Other', 'in_vivo')['id']
    with pytest.raises(ValueError): export_file(lab.notebook, other, artifact['id'])


def test_concurrent_records(lab, exp):
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda i: lab.notebook.add_record(exp, f'Observation {i}'), range(12)))
    assert len(lab.notebook.get(exp)['records']) == 12


def test_profile_stable(lab):
    assert Notebook(lab.notebook.root).profile() == lab.notebook.profile()
