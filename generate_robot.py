"""
ROBA Robot Humanoid Proxy — T-Pose  (Challenge 3: Roba Robot T-Pose 3D Simple)
================================================================================
Generates  index.glb  containing:
  • Coloured PBR geometry (White Armour / Dark Grey Metal / Cyan Glow)
  • A 15-bone humanoid skeleton (Hips → Spine → Head, shoulders, arms, legs)
  • Skin-weights so every vertex is bound to one bone  →  fully RIGGED GLB

Requirements:
    pip install pygltflib numpy

Usage:
    python generate_robot.py
"""

import os, math, struct
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
WHITE  = [0.960, 0.960, 0.960, 1.0]   # White Armor
GREY   = [0.176, 0.176, 0.188, 1.0]   # Dark Grey Metal
CYAN   = [0.000, 0.863, 1.000, 1.0]   # Cyan Glow

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
            c = i*lon+(j+1)%lon; d = b+(lon if(j+1)<lon else -lon*(lon-1))
            d = i*lon+(j+1)%lon+lon
            tris += [a,b,c, b,d,c]
    return (np.array(verts,dtype=np.float32),
            np.array(norms,dtype=np.float32),
            np.array(tris, dtype=np.uint16))

# ── GLB builder ───────────────────────────────────────────────────────────────

class Builder:
    def __init__(self):
        g = GLTF2()
        g.asset = Asset(version="2.0", generator="roba-tpose-gen")
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

    def mat(self, color):
        m = Material()
        m.pbrMetallicRoughness = pygltflib.PbrMetallicRoughness(
            baseColorFactor=color,
            metallicFactor =0.4 if color==GREY else 0.1,
            roughnessFactor=0.3 if color==GREY else 0.6)
        i = len(self.g.materials); self.g.materials.append(m); return i

    def mesh(self, pos, nor, idx, mat, ji=None, jw=None):
        bv_p = self._bv(pos.tobytes(), ARRAY_BUFFER)
        bv_n = self._bv(nor.tobytes(), ARRAY_BUFFER)
        bv_i = self._bv(idx.tobytes(), ELEMENT_ARRAY_BUFFER)
        ap = self._acc(bv_p,len(pos),FLOAT,VEC3, pos.min(0),pos.max(0))
        an = self._acc(bv_n,len(nor),FLOAT,VEC3)
        ai = self._acc(bv_i,len(idx),UNSIGNED_SHORT,SCALAR)
        attr = pygltflib.Attributes(POSITION=ap, NORMAL=an)
        if ji is not None:
            bv_ji=self._bv(ji.astype(np.uint8).tobytes(),ARRAY_BUFFER)
            bv_jw=self._bv(jw.astype(np.float32).tobytes(),ARRAY_BUFFER)
            attr.JOINTS_0  = self._acc(bv_ji,len(ji),UNSIGNED_BYTE,VEC4)
            attr.WEIGHTS_0 = self._acc(bv_jw,len(jw),FLOAT,VEC4)
        prim = Primitive(attributes=attr, indices=ai, material=mat, mode=4)
        i=len(self.g.meshes); self.g.meshes.append(Mesh(primitives=[prim])); return i

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

# ── Robot definition ──────────────────────────────────────────────────────────

