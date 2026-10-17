"""MUSITU studio CI integration test (runs inside actual Blender 4.5 LTS).

Builds architecture / product / stylized character example assets without
network access, renders a short CPU preview, and exports a GLB animation.
This is a software integration test, NOT a production rendering service.
"""
import bpy
import hashlib
import json
import math
from mathutils import Vector
from pathlib import Path
import sys
import time
import traceback


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, 'rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def material(name, color, metallic=0.0, roughness=0.6):
    m = bpy.data.materials.new(name)
    m.diffuse_color = (*color, 1.0)
    m.use_nodes = True
    shader = m.node_tree.nodes.get('Principled BSDF')
    shader.inputs['Base Color'].default_value = (*color, 1.0)
    shader.inputs['Metallic'].default_value = metallic
    shader.inputs['Roughness'].default_value = roughness
    return m


def primitive_cube(name, xyz, dimensions, mat, bevel=0.0):
    bpy.ops.mesh.primitive_cube_add(size=1, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(mat)
    if bevel:
        modifier = obj.modifiers.new('Rounded edges', 'BEVEL')
        modifier.width = bevel
        modifier.segments = 2
        obj.modifiers.new('Weighted normals', 'WEIGHTED_NORMAL')
    return obj


def primitive_cylinder(name, xyz, radius, depth, mat, vertices=24):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=xyz)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(mat)
    return obj


def parent_keep_world(obj, parent):
    world = obj.matrix_world.copy()
    obj.parent = parent
    obj.matrix_world = world
    return obj


def empty(name, location):
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=location)
    bpy.context.object.name = name
    return bpy.context.object


def animate_rotation(obj, axis, at_a, at_b, start=1, end=32):
    obj.rotation_mode = 'XYZ'
    obj.rotation_euler[axis] = at_a
    obj.keyframe_insert(data_path='rotation_euler', frame=start)
    obj.rotation_euler[axis] = at_b
    obj.keyframe_insert(data_path='rotation_euler', frame=end)
    if obj.animation_data and obj.animation_data.action:
        obj.animation_data.action.name = 'MUSITU_' + obj.name + '_Movement'


def create_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene['musitu_demo_only'] = True
    scene['project'] = 'MUSITU Foundry 3D Workflow Integration'
    scene['categories'] = 'architecture, product visualization, character animation'
    scene['asset_origin'] = 'procedurally created within Blender; no third-party assets'
    scene.unit_settings.system = 'METRIC'
    scene.frame_start = 1
    scene.frame_end = 32
    scene.render.film_transparent = False

    charcoal = material('Studio Graphite', (.06, .085, .11), 0.15)
    gold = material('Studio Burnt Gold', (.85, .39, .085), 0.45, 0.3)
    blue = material('Studio Deep Teal', (.015, .31, .39), 0.2)
    pale = material('Architectural White', (.82, .87, .86), 0.0)
    glass = material('Blue Glass Stylized', (.15, .54, .7), 0.05)
    tire = material('Rubber', (.012, .016, .023), 0.05)
    ground = material('Studio Floor', (.16, .19, .22), 0.05)
    skin = material('Character Gold', (.91, .53, .22), 0.0)

    primitive_cube('STUDIO_ground', (0,0,-.16), (16,9,.30), ground, 0.02)

    # Department A: modular building concept (not certified architectural BIM).
    arch = empty('ARCH_Pavilion_Root', (-5.0,0,0))
    for name, xyz, dims, mat in [
        ('ARCH_floor',(-5.0,0.0,.12),(3.0,2.9,.24),pale),
        ('ARCH_back_wall',(-5.0,1.18,1.65),(3.0,.18,2.95),pale),
        ('ARCH_left_wall',(-6.37,0,1.65),(.18,2.6,2.95),pale),
        ('ARCH_roof',(-5.0,0,3.25),(3.5,3.15,.21),blue),
        ('ARCH_window_panel',(-4.95,1.065,1.89),(1.28,.09,1.53),glass),
        ('ARCH_sill',(-4.95,.98,1.07),(1.43,.24,.12),gold),
    ]:
        parent_keep_world(primitive_cube(name, xyz, dims, mat, .035), arch)
    for x in (-3.66,-6.35):
        parent_keep_world(primitive_cube('ARCH_column_'+str(x), (x,-1.20,1.65),(.20,.20,3.0),gold),arch)

    # Department B: stylized four-wheel mobility product, with moving wheels.
    product = empty('PRODUCT_Vehicle_Root', (0.2,0,0))
    parent_keep_world(primitive_cube('PRODUCT_chassis', (0.2,0,1.02),(3.35,1.55,.72),blue,.18),product)
    parent_keep_world(primitive_cube('PRODUCT_cabin', (-.20,0,1.73),(1.75,1.30,.83),glass,.14),product)
    parent_keep_world(primitive_cube('PRODUCT_front', (1.76,0,1.03),(.24,1.40,.32),gold,.06),product)
    parent_keep_world(primitive_cube('PRODUCT_rear', (-1.42,0,1.03),(.24,1.4,.32),gold,.06),product)
    wheels = []
    for x in (-.95,1.31):
        for y in (-.79,.79):
            wheel = primitive_cylinder('PRODUCT_wheel_{}_{}'.format(str(x).replace('-','N'),str(y).replace('-','N')),(x,y,.53),.47,.26,tire)
            wheel.rotation_euler[0] = math.pi/2
            parent_keep_world(wheel, product)
            wheels.append(wheel)
            animate_rotation(wheel, 0, math.pi/2, math.pi/2 + 2*math.pi)

    # Department C: stylized figure with keyed object animation (not rigged).
    char = empty('CHAR_Stylized_Root',(4.5,0,0))
    parent_keep_world(primitive_cube('CHAR_torso',(4.5,0,1.66),(.77,.44,1.12),gold,.12),char)
    parent_keep_world(primitive_cube('CHAR_head',(4.5,0,2.52),(.59,.51,.59),skin,.18),char)
    for x in (4.29,4.71):
        parent_keep_world(primitive_cube('CHAR_leg_'+str(x),(x,0,.62),(.30,.32,1.04),charcoal,.09),char)
    shoulder = empty('CHAR_RightArm_Pivot',(4.98,0,2.00))
    parent_keep_world(shoulder,char)
    parent_keep_world(primitive_cube('CHAR_RightArm',(5.14,0,1.61),(.26,.27,.85),skin,.07),shoulder)
    animate_rotation(shoulder,1,-0.06,-0.65)
    parent_keep_world(primitive_cube('CHAR_LeftArm',(4.00,0,1.62),(.28,.27,.85),skin,.07),char)

    # Presentation only: camera and lights are not geometry certification.
    bpy.ops.object.camera_add(location=(10,-18,11.0))
    cam = bpy.context.object
    cam.name='STUDIO_PreviewCamera'
    target=Vector((0,0,1.13))
    cam.rotation_euler=(target - cam.location).to_track_quat('-Z','Y').to_euler()
    cam.data.type='ORTHO'
    cam.data.ortho_scale=16.4
    scene.camera=cam
    for name,xyz,power,size in [('STUDIO_KeyLight',(-3,-5,11),1550,8),('STUDIO_FillLight',(7,1,10),1100,7)]:
        bpy.ops.object.light_add(type='AREA', location=xyz)
        light=bpy.context.object
        light.name=name
        light.data.energy=power
        light.data.shape='DISK'
        light.data.size=size
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=10
    scene.render.resolution_x=480
    scene.render.resolution_y=300
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.frame_set(1)
    scene.world.color=(.13,.13,.13)
    return scene


