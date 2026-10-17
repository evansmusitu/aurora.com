"""MUSITU enterprise CI proof: actually create, save and CPU-render a Blender scene.

Runs inside genuine Blender, not ordinary Python. No network, credentials or other
project files are accessed. All results stay inside the caller-supplied folder.
"""
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback

import bpy

def digest(p):
    h=hashlib.sha256()
    with open(p,"rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    argv=sys.argv[sys.argv.index("--")+1:] if "--" in sys.argv else []
    if len(argv)!=2 or argv[0]!="--outdir":
        raise SystemExit("Usage: blender -b --python blender_smoke.py -- --outdir DIR")
    out=Path(argv[1]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    evidence={"schema":"musitu.blender.actual-execution.v1","blender":bpy.app.version_string,
              "engine":"CYCLES","device":"CPU","result":"FAIL",
              "time_unix":int(time.time()),"gpu_verified":False}
    try:
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.ops.mesh.primitive_cube_add(size=2.0,location=(0,0,0))
        cube=bpy.context.object
        cube.name="MUSITU Proof Cube"
        material=bpy.data.materials.new("MUSITU Copper")
        material.diffuse_color=(0.75,0.23,0.07,1.0)
        material.use_nodes=True
        material.node_tree.nodes.get("Principled BSDF").inputs["Base Color"].default_value=(0.75,0.23,0.07,1.0)
        cube.data.materials.append(material)
        bpy.ops.object.light_add(type="AREA",location=(1.0,-3.0,5.0))
        bpy.context.object.data.energy=550
        bpy.ops.object.camera_add(location=(4,-6,3))
        camera=bpy.context.object
        camera.rotation_euler=(cube.location-camera.location).to_track_quat("-Z","Y").to_euler()
        scene=bpy.context.scene
        scene.camera=camera
        scene.render.engine="CYCLES"
        scene.cycles.device="CPU"
        scene.cycles.samples=8
        scene.render.resolution_x=192
        scene.render.resolution_y=192
        scene.render.resolution_percentage=100
        scene.render.image_settings.file_format="PNG"
        scene.render.filepath=str(out/"cpu_render.png")
        blend=out/"MUSITU_Blender_Actual_Execution.blend"
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        bpy.ops.render.render(write_still=True)
        png=out/"cpu_render.png"
        if not png.exists() or png.stat().st_size<1000 or png.open("rb").read(8)!=b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Missing, corrupt, or unexpectedly small PNG render")
        if not blend.exists() or blend.stat().st_size<2000:
            raise RuntimeError("No real Blender .blend scene saved")
        evidence.update(result="PASS",blend_bytes=blend.stat().st_size,
                        blend_sha256=digest(blend),png_bytes=png.stat().st_size,
                        png_sha256=digest(png),scene_objects=len(bpy.data.objects))
    except Exception as exc:
        evidence["error"]=str(exc)
        evidence["traceback"]=traceback.format_exc()[-3000:]
        raise
    finally:
        (out/"execution_evidence.json").write_text(json.dumps(evidence,indent=2,sort_keys=True)+"\n")
        print("MUSITU_BLENDER_EVIDENCE="+json.dumps(evidence,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