def build(out_path):
    b = Builder()
    mW = b.mat(WHITE); mG = b.mat(GREY); mC = b.mat(CYAN)

    # ── Bone world positions (T-pose) ────────────────────────────────────────
    BW = [
        np.array([ 0.00, 0, 0.79 ]),   # 0  Hips
        np.array([ 0.00, 0, 0.925]),   # 1  Spine
        np.array([ 0.00, 0, 1.25 ]),   # 2  Chest
        np.array([ 0.00, 0, 1.54 ]),   # 3  Neck
        np.array([ 0.00, 0, 1.68 ]),   # 4  Head
        np.array([ 0.25, 0, 1.35 ]),   # 5  L_Shoulder
        np.array([ 0.58, 0, 1.35 ]),   # 6  L_Elbow
        np.array([ 0.85, 0, 1.35 ]),   # 7  L_Wrist
        np.array([-0.25, 0, 1.35 ]),   # 8  R_Shoulder
        np.array([-0.58, 0, 1.35 ]),   # 9  R_Elbow
        np.array([-0.85, 0, 1.35 ]),   # 10 R_Wrist
        np.array([ 0.12, 0, 0.70 ]),   # 11 L_Hip
        np.array([ 0.12, 0, 0.32 ]),   # 12 L_Knee
        np.array([-0.12, 0, 0.70 ]),   # 13 R_Hip
        np.array([-0.12, 0, 0.32 ]),   # 14 R_Knee
    ]
    NAMES  = ["Hips","Spine","Chest","Neck","Head",
               "L_Shoulder","L_Elbow","L_Wrist",
               "R_Shoulder","R_Elbow","R_Wrist",
               "L_Hip","L_Knee","R_Hip","R_Knee"]
    PARENT = [-1,0,1,2,3, 2,5,6, 2,8,9, 0,11, 0,13]

    # Build bone nodes
    bone_ni = []
    for i,name in enumerate(NAMES):
        p = PARENT[i]
        lt = (BW[i]-BW[p]).tolist() if p!=-1 else BW[i].tolist()
        bone_ni.append(b.node(name, t=lt))

    # Wire children
    for i,p in enumerate(PARENT):
        if p!=-1:
            pn=b.g.nodes[bone_ni[p]]
            if pn.children is None: pn.children=[]
            pn.children.append(bone_ni[i])

    # Inverse bind matrices
    ibms=[]
    for wp in BW:
        m=np.eye(4,dtype=np.float32); m[3,:3]=-wp; ibms.append(m)
    skin_i = b.skin("Humanoid", bone_ni, ibms)

    # ── Geometry parts: (shape_fn, offset_xyz, mat, bone_idx) ────────────────
    parts=[]

    def bx(w,h,d, tx,ty,tz, m, bi):
        p,n,i=_box(w,h,d)
        p+=np.array([tx,ty,tz],dtype=np.float32); parts.append((p,n,i,m,bi))
    def cy(r,h, tx,ty,tz, m, bi, ax='y'):
        p,n,i=_cylinder(r,h,axis=ax)
        p+=np.array([tx,ty,tz],dtype=np.float32); parts.append((p,n,i,m,bi))
    def sp(r, tx,ty,tz, m, bi):
        p,n,i=_sphere(r)
        p+=np.array([tx,ty,tz],dtype=np.float32); parts.append((p,n,i,m,bi))

    # Torso
    bx(0.40,0.25,0.50,  0.00, 0.00,1.25, mW, 2)   # Chest
    bx(0.18,0.03,0.18,  0.00,-0.13,1.25, mC, 2)   # Core (Cyan)
    cy(0.08,0.15,       0.00, 0.00,0.925,mG, 1)   # Spine joint
    bx(0.32,0.20,0.12,  0.00, 0.00,0.79, mW, 0)   # Pelvis

    # Head
    cy(0.05,0.08,       0.00, 0.00,1.54, mG, 3,'y')# Neck
    sp(0.15,            0.00, 0.00,1.68, mW, 4)    # Head sphere
    bx(0.20,0.05,0.06,  0.00,-0.13,1.70, mC, 4)   # Visor (Cyan)
    cy(0.02,0.05,       0.16, 0.00,1.68, mG, 4,'x')# L ear
    cy(0.02,0.05,      -0.16, 0.00,1.68, mG, 4,'x')# R ear

    # Left arm
    sp(0.06,            0.25, 0.00,1.35, mG, 5)
    cy(0.045,0.25,      0.425,0.00,1.35, mW, 5,'x')
    sp(0.05,            0.58, 0.00,1.35, mG, 6)
    cy(0.038,0.22,      0.72, 0.00,1.35, mW, 6,'x')
    bx(0.06,0.06,0.02,  0.85, 0.00,1.35, mG, 7)

    # Right arm
    sp(0.06,           -0.25, 0.00,1.35, mG, 8)
    cy(0.045,0.25,     -0.425,0.00,1.35, mW, 8,'x')
    sp(0.05,           -0.58, 0.00,1.35, mG, 9)
    cy(0.038,0.22,     -0.72, 0.00,1.35, mW, 9,'x')
    bx(0.06,0.06,0.02, -0.85, 0.00,1.35, mG,10)

    # Left leg
    sp(0.06,            0.12, 0.00,0.70, mG,11)
    cy(0.055,0.30,      0.12, 0.00,0.50, mW,11)
    sp(0.05,            0.12, 0.00,0.32, mG,12)
    cy(0.045,0.32,      0.12, 0.00,0.12, mW,12)
    bx(0.08,0.16,0.04,  0.12,-0.04,-0.06,mG,12)

    # Right leg
    sp(0.06,           -0.12, 0.00,0.70, mG,13)
    cy(0.055,0.30,     -0.12, 0.00,0.50, mW,13)
    sp(0.05,           -0.12, 0.00,0.32, mG,14)
    cy(0.045,0.32,     -0.12, 0.00,0.12, mW,14)
    bx(0.08,0.16,0.04, -0.12,-0.04,-0.06,mG,14)

    # ── Merge into one skinned mesh ───────────────────────────────────────────
    apos,anor,aidx,aji,ajw=[],[],[],[],[]
    off=0
    for pos,nor,idx,mat,bi in parts:
        n=len(pos)
        ji=np.zeros((n,4),dtype=np.uint8);  ji[:,0]=bi
        jw=np.zeros((n,4),dtype=np.float32);jw[:,0]=1.0
        apos.append(pos); anor.append(nor)
        aidx.append(idx+off); aji.append(ji); ajw.append(jw)
        off+=n

    mpos=np.concatenate(apos); mnor=np.concatenate(anor)
    midx=np.concatenate(aidx); mji =np.concatenate(aji)
    mjw =np.concatenate(ajw)

    mesh_i = b.mesh(mpos, mnor, midx, mW, mji, mjw)

    # ── Scene graph ───────────────────────────────────────────────────────────
    mesh_node = b.node("Robot_Mesh", mesh=mesh_i, skin=skin_i)
    root_node = b.node("Armature",
                       children=[bone_ni[0], mesh_node])
    b.g.scenes[0].nodes=[root_node]

    b.save(out_path)


if __name__=="__main__":
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "index.glb")
    print("Building rigged ROBA humanoid T-pose...")
    build(out)
