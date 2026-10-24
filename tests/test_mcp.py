import json
import os
import sys

import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session
from openpklab.server import create_server
from openpklab.storage import Notebook

REQUIRED={'create_experiment','list_experiments','get_experiment','add_observation','add_methodology','attach_file','list_figures','list_tables','organize_experiment','analyze_dataset','generate_scientific_hints','run_scientific_plugin','generate_experiment_report','export_notebook'}


def data(result):
    assert not result.isError, result.content
    return result.structuredContent or json.loads(result.content[0].text)


async def test_protocol_full_workflow(tmp_path,png):
    mcp,lab,_=create_server(tmp_path)
    async with create_connected_server_and_client_session(mcp) as session:
        tools=(await session.list_tools()).tools
        assert REQUIRED <= {t.name for t in tools}
        assert all(t.inputSchema['type']=='object' and t.outputSchema for t in tools)
        e=data(await session.call_tool('create_experiment',{'title':'MCP workflow','category':'pharmacokinetic'}))['experiment']['id']
        obs=data(await session.call_tool('add_observation',{'experiment_id':e,'content':'Measured synthetic profile'}))['record']
        first=data(await session.call_tool('add_methodology',{'experiment_id':e,'section':'protocol','content':'Synthetic protocol'}))['record']
        data(await session.call_tool('add_methodology',{'experiment_id':e,'section':'protocol','content':'Protocol revision','revises':first['id']}))
        f=lab.upload(e,'pk.csv',b'time,concentration\n0,16\n1,8\n2,4\n3,2\n4,1\n')['file']
        image=lab.upload(e,'photo.png',png)['file']
        data(await session.call_tool('attach_file',{'experiment_id':e,'file_id':f['id'],'title':'Synthetic PK','metadata':{'units':{'time':'h','concentration':'mg/L'},'observation_ids':[obs['id']]}}))
        assert len(data(await session.call_tool('list_tables',{'experiment_id':e}))['tables'])==1
        assert len(data(await session.call_tool('list_figures',{'experiment_id':e}))['figures'])==1
        assert data(await session.call_tool('analyze_dataset',{'experiment_id':e,'file_id':f['id']}))['rows']==5
        calc=data(await session.call_tool('run_scientific_plugin',{'experiment_id':e,'file_id':f['id'],'plugin':'nca','options':{'time_unit':'h','concentration_unit':'mg/L'}}))
        assert calc['findings']['half_life']==pytest.approx(1)
        assert data(await session.call_tool('organize_experiment',{'experiment_id':e}))['targeted_questions']
        hints=data(await session.call_tool('generate_scientific_hints',{'experiment_id':e}))['hints']
        data(await session.call_tool('record_hint_feedback',{'experiment_id':e,'hint_id':hints[0]['id'],'decision':'deferred'}))
        assert '# MCP workflow' in data(await session.call_tool('generate_experiment_report',{'experiment_id':e}))['markdown']
        artifact=data(await session.call_tool('export_notebook',{'experiment_id':e}))
        assert artifact['size']>500
        data(await session.call_tool('update_experiment_status',{'experiment_id':e,'status':'completed'}))
        assert data(await session.call_tool('get_experiment',{'experiment_id':e}))['status']=='completed'
        assert len(data(await session.call_tool('list_experiments',{}))['experiments'])==1
        assert data(await session.call_tool('get_profile',{}))['id']==lab.notebook.profile()['id']
        bad=await session.call_tool('get_experiment',{'experiment_id':'missing'})
        assert bad.isError
    assert Notebook(tmp_path).get(e)['files'][0]['id']==f['id']


async def test_stdio_process_restart_persistence(tmp_path):
    params=StdioServerParameters(command=sys.executable,args=['-m','openpklab.cli','--data-dir',str(tmp_path),'serve'])
    for first in (True,False):
        async with stdio_client(params) as (read,write):
            async with ClientSession(read,write) as session:
                initialized=await session.initialize()
                assert initialized.serverInfo.name=='OpenPKLab'
                if first:
                    data(await session.call_tool('create_experiment',{'title':'Persistent stdio','category':'in_vitro','experiment_id':'stdio-persistence'}))
                else:
                    assert data(await session.call_tool('get_experiment',{'experiment_id':'stdio-persistence'}))['title']=='Persistent stdio'


SCENARIOS=[('in_vitro_metabolism','in_vitro'),('in_vitro_permeability','in_vitro'),('protein_binding','in_vitro'),('iv_pk','pharmacokinetic'),('oral_pk','pharmacokinetic'),('multiple_dose_pk','pharmacokinetic'),('pk_pd_relationship','translational_pkpd'),('missing_data','pharmacokinetic'),('conflicting_observations','pharmacodynamic'),('multimedia_revisions','in_vivo')]

