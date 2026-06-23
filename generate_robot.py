"""
ROBA Robot Humanoid — T-Pose Generator (Challenge 3: Roba Robot T-Pose 3D Simple)
================================================================================
Generates:
  • index.glb       -> [Required] Rigged humanoid character in T-pose
  • ROBA_rigged.glb -> Rigged version
  • ROBA_static.glb -> Static version (same geometry, no skeleton or skin weights)

Requirements:
    pip install pygltflib numpy

Usage:
    python generate_robot.py
"""

import os
import math
import numpy as np
import pygltflib
from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Accessor, BufferView, Buffer,
    Material, Skin, Asset,
    ARRAY_BUFFER, ELEMENT_ARRAY_BUFFER,
    FLOAT, UNSIGNED_SHORT, UNSIGNED_BYTE,
    VEC3, VEC4, MAT4, SCALAR,
)

# ── Colour palette ────────────────────────────────────────────────────────────
# Metallic grey PBR materials
# baseColorFactor: [R, G, B, A]
# Slight color variation: torso/head slightly lighter than limbs, joints darker.
COLOR_TORSO  = [0.70, 0.70, 0.75, 1.0] # lighter grey
COLOR_LIMBS  = [0.62, 0.62, 0.67, 1.0] # neutral grey
COLOR_JOINTS = [0.55, 0.55, 0.60, 1.0] # darker grey

# ── Low-level geometry primitives ────────────────────────────────────────────

def _box(w, h, d):
    hw, hh, hd = w/2, h/2, d/2
    pos = np.array([
        [-hw,-hh,-hd],[-hw,-hh, hd],[-hw, hh, hd],[-hw, hh,-hd],
        [ hw,-hh,-hd],[ hw, hh,-hd],[ hw, hh, hd],[ hw,-hh, hd],
        [-hw,-hh,-hd],[ hw,-hh,-hd],[ hw,-hh, hd],[-hw,-hh, hd],
        [-hw, hh,-hd],[-hw, hh, hd],[ hw, hh, hd],[ hw, hh,-hd],
        [-hw,-hh,-hd],[-hw, hh,-hd],[ hw, hh,-hd],[ hw,-hh,-hd],
        [-hw,-hh, hd],[ hw,-hh, hd],[ hw, hh, hd],[-hw, hh, hd],
    ], dtype=np.float32)
    nor = np.repeat([
        [-1,0,0],[1,0,0],[0,-1,0],[0,1,0],[0,0,-1],[0,0,1]
    ], 4, axis=0).astype(np.float32)
    idx = np.array([
        0,1,2, 0,2,3,   4,5,6, 4,6,7,
        8,9,10, 8,10,11, 12,13,14, 12,14,15,
        16,17,18,16,18,19, 20,21,22,20,22,23,
    ], dtype=np.uint16)
    return pos, nor, idx


def _cylinder(radius=0.05, height=0.2, segs=12, axis='y'):
    angles = np.linspace(0, 2*math.pi, segs, endpoint=False)
    verts, norms, tris = [], [], []
    hh = height / 2
    for i in range(segs):
        a0, a1 = angles[i], angles[(i+1) % segs]
        for a in (a0, a1):
            c, s = math.cos(a)*radius, math.sin(a)*radius
            nc, ns = math.cos(a), math.sin(a)
            if   axis=='y': verts += [[c,-hh,s],[c, hh,s]]; norms += [[nc,0,ns],[nc,0,ns]]
            elif axis=='z': verts += [[c,s,-hh],[c,s, hh]]; norms += [[nc,ns,0],[nc,ns,0]]
            else:           verts += [[-hh,c,s],[ hh,c,s]]; norms += [[0,nc,ns],[0,nc,ns]]
        b = i*4
        tris += [b,b+1,b+3, b,b+3,b+2]
    # caps
    for sign in (-1, 1):
        if   axis=='y': ctr=[0, sign*hh, 0]; cn=[0,sign,0]
        elif axis=='z': ctr=[0,0, sign*hh];  cn=[0,0,sign]
        else:           ctr=[sign*hh,0,0];   cn=[sign,0,0]
        cb = len(verts)
        verts.append(ctr); norms.append(cn)
        for i in range(segs):
            c,s = math.cos(angles[i])*radius, math.sin(angles[i])*radius
            if   axis=='y': verts.append([c, sign*hh, s])
            elif axis=='z': verts.append([c, s, sign*hh])
            else:           verts.append([sign*hh, c, s])
            norms.append(cn)
        for i in range(segs):
            a, b2 = cb+1+i, cb+1+(i+1)%segs
            if sign==1: tris += [cb,a,b2]
            else:       tris += [cb,b2,a]
    return (np.array(verts,dtype=np.float32),
            np.array(norms,dtype=np.float32),
            np.array(tris, dtype=np.uint16))


