
import os
import sys
import pyprogmesh
import pyffi.formats.nif
from pyffi.formats.nif import NifFormat


def PMBlock(block):
    print "========================NEW BLOCK========================="
    verts = list()
    faces = list()
    PMargs = pyprogmesh.PMarg()
    for i in range(0, len(block.vertices)):
        _v = block.vertices[i]
        if block.has_uv:
            _uv = block.uv[i]
            PMargs.protecttexture = True
        else:
            _uv = [0.0, 0.0]
#        print "vertex: (%f, %f, %f)" % (_v.x, _v.y, _v.z)
        v = [_v.x, _v.y, _v.z]
        verts.append(pyprogmesh.DXVertex(v, uv=_uv))
    for _t in block.triangles:
#        print "triangle: [%d, %d, %d]" % (_t.v_1, _t.v_2, _t.v_3)
        f = [_t.v_1, _t.v_2, _t.v_3]
        faces.append(f)
    print "PREP: old verts = %d, old faces = %d" % (len(verts), len(faces))
    pm = pyprogmesh.ProgMesh(len(verts), len(faces), verts, faces)
    pm.arguments = PMargs
#    raw_input("Press ENTER to compute progressive mesh.")
    pm.ComputeProgressiveMesh()
#    raw_input("Press ENTER to perform decimation.")    
    result = pm.DoProgressiveMesh(0.75)
    if result == 0:
        return
    else:
        print "RESULTS: new verts = %d, new faces = %d" % (result[0], result[2])
        i = 0
##        for r in result[1]:
##            print "New Triangle[%d]: (%f, %f, %f)" % (i, r.Position[0], r.Position[1], r.Position[2])
##            i = i + 1
##            if i > 5:
##                break
##        i = 0
##        for f in result[3]:
##            print "New Face[%d]: [%d, %d, %d]" % (i, f[0], f[1], f[2])
##            i = i + 1
##            if i > 5:
##                break


input_filename = 'c:/dev/ESPNIFTest/meshes/floraUbcUtreeU01.nif'
fstream = open(input_filename, 'rb')
x = NifFormat.Data()
x.read(fstream)
fstream.close()

for root in x.roots:
    for block in root.tree():
        if isinstance(block, NifFormat.NiTriShapeData):
            if block.has_vertices and block.has_triangles:
                if block.num_vertices < 10000:
                    PMBlock(block)
                

