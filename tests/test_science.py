import hashlib
import io
import math

import numpy as np
import pandas as pd
import pytest
from PIL import Image
from openpklab.datasets import quality
from openpklab.plugins import NCA, PKVisualization, Registry

OPTIONS = {'time_unit':'h', 'concentration_unit':'mg/L'}


def test_nca_analytical_exponential():
    # c=16 exp(-ln(2)t); linear trapezoidal AUClast=22.5, exact terminal ln(2).
    frame = pd.DataFrame({'time':[0,1,2,3,4], 'concentration':[16,8,4,2,1]})
    r = NCA().run(frame, OPTIONS)
    assert r['cmax'] == 16 and r['tmax'] == 0
    assert r['auclast'] == pytest.approx(22.5)
    assert r['lambda_z'] == pytest.approx(math.log(2))
    assert r['half_life'] == pytest.approx(1)
    assert r['units']['auclast'] == 'mg/L*h'
    assert r['terminal_points'] == [2,3,4] and r['status'] == 'estimated'

@pytest.mark.parametrize('unit', ['h','min','s'])
def test_nca_time_units_preserved(unit):
    r = NCA().run(pd.DataFrame({'time':[0,1,2,3,4], 'concentration':[16,8,4,2,1]}), {**OPTIONS,'time_unit':unit})
    assert r['units']['half_life'] == unit and r['half_life'] == pytest.approx(1)


def test_nca_linear_auc_and_tied_max():
    r = NCA().run(pd.DataFrame({'time':[1,2,4], 'concentration':[2,2,0]}), OPTIONS)
    assert r['auclast'] == 4 and r['tmax'] == 1
    assert r['half_life'] is None and r['status'] == 'partial'

@pytest.mark.parametrize('values', [[1,2,3,4,5], [5,0,0,0,0], [5,4,3,2,1.9]])
def test_terminal_uncertainty(values):
    r = NCA().run(pd.DataFrame({'time':[0,1,2,3,4],'concentration':values}), OPTIONS)
    assert r['half_life'] is None and r['uncertainty']

@pytest.mark.parametrize('times,conc', [([0,1],[1,None]), ([0,1],[1,float('inf')]), ([0,1],[1,-1]), ([0,0],[1,2]), ([1,0],[1,2]), ([-1,0],[1,2]), ([0],[1]), ([0,1],['x',1])])
def test_nca_rejects_ambiguous_data(times,conc):
    with pytest.raises(ValueError): NCA().run(pd.DataFrame({'time':times,'concentration':conc}), OPTIONS)

@pytest.mark.parametrize('options', [{}, {'time_unit':'days','concentration_unit':'mg/L'}, {'time_unit':'h','concentration_unit':'unknown'}])
def test_nca_explicit_units(options):
    with pytest.raises(ValueError): NCA().run(pd.DataFrame({'time':[0,1],'concentration':[1,2]}), options)


def test_nca_rejects_mixed_profiles_and_unit_conflicts():
    for extra in [{'subject':['a','b']}, {'concentration_unit':['mg/L','ng/mL']}, {'time_unit':['min','min']}]:
        with pytest.raises(ValueError): NCA().run(pd.DataFrame({'time':[0,1],'concentration':[2,1],**extra}), OPTIONS)


def test_quality_preserves_data():
    df = pd.DataFrame({'value':[1,1,1,1,100,None], 'unit':['mg','mg','mg','mg','ng','mg']})
    original = df.copy(deep=True)
    result = quality(df)
    assert {f['code'] for f in result['findings']} >= {'missing_values','duplicate_rows','inconsistent_units','outlier_screen'}
    assert result['completeness'] == pytest.approx(11/12)
    pd.testing.assert_frame_equal(df, original)


def test_quality_invalid_numeric():
    df = pd.DataFrame({'value':[1,2,'oops',float('inf')]})
    assert any(f['code']=='invalid_numeric_entries' and f['count']==2 for f in quality(df)['findings'])

