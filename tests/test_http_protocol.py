"""Use the official SDK client against a real TCP HTTP server, not a mocked PID check."""
import os
import secrets
import socket
import subprocess
import sys
import time

import httpx
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from openpklab.storage import Notebook


async def test_real_authenticated_streamable_http(tmp_path):
    token=secrets.token_urlsafe(36)
    with socket.socket() as reserved:
        reserved.bind(('127.0.0.1',0)); port=reserved.getsockname()[1]
    process_env={**os.environ,'OPENPKLAB_TOKEN':token}
    process_env.pop('OPENPKLAB_OAUTH_ISSUER',None)
    process_env.pop('OPENPKLAB_PUBLIC_URL',None)
    log=(tmp_path/'server.log').open('w')
    proc=subprocess.Popen([sys.executable,'-m','openpklab.cli','--data-dir',str(tmp_path/'data'),'serve','--transport','http','--port',str(port)],env=process_env,stdout=log,stderr=log)
    try:
        url=f'http://127.0.0.1:{port}'
        for _ in range(100):
            try:
                if httpx.get(url+'/healthz',timeout=0.5).status_code==200: break
            except httpx.HTTPError: pass
            if proc.poll() is not None: raise AssertionError('Server exited: '+(tmp_path/'server.log').read_text())
            time.sleep(0.05)
        else: raise AssertionError('HTTP server did not become ready')
        assert httpx.post(url+'/mcp').status_code==401
        async with httpx.AsyncClient(headers={'Authorization':f'Bearer {token}'}) as client:
            async with streamable_http_client(url+'/mcp',http_client=client) as (read,write,_):
                async with ClientSession(read,write) as session:
                    init=await session.initialize()
                    assert init.serverInfo.name=='OpenPKLab'
                    made=await session.call_tool('create_experiment',{'title':'Real HTTP','category':'in_vitro','experiment_id':'real-http'})
                    assert not made.isError
                    upload=await client.post(url+'/experiments/real-http/files?filename=measurements.csv',content=b'time,concentration\n0,4\n1,2\n')
                    assert upload.status_code==201
                    file_id=upload.json()['file']['id']
                    checked=await session.call_tool('analyze_dataset',{'experiment_id':'real-http','file_id':file_id})
                    assert not checked.isError and checked.structuredContent['rows']==2
                    exported=await session.call_tool('export_notebook',{'experiment_id':'real-http'})
                    path=exported.structuredContent['download_path']
                    download=await client.get(url+path)
                    assert download.status_code==200 and download.content[:2]==b'PK'
                    assert httpx.get(url+path).status_code==401
        assert Notebook(tmp_path/'data').get('real-http')['files'][0]['id']==file_id
    finally:
        proc.terminate()
        try: proc.wait(timeout=10)
        except subprocess.TimeoutExpired: proc.kill(); proc.wait(timeout=5)
        log.close()