def _sphere(radius=0.10, lat=8, lon=12):
    verts, norms, tris = [], [], []
    for i in range(lat+1):
        th = math.pi*i/lat
        for j in range(lon):
            ph = 2*math.pi*j/lon
            x = math.sin(th)*math.cos(ph)
            y = math.cos(th)
            z = math.sin(th)*math.sin(ph)
            verts.append([x*radius, y*radius, z*radius])
            norms.append([x, y, z])
    for i in range(lat):
        for j in range(lon):
            a = i*lon+j; b = a+lon
            c = i*lon+(j+1)%lon
            d = i*lon+(j+1)%lon+lon
            tris += [a,b,c, b,d,c]
    return (np.array(verts,dtype=np.float32),
            np.array(norms,dtype=np.float32),
            np.array(tris, dtype=np.uint16))

# ── GLB builder ───────────────────────────────────────────────────────────────

class Builder:
    def __init__(self):
        g = GLTF2()
        g.asset = Asset(version="2.0", generator="roba-tpose-gen-yup")
        g.scene = 0
        g.scenes = [Scene(nodes=[])]
        g.nodes, g.meshes, g.materials = [], [], []
        g.accessors, g.bufferViews, g.buffers, g.skins = [], [], [], []
        self.g = g
        self._bin = bytearray()

    def _bv(self, data: bytes, target=None):
        pad = (-len(self._bin)) % 4
        self._bin += b'\x00'*pad
        off = len(self._bin)
        self._bin += data
        bv = BufferView(buffer=0, byteOffset=off, byteLength=len(data))
        if target: bv.target = target
        i = len(self.g.bufferViews); self.g.bufferViews.append(bv); return i

    def _acc(self, bv, count, ctype, atype, mn=None, mx=None):
        a = Accessor(bufferView=bv, byteOffset=0,
                     componentType=ctype, type=atype, count=count)
        if mn is not None: a.min=[float(v) for v in mn]
        if mx is not None: a.max=[float(v) for v in mx]
        i = len(self.g.accessors); self.g.accessors.append(a); return i

    def mat(self, color, metallic=0.6, roughness=0.4):
        m = Material()
        m.pbrMetallicRoughness = pygltflib.PbrMetallicRoughness(
            baseColorFactor=color,
            metallicFactor =metallic,
            roughnessFactor=roughness)
        i = len(self.g.materials); self.g.materials.append(m); return i

    def mesh_with_primitives(self, prims_data):
        # prims_data is a list of tuples: (pos, nor, idx, mat_idx, ji, jw)
        primitives = []
        for pos, nor, idx, mat_idx, ji, jw in prims_data:
            bv_p = self._bv(pos.tobytes(), ARRAY_BUFFER)
            bv_n = self._bv(nor.tobytes(), ARRAY_BUFFER)
            bv_i = self._bv(idx.tobytes(), ELEMENT_ARRAY_BUFFER)
            ap = self._acc(bv_p, len(pos), FLOAT, VEC3, pos.min(0), pos.max(0))
            an = self._acc(bv_n, len(nor), FLOAT, VEC3)
            ai = self._acc(bv_i, len(idx), UNSIGNED_SHORT, SCALAR)
            attr = pygltflib.Attributes(POSITION=ap, NORMAL=an)
            if ji is not None and jw is not None:
                bv_ji = self._bv(ji.astype(np.uint8).tobytes(), ARRAY_BUFFER)
                bv_jw = self._bv(jw.astype(np.float32).tobytes(), ARRAY_BUFFER)
                attr.JOINTS_0  = self._acc(bv_ji, len(ji), UNSIGNED_BYTE, VEC4)
                attr.WEIGHTS_0 = self._acc(bv_jw, len(jw), FLOAT, VEC4)
            prim = Primitive(attributes=attr, indices=ai, material=mat_idx, mode=4)
            primitives.append(prim)
        
        i = len(self.g.meshes)
        self.g.meshes.append(Mesh(primitives=primitives))
        return i

    def node(self, name, t=(0,0,0), children=None, mesh=None, skin=None):
        n=Node(name=name,translation=list(t))
        if children: n.children=children
        if mesh is not None: n.mesh=mesh
        if skin is not None: n.skin=skin
        i=len(self.g.nodes); self.g.nodes.append(n); return i

    def skin(self, name, joints, ibms):
        flat=np.array(ibms,dtype=np.float32).reshape(-1)
        bv=self._bv(flat.tobytes())
        acc=self._acc(bv,len(joints),FLOAT,MAT4)
        s=Skin(name=name,joints=joints,inverseBindMatrices=acc)
        i=len(self.g.skins); self.g.skins.append(s); return i

    def save(self, path):
        self.g.buffers=[Buffer(byteLength=len(self._bin))]
        self.g.set_binary_blob(bytes(self._bin))
        self.g.save_binary(path)
        print(f"[OK] Saved -> {path}")