@pytest.mark.parametrize('scenario,category',SCENARIOS)
async def test_ten_complete_experiments(tmp_path,png,scenario,category):
    mcp,lab,_=create_server(tmp_path)
    async with create_connected_server_and_client_session(mcp) as session:
        async def call(name,**args): return data(await session.call_tool(name,args))
        eid=(await call('create_experiment',title=scenario,category=category,objective='Synthetic end-to-end validation'))['experiment']['id']
        await call('update_experiment_status',experiment_id=eid,status='active')
        first=(await call('add_methodology',experiment_id=eid,section='protocol',content='Synthetic test data only; no real animal or patient data'))['record']
        if scenario=='multimedia_revisions':
            second=(await call('add_methodology',experiment_id=eid,section='protocol',content='Explicit second version',revises=first['id']))['record']
            await call('add_methodology',experiment_id=eid,section='protocol',content='Explicit third version',revises=second['id'])
            image=lab.upload(eid,'photograph.png',png)['file']
            await call('attach_file',experiment_id=eid,file_id=image['id'],title='Synthetic photograph',caption='Blank synthetic image')
        csv=b'time,concentration\n0,16\n1,8\n2,4\n3,2\n4,1\n'
        if scenario=='in_vitro_metabolism': csv=b'incubation_min,parent_remaining_percent\n0,100\n15,75\n30,50\n'
        if scenario=='in_vitro_permeability': csv=b'well,papp_cm_s,treatment\nA1,0.000001,control\nA2,0.000002,test\n'
        if scenario=='protein_binding': csv=b'replicate,fraction_unbound,unit\n1,0.10,fraction\n2,0.11,fraction\n'
        if scenario=='pk_pd_relationship': csv=b'time,concentration,response\n0,16,80\n1,8,67\n2,4,50\n3,2,33\n4,1,20\n'
        if scenario=='conflicting_observations': csv=b'dose,response,unit\n0,0,percent\n1,20,percent\n2,40,percent\n'
        if scenario=='multimedia_revisions': csv=b'subject,endpoint,value,unit\nsynthetic_A,weight,25,g\nsynthetic_B,weight,26,g\n'
        if scenario=='oral_pk': csv=b'time,concentration\n0,0\n1,8\n2,4\n3,2\n4,1\n'
        if scenario=='missing_data': csv=b'time,concentration\n0,16\n1,\n2,4\n'
        if scenario=='multiple_dose_pk': csv=b'time,concentration,occasion\n0,16,1\n1,8,1\n2,4,1\n3,2,1\n4,1,1\n'
        f=lab.upload(eid,'results.csv',csv)['file']
        await call('attach_file',experiment_id=eid,file_id=f['id'],title='Synthetic evidence',metadata={'units':{'time':'h','concentration':'mg/L'}})
        await call('add_observation',experiment_id=eid,content='Synthetic observation, not real experimental evidence',metadata={'endpoint':'binding','value':10,'unit':'%'})
        if scenario=='conflicting_observations':
            await call('add_observation',experiment_id=eid,content='Potentially conflicting value',metadata={'endpoint':'binding','value':20,'unit':'%'})
        analysis=await call('analyze_dataset',experiment_id=eid,file_id=f['id'])
        if scenario=='missing_data':
            assert analysis['missing_values']
            invalid=await session.call_tool('run_scientific_plugin',{'experiment_id':eid,'file_id':f['id'],'plugin':'nca','options':{'time_unit':'h','concentration_unit':'mg/L'}})
            assert invalid.isError
        elif scenario in {'iv_pk','oral_pk','multiple_dose_pk','pk_pd_relationship'}:
            result=await call('run_scientific_plugin',experiment_id=eid,file_id=f['id'],plugin='nca',options={'time_unit':'h','concentration_unit':'mg/L'})
            assert result['findings']['cmax'] in (8,16)
            await call('run_scientific_plugin',experiment_id=eid,file_id=f['id'],plugin='pk_visualization',options={'time_unit':'h','concentration_unit':'mg/L'})
        else:
            screened=await call('run_scientific_plugin',experiment_id=eid,file_id=f['id'],plugin='data_quality')
            assert screened['findings']['rows']>=2
        hints=(await call('generate_scientific_hints',experiment_id=eid))['hints']
        assert all(h['sources']['experiment_id']==eid for h in hints)
        if scenario=='conflicting_observations': assert any(h['code']=='potential_conflict' for h in hints)
        if scenario=='missing_data': assert any(h['code']=='missing_values' for h in hints)
        await call('add_observation',experiment_id=eid,content='Synthetic workflow completed; no biological conclusions',kind='conclusion')
        assert (await call('export_notebook',experiment_id=eid))['size']>500
        await call('update_experiment_status',experiment_id=eid,status='completed')
        restored=Notebook(tmp_path).get(eid)
        assert restored['status']=='completed' and restored['files'] and restored['records'] and restored['events']