@pytest.mark.parametrize('scale', ['linear','log'])
def test_multigroup_individual_plot(scale):
    frame = pd.DataFrame({'time':[0,1,0,1], 'concentration':[8,4,6,3], 'group':['A','A','B','B'], 'subject':['1','1','2','2']})
    r = PKVisualization().run(frame, {**OPTIONS,'group_column':'group','individual_column':'subject','scale':scale})
    with Image.open(io.BytesIO(r['image_bytes'])) as image:
        assert image.format=='PNG' and image.width>500
    assert r['profiles']==2 and r['scale']==scale


def test_plot_rejects_log_zero():
    with pytest.raises(ValueError, match='positive'): PKVisualization().run(pd.DataFrame({'time':[0,1],'concentration':[0,1]}), {**OPTIONS,'scale':'log'})


def test_plugin_reproducibility(lab, exp, pkfile):
    _, path = lab.notebook.file(exp, pkfile['id'])
    original = path.read_bytes()
    r = lab.run_plugin(exp, pkfile['id'], 'nca', OPTIONS)
    assert r['source_sha256'] == hashlib.sha256(original).hexdigest()
    assert r['runtime']['numpy'] and r['plugin_version'] == '1.0'
    rec = lab.notebook.get(exp)['records'][-1]
    assert rec['id'] == r['calculation_record_id'] and rec['provenance']=='computational'
    fig = lab.run_plugin(exp, pkfile['id'], 'pk_visualization', OPTIONS)['findings']['figure']
    assert fig['role']=='derived' and fig['metadata']['source_file_id']==pkfile['id']
    assert path.read_bytes() == original


def test_plugin_registration_and_isolation():
    class Example:
        name='custom'; version='1'
        def run(self,frame,options):
            frame.iloc[0,0] = 999
            return {'answer':42}
    registry=Registry(load_external=False); registry.register(Example())
    frame=pd.DataFrame({'a':[1]})
    assert registry.run('custom',frame,{})['findings']['answer']==42 and frame.iloc[0,0]==1
    with pytest.raises(ValueError): registry.register(Example())
    with pytest.raises(ValueError): registry.register(object())
    with pytest.raises(ValueError): registry.run('missing',frame,{})


def test_hints_events_dedup_feedback(lab, exp):
    lab.upload(exp, 'missing.csv', b'time,concentration\n0,4\n1,\n')
    first=lab.hints(exp)['hints']; second=lab.hints(exp)['hints']
    assert [h['id'] for h in first]==[h['id'] for h in second]
    hint=next(h for h in first if h['code']=='missing_values')
    assert all(k in hint for k in ['observed_evidence','computational_finding','scientific_interpretation','hypothesis','recommended_action','uncertainty','sources'])
    lab.notebook.feedback(exp,hint['id'],'accepted','I will check the instrument')
    assert next(h for h in lab.hints(exp)['hints'] if h['id']==hint['id'])['status']=='accepted'
    assert any(e['action']=='hint_feedback' for e in lab.notebook.get(exp)['events'])


def test_conflict_requires_explicit_evidence(lab, exp):
    lab.add_record(exp,'Value 1',metadata={'endpoint':'binding','value':1,'unit':'%'})
    lab.add_record(exp,'Value 2',metadata={'endpoint':'binding','value':2,'unit':'%'})
    h=next(h for h in lab.hints(exp)['hints'] if h['code']=='potential_conflict')
    assert len(h['sources']['record_ids'])==2 and 'replicate' in h['uncertainty']


def test_constant_concentration_uncertainty():
    r=NCA().run(pd.DataFrame({'time':[0,1,2,3,4],'concentration':[5,5,5,5,5]}),OPTIONS)
    assert r['half_life'] is None and r['lambda_z'] is None


def test_negative_pk_values_are_flagged():
    assert any(f['code']=='negative_pk_values' for f in quality(pd.DataFrame({'time':[0,1],'concentration':[1,-1]}))['findings'])