# ── Robot geometry parts definition ──────────────────────────────────────────

def get_geometry_parts(mT, mL, mJ):
    parts = []
    
    def bx(w, h, d, tx, ty, tz, m, bi):
        p, n, i = _box(w, h, d)
        p += np.array([tx, ty, tz], dtype=np.float32)
        parts.append((p, n, i, m, bi))
        
    def cy(r, h, tx, ty, tz, m, bi, ax='y'):
        p, n, i = _cylinder(r, h, axis=ax)
        p += np.array([tx, ty, tz], dtype=np.float32)
        parts.append((p, n, i, m, bi))
        
    def sp(r, tx, ty, tz, m, bi):
        p, n, i = _sphere(r)
        p += np.array([tx, ty, tz], dtype=np.float32)
        parts.append((p, n, i, m, bi))

    # 1. Pelvis block (skinned to root=0)
    bx(0.26, 0.12, 0.16,  0.0, 1.04, 0.0, mT, 0)
    
    # 2. Waist cylinder (skinned to spine=1)
    cy(0.06, 0.08,  0.0, 1.10, 0.0, mJ, 1, 'y')
    
    # 3. rounded torso (0.32×0.38×0.18m) (skinned to chest=2)
    bx(0.32, 0.38, 0.18,  0.0, 1.29, 0.0, mT, 2)
    
    # 4. Chest plate (skinned to chest=2)
    bx(0.26, 0.22, 0.03,  0.0, 1.35, 0.09, mJ, 2)
    
    # 5. Cylindrical neck (skinned to neck=3)
    cy(0.045, 0.10,  0.0, 1.53, 0.0, mJ, 3, 'y')
    
    # 6. Helmet-style head base (skinned to head=4)
    cy(0.10, 0.14,  0.0, 1.68, 0.0, mT, 4, 'y')
    # 7. Head dome cap (skinned to head=4)
    sp(0.10,  0.0, 1.75, 0.0, mT, 4)
    # 8. Visor (skinned to head=4)
    bx(0.16, 0.06, 0.03,  0.0, 1.68, 0.09, mJ, 4)

    # Left Arm
    # 9. Shoulder cap (skinned to l_shoulder=5)
    sp(0.06,  0.22, 1.40, 0.0, mJ, 5)
    # 10. Upper arm cylinder (skinned to l_shoulder=5)
    cy(0.05, 0.24,  0.37, 1.40, 0.0, mL, 5, 'x')
    # 11. Elbow joint (skinned to l_elbow=6)
    sp(0.05,  0.52, 1.40, 0.0, mJ, 6)
    # 12. Forearm cylinder (skinned to l_elbow=6)
    cy(0.045, 0.20,  0.645, 1.40, 0.0, mL, 6, 'x')
    # 13. Flat hand block (skinned to l_hand=7)
    bx(0.10, 0.02, 0.08,  0.795, 1.40, 0.0, mJ, 7)

    # Right Arm
    # 14. Shoulder cap (skinned to r_shoulder=8)
    sp(0.06, -0.22, 1.40, 0.0, mJ, 8)
    # 15. Upper arm cylinder (skinned to r_shoulder=8)
    cy(0.05, 0.24, -0.37, 1.40, 0.0, mL, 8, 'x')
    # 16. Elbow joint (skinned to r_elbow=9)
    sp(0.05, -0.52, 1.40, 0.0, mJ, 9)
    # 17. Forearm cylinder (skinned to r_elbow=9)
    cy(0.045, 0.20, -0.645, 1.40, 0.0, mL, 9, 'x')
    # 18. Flat hand block (skinned to r_hand=10)
    bx(0.10, 0.02, 0.08, -0.795, 1.40, 0.0, mJ, 10)

    # Left Leg
    # 19. Hip cap (skinned to l_hip=11)
    sp(0.06,  0.12, 0.98, 0.0, mJ, 11)
    # 20. Upper leg cylinder (skinned to l_hip=11)
    cy(0.05, 0.38,  0.12, 0.755, 0.0, mL, 11, 'y')
    # 21. Knee joint (skinned to l_knee=12)
    sp(0.05,  0.12, 0.53, 0.0, mJ, 12)
    # 22. Lower leg cylinder (skinned to l_knee=12)
    cy(0.045, 0.38,  0.12, 0.305, 0.0, mL, 12, 'y')
    # 23. Ankle joint (skinned to l_foot=13)
    sp(0.04,  0.12, 0.08, 0.0, mJ, 13)
    # 24. Flat foot block (skinned to l_foot=13)
    bx(0.08, 0.08, 0.20,  0.12, 0.04, 0.06, mJ, 13)

    # Right Leg
    # 25. Hip cap (skinned to r_hip=14)
    sp(0.06, -0.12, 0.98, 0.0, mJ, 14)
    # 26. Upper leg cylinder (skinned to r_hip=14)
    cy(0.05, 0.38, -0.12, 0.755, 0.0, mL, 14, 'y')
    # 27. Knee joint (skinned to r_knee=15)
    sp(0.05, -0.12, 0.53, 0.0, mJ, 15)
    # 28. Lower leg cylinder (skinned to r_knee=15)
    cy(0.045, 0.38, -0.12, 0.305, 0.0, mL, 15, 'y')
    # 29. Ankle joint (skinned to r_foot=16)
    sp(0.04, -0.12, 0.08, 0.0, mJ, 16)
    # 30. Flat foot block (skinned to r_foot=16)
    bx(0.08, 0.08, 0.20, -0.12, 0.04, 0.06, mJ, 16)

    return parts

# ── Build methods ─────────────────────────────────────────────────────────────

def build_rigged(out_path):
    b = Builder()
    mT = b.mat(COLOR_TORSO); mL = b.mat(COLOR_LIMBS); mJ = b.mat(COLOR_JOINTS)

    # 17-joint positions in world space
    BW = [
        np.array([ 0.0,  1.04,  0.0 ]),   # 0  root (hips)
        np.array([ 0.0,  1.15,  0.0 ]),   # 1  spine
        np.array([ 0.0,  1.35,  0.0 ]),   # 2  chest
        np.array([ 0.0,  1.53,  0.0 ]),   # 3  neck
        np.array([ 0.0,  1.70,  0.0 ]),   # 4  head
        np.array([ 0.22, 1.40,  0.0 ]),   # 5  l_shoulder
        np.array([ 0.52, 1.40,  0.0 ]),   # 6  l_elbow
        np.array([ 0.77, 1.40,  0.0 ]),   # 7  l_hand
        np.array([-0.22, 1.40,  0.0 ]),   # 8  r_shoulder
        np.array([-0.52, 1.40,  0.0 ]),   # 9  r_elbow
        np.array([-0.77, 1.40,  0.0 ]),   # 10 r_hand
        np.array([ 0.12, 0.98,  0.0 ]),   # 11 l_hip
        np.array([ 0.12, 0.53,  0.0 ]),   # 12 l_knee
        np.array([ 0.12, 0.08,  0.0 ]),   # 13 l_foot
        np.array([-0.12, 0.98,  0.0 ]),   # 14 r_hip
        np.array([-0.12, 0.53,  0.0 ]),   # 15 r_knee
        np.array([-0.12, 0.08,  0.0 ]),   # 16 r_foot
    ]
    NAMES  = [
        "root", "spine", "chest", "neck", "head",
        "l_shoulder", "l_elbow", "l_hand",
        "r_shoulder", "r_elbow", "r_hand",
        "l_hip", "l_knee", "l_foot",
        "r_hip", "r_knee", "r_foot"
    ]
    PARENT = [
        -1, 0, 1, 2, 3,
        2, 5, 6,
        2, 8, 9,
        0, 11, 12,
        0, 14, 15
    ]

    # Build bone nodes
    bone_ni = []
    for i, name in enumerate(NAMES):
        p = PARENT[i]
        lt = (BW[i] - BW[p]).tolist() if p != -1 else BW[i].tolist()
        bone_ni.append(b.node(name, t=lt))

    # Wire bone hierarchy
    for i, p in enumerate(PARENT):
        if p != -1:
            pn = b.g.nodes[bone_ni[p]]
            if pn.children is None:
                pn.children = []
            pn.children.append(bone_ni[i])

    # Inverse bind matrices (column-major translation matrices)
    ibms = []
    for wp in BW:
        m = np.eye(4, dtype=np.float32)
        m[3, :3] = -wp
        ibms.append(m)
    skin_i = b.skin("ArmatureSkin", bone_ni, ibms)

    # Get body parts
    parts = get_geometry_parts(mT, mL, mJ)

    # Generate 30 separate primitives (one primitive per body part geometry)
    prims_data = []
    for pos, nor, idx, mat_idx, bi in parts:
        n = len(pos)
        ji = np.zeros((n, 4), dtype=np.uint8)
        ji[:, 0] = bi
        jw = np.zeros((n, 4), dtype=np.float32)
        jw[:, 0] = 1.0
        prims_data.append((pos, nor, idx, mat_idx, ji, jw))

    mesh_i = b.mesh_with_primitives(prims_data)

    # Scene graph connection
    # To fix NODE_SKINNED_MESH_NON_ROOT, make the mesh node a root node alongside the armature root bone
    mesh_node = b.node("ROBA_Robot_Rigged_Mesh", mesh=mesh_i, skin=skin_i)
    
    # Scene has two root nodes: the armature root (root) and the skinned mesh node
    b.g.scenes[0].nodes = [bone_ni[0], mesh_node]

    # Save to destination path
    b.save(out_path)