def main():
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    if len(argv)!=2 or argv[0]!='--outdir':
        raise SystemExit('Usage: blender -b --python studio_asset_pipeline.py -- --outdir PATH')
    out=Path(argv[1]).resolve()
    out.mkdir(parents=True,exist_ok=True)
    evidence={
        'schema':'musitu.studio.ci-asset-integration.v1',
        'result':'FAIL', 'blender':bpy.app.version_string,
        'renderer':'CYCLES_CPU', 'gpu_verified':False,
        'external_asset_dependencies':False, 'timestamp_unix':int(time.time()),
        'intent':'software pipeline integration test; not production render farm',
    }
    try:
        scene=create_scene()
        blend=out/'MUSITU_Studio_Prototype.blend'
        glb=out/'MUSITU_Studio_Animated_Assets.glb'
        preview=out/'MUSITU_Studio_Preview.png'
        scene.render.filepath=str(preview)
        bpy.ops.wm.save_as_mainfile(filepath=str(blend))
        export_result=bpy.ops.export_scene.gltf(filepath=str(glb),export_format='GLB',export_animations=True)
        if 'FINISHED' not in export_result:
            raise RuntimeError('glTF exporter did not return FINISHED')
        bpy.ops.render.render(write_still=True)
        evidence['objects_in_blend']=len(bpy.data.objects)
        evidence['named_asset_roots']=[ob.name for ob in bpy.data.objects if ob.name in ('ARCH_Pavilion_Root','PRODUCT_Vehicle_Root','CHAR_Stylized_Root')]
        evidence['animated_objects']=len([ob for ob in bpy.data.objects if ob.animation_data and ob.animation_data.action])
        evidence['files']={p.name:{'bytes':p.stat().st_size,'sha256':sha256_file(p)} for p in (blend,glb,preview)}
        assert len(evidence['named_asset_roots'])==3
        assert evidence['animated_objects']>=1
        assert all(p.is_file() and p.stat().st_size>1000 for p in (blend,glb,preview))
        evidence['result']='PASS'
    except Exception as exc:
        evidence['error']=str(exc)
        evidence['traceback']=traceback.format_exc()[-3500:]
        raise
    finally:
        (out/'studio_evidence.json').write_text(json.dumps(evidence,indent=2,sort_keys=True)+'\n')
        print('MUSITU_STUDIO_EVIDENCE='+json.dumps(evidence,sort_keys=True),flush=True)

if __name__=='__main__':
    main()