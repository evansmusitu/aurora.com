"""Dependency-free CI verifier for MUSITU Blender asset pipeline outputs."""
import hashlib
import json
from pathlib import Path
import struct
import sys


def validate(out):
    out=Path(out)
    data=json.loads((out/'studio_evidence.json').read_text())
    assert data['result']=='PASS',data
    assert data['renderer']=='CYCLES_CPU' and data['gpu_verified'] is False
    assert set(data['named_asset_roots']) == {'ARCH_Pavilion_Root','PRODUCT_Vehicle_Root','CHAR_Stylized_Root'}
    assert data['animated_objects']>=1
    expected={'MUSITU_Studio_Prototype.blend','MUSITU_Studio_Animated_Assets.glb','MUSITU_Studio_Preview.png'}
    assert set(data['files'])==expected
    for name,record in data['files'].items():
        path=out/name
        assert path.is_file() and path.stat().st_size==record['bytes'] and record['bytes']>1000,name
        assert hashlib.sha256(path.read_bytes()).hexdigest()==record['sha256'],name
    blend=(out/'MUSITU_Studio_Prototype.blend').read_bytes()
    assert blend[:7]==b'BLENDER','not native Blender project'
    image=(out/'MUSITU_Studio_Preview.png').read_bytes()
    assert image[:8]==b'\x89PNG\r\n\x1a\n','not PNG'
    width,height=struct.unpack('>II',image[16:24])
    assert (width,height)==(480,300), (width,height)
    glb=(out/'MUSITU_Studio_Animated_Assets.glb').read_bytes()
    magic,version,length=struct.unpack('<4sII',glb[:12])
    assert (magic,version,length)==(b'glTF',2,len(glb)), 'bad GLB header'
    chunk_size,kind=struct.unpack('<I4s',glb[12:20])
    assert kind==b'JSON', 'missing GLB JSON chunk'
    scene=json.loads(glb[20:20+chunk_size])
    names=[str(node.get('name','')) for node in scene.get('nodes',[])]
    for required_prefix in ['ARCH_','PRODUCT_','CHAR_']:
        assert sum(n.startswith(required_prefix) for n in names)>=3, (required_prefix,names)
    assert len(scene.get('meshes',[]))>=15, len(scene.get('meshes',[]))
    assert len(scene.get('animations',[]))>=1, 'animated glTF export must contain animation'
    summary={'result':'PASS','native_blend_bytes':len(blend),'png_width':width,'png_height':height,
             'gltf_mesh_count':len(scene.get('meshes',[])),'gltf_animations':len(scene.get('animations',[])),
             'glb_sha256':hashlib.sha256(glb).hexdigest(),'source_evidence_sha256':hashlib.sha256((out/'studio_evidence.json').read_bytes()).hexdigest()}
    (out/'verification_summary.json').write_text(json.dumps(summary,indent=2,sort_keys=True)+'\n')
    print('VERIFIED_STUDIO_ASSET_PIPELINE',json.dumps(summary,sort_keys=True))
    return summary

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('Usage: python verify_studio.py OUTDIR')
    validate(sys.argv[1])