def build_static(out_path):
    b = Builder()
    mT = b.mat(COLOR_TORSO); mL = b.mat(COLOR_LIMBS); mJ = b.mat(COLOR_JOINTS)

    # Get body parts
    parts = get_geometry_parts(mT, mL, mJ)

    # Build GLB mesh primitives without skin weight attributes
    prims_data = []
    for pos, nor, idx, mat_idx, _ in parts:
        prims_data.append((pos, nor, idx, mat_idx, None, None))

    mesh_i = b.mesh_with_primitives(prims_data)

    # Scene graph connection for static (direct layout)
    mesh_node = b.node("ROBA_Robot_Static_Mesh", mesh=mesh_i)
    b.g.scenes[0].nodes = [mesh_node]

    b.save(out_path)


if __name__ == "__main__":
    out_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 1. Output index.glb (required preview - rigged)
    print("Building rigged ROBA humanoid T-pose (index.glb)...")
    build_rigged(os.path.join(out_dir, "index.glb"))
    
    # 2. Output ROBA_rigged.glb
    print("Building rigged ROBA humanoid T-pose (ROBA_rigged.glb)...")
    build_rigged(os.path.join(out_dir, "ROBA_rigged.glb"))
    
    # 3. Output ROBA_static.glb
    print("Building static ROBA humanoid T-pose (ROBA_static.glb)...")
    build_static(os.path.join(out_dir, "ROBA_static.glb"))
    
    print("\n* All GLB models generated successfully!")
