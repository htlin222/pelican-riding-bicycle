import bpy, math, os
from mathutils import Vector, Matrix
def setup(w=1280,h=536,spp=48,gpu=False,mblur=True):
    sc=bpy.context.scene; r=sc.render
    r.engine='CYCLES'; r.resolution_x=w; r.resolution_y=h; r.resolution_percentage=100
    r.fps=24; r.image_settings.file_format='JPEG'; r.image_settings.quality=96
    c=sc.cycles; c.samples=spp; c.use_adaptive_sampling=True; c.adaptive_threshold=0.03
    c.use_denoising=True
    try: c.denoiser='OPENIMAGEDENOISE'
    except Exception as e: print('denoiser',e)
    c.max_bounces=6; c.diffuse_bounces=2; c.glossy_bounces=3; c.transmission_bounces=4; c.transparent_max_bounces=8; c.volume_bounces=0
    c.sample_clamp_indirect=6.0; c.sample_clamp_direct=0.0; c.caustics_reflective=False; c.caustics_refractive=False
    c.use_light_tree=True
    r.use_motion_blur=mblur; r.motion_blur_shutter=0.32
    r.use_persistent_data=True
    vs=sc.view_settings
    try: vs.view_transform='AgX'; vs.look='AgX - Medium High Contrast'
    except Exception as e: print('view',e)
    vs.exposure=-1.6; vs.gamma=1.0
    if gpu:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        for t in ('OPTIX','CUDA'):
            try:
                prefs.compute_device_type=t; prefs.get_devices()
                ok=False
                for d in prefs.devices:
                    d.use=(d.type!='CPU'); ok=ok or d.use
                if ok: c.device='GPU'; print('GPU:',t,[d.name for d in prefs.devices if d.use]); break
            except Exception as e: print('gpu',t,e)
        try: c.denoising_use_gpu=True
        except Exception: pass
    return sc
def make_camera():
    cd=bpy.data.cameras.new('Cam'); ob=bpy.data.objects.new('Cam',cd); bpy.context.scene.collection.objects.link(ob)
    bpy.context.scene.camera=ob; cd.sensor_width=36; cd.clip_start=0.05; cd.clip_end=40000; ob.rotation_mode='QUATERNION'
    return ob
def aim(cam,pos,target,vfov_deg,roll=0.0,aspect=2.39):
    pos=Vector(pos); d=(Vector(target)-pos)
    q=d.to_track_quat('-Z','Y')
    if roll: q=q@Matrix.Rotation(roll,4,'Z').to_quaternion()
    cam.location=pos; cam.rotation_quaternion=q
    hf=2*math.atan(math.tan(math.radians(vfov_deg)/2)*aspect)
    cam.data.lens=18/math.tan(hf/2)
