
import os
import sys
import pyprogmesh
import pyffi.formats.nif
from pyffi.formats.nif import NifFormat


def PMBlock(block):
    print "========================NEW BLOCK========================="
    verts = list()
    faces = list()
    PMSettings = pyprogmesh.ProgMeshSettings()
    if block.has_uv:
        PMSettings.ProtectTexture = True
    if block.has_vertex_colors:
        PMSettings.ProtectColor = True
##    if block.num_vertices > block.num_triangles:
###        raw_input("Border condition decteted.  Enabling option. Press ENTER to continue...")
##        PMSettings.KeepBorder = True

    for i in range(0, len(block.vertices)):
        _v = block.vertices[i]
#        print "vertex: (%f, %f, %f)" % (_v.x, _v.y, _v.z)
        v = [_v.x, _v.y, _v.z]
        if block.has_uv:
            _uv = [block.uv_sets[0][i].u, block.uv_sets[0][i].v]
        else:
            _uv = None
        if block.has_normals:
            _normal = [block.normals[i].x, block.normals[i].y, block.normals[i].z]
        else:
            _normal = None
        if block.has_vertex_colors:
            _vc = [block.vertex_colors[i].r, block.vertex_colors[i].g, block.vertex_colors[i].b, block.vertex_colors[i].a]
        else:
            _vc = None
        verts.append(pyprogmesh.RawVertex(Position=v, UV=_uv, Normal=_normal, RGBA=_vc))
    for i in range(0, len(block.triangles)):
        _t = block.triangles[i]
#        print "triangle: [%d, %d, %d]" % (_t.v_1, _t.v_2, _t.v_3)
        f = [_t.v_1, _t.v_2, _t.v_3]
        faces.append(f)
    print "PREP: old verts = %d, old faces = %d" % (len(verts), len(faces))
    pm = pyprogmesh.ProgMesh(len(verts), len(faces), verts, faces, PMSettings)
#    raw_input("Press ENTER to compute progressive mesh.")
    pm.ComputeProgressiveMesh()
#    raw_input("Press ENTER to perform decimation.")    
    result = pm.DoProgressiveMesh(0.5)
    if result == 0:
        return
    else:
        numVerts, verts, numFaces, faces = result[0], result[1], result[2], result[3]
        print "RESULTS: new verts = %d, new faces = %d" % (numVerts, numFaces)
        block.num_vertices = numVerts
        block.vertices.update_size()
        if block.has_uv or block.num_uv_sets > 0:
            block.uv_sets.update_size()
        if block.has_normals:
            block.normals.update_size()
        if block.has_vertex_colors:
            block.vertex_colors.update_size()
        for i in range(0, numVerts):
            rawVert = verts[i]
            v = block.vertices[i]
            v.x = rawVert.Position[0]
            v.y = rawVert.Position[1]
            v.z = rawVert.Position[2]
            if block.has_uv:
                uv = block.uv_sets[0][i]
                uv.u = rawVert.UV[0]
                uv.v = rawVert.UV[1]
            if block.has_normals:
                normals = block.normals[i]
                normals.x = rawVert.Normal[0]
                normals.y = rawVert.Normal[1]
                normals.z = rawVert.Normal[2]
            if block.has_vertex_colors:
                vc = block.vertex_colors[i]
                vc.r = rawVert.RGBA[0]
                vc.g = rawVert.RGBA[1]
                vc.b = rawVert.RGBA[2]
                vc.a = rawVert.RGBA[3]
        block.num_triangles = numFaces
        block.triangles.update_size()
        for i in range(0, numFaces):
            triangle = faces[i]
            t = block.triangles[i]
            t.v_1 = triangle[0]
            t.v_2 = triangle[1]
            t.v_3 = triangle[2]

##        i = 0
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


input_filename = 'meshes/floraUbcUtreeU01.nif'
#input_filename = 'meshes/cessna.nif'
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

output_filename = input_filename.lower().replace(".nif", "_reduced.nif")
ostream = open(output_filename, 'wb')
x.write(ostream)
ostream.close()

