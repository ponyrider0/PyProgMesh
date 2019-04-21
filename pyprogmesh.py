
from pyffi.utils.mathutils import vecAdd
from pyffi.utils.mathutils import vecSub
from pyffi.utils.mathutils import vecscalarMul
from pyffi.utils.mathutils import vecDotProduct
from pyffi.utils.mathutils import vecCrossProduct
from pyffi.utils.mathutils import vecNormalized 
from pyffi.utils.mathutils import vecNorm 

from collections import defaultdict
import time

class Triangle:
    v1 = 0
    v2 = 0
    v3 = 0
    def __init__(self, _verts):
        self.v1 = _verts[0]
        self.v2 = _verts[1]
        self.v3 = _verts[2]

def SortByCost(u, v):
    return (u.Cost > v.Cost)

class DXVertex:
    Position = [0.0, 0.0, 0.0]
    Normal = [0.0, 0.0, 0.0]
    Diffuse = [0, 0, 0, 0]
    texCoord = [0.0, 0.0]
    def __init__(self, position=None, normal=None, vc=None, uv=None):
        if position is not None:
            self.Position = position
        if normal is not None:
            self.Normal = normal
        if vc is not None:
            self.Diffuse = vc
        if uv is not None:
            self.texCoord = uv

##########################################################
#
# CollapseVertex
#
##########################################################
class CollapseVertex:
    Neighbors = list()
    Faces = list()
    Vert = DXVertex()
    ID = 0
    Cost = 0.0
    Candidate = None
    Duplicate = 0
    use_cost = False
    parent = None
    n_costs = defaultdict(list)
    border = False
    def __init__(self, _parent, _ID, _use_cost=False):
        self.parent = _parent
        self.ID = _ID
        self.use_cost = _use_cost
        self.Vert = _parent.GetVert(self.ID)
        self.Cost = -1.0
        self.Candidate = None
        self.Duplicate = False
        self.border = False
        return
    def IsNeighbor(self, v):
        if v in self.Neighbors:
            return True
        return False
    def AddNeighbor(self, v):
#        print "DEBUG: AddNeighbor()..."
        if (not self.IsNeighbor(v)) and (v is not self):
            self.Neighbors.append(v)
            if self.use_cost:
                c = self.ComputeCost(v)
                self.AddCost(c, v)
            return True
        return False
    def RemoveNeighbor(self, v):
        if self.IsNeighbor(v):
            self.Neighbors.remove(v)
            if self.use_cost:
                self.RemoveCost(v)
            return True
        return False
    def RemoveIfNotNeighbor(self, v):
        if not self.IsInFaces(v):
            return self.RemoveNeighbor(v)
        return False
    def IsFace(self, f):
        if f in self.Faces:
            return True
        return False
    def IsInFaces(self, v):
        for f in self.Faces:
            if f.HasVertex(v):
                return True
        return False
    def AddFace(self, f):
#        print "DEBUG: AddFace()..."
        if not self.IsFace(f):
            self.Faces.append(f)
            for v in f.vertex:
                if v == self:
                    continue
                self.AddNeighbor(v)
        return
    def RemoveFace(self, f):
        if self.IsFace(f):
            self.Faces.remove(f)
            for v in f.vertex:
                if v == self:
                    self.RemoveIfNotNeighbor(v)
        return
    def IsBorder(self):
        return self.border
    def LockBorder(self):
        self.border = (len(self.Faces) < len(self.Neighbors))
        return
    def AddCost(self, c, v):
        self.n_costs[c].append(v)
        if (c < self.Cost) or (self.Candidate is None):
            self.Cost = c
#            print "DEBUG: assigning self.Candidate"
            self.Candidate = v
        return
    def RemoveCost(self, v):
        for c, verts in self.n_costs.items():
            if v in verts:
                verts.remove(v)
                if (len(verts) == 0):
                    del self.n_costs[c]
                break
        if self.Candidate == v:
            if len(self.n_costs) == 0:
                self.Cost = -1.0
                self.Candidate = None
            else:
                if len(verts) > 0:
                    self.Cost = c
                    self.Candidate = verts[0]
                else:
                    self.Cost, verts = self.n_costs.items()[0]
                    self.Candidate = verts[0]
        return
    def GetCost(self, v):
        if not self.use_cost:
            return -1.0
        for c, verts in self.n_costs.items():
            if v in verts:
                return c
        return -1.0
    def IsSameUV(self, v):
        return (self.Vert.texCoord == v.Vert.texCoord)
    def __eq__(self, v):
        return (self.ID == v.ID and self.parent == v.parent)
    def __lt__(self, v):
        return (self.Cost > v.Cost)
    def ComputeCost(self, v):
        edgelength = 1.0
        if self.parent.Arguments.useedgelength:
            length = vecSub(v.Vert.Position, self.Vert.Position)
            edgelength = vecNorm(length)
        if (len(self.Neighbors) == len(v.Neighbors)):
            same_neighbors = True
            for neighbor in self.Neighbors:
                if neighbor == v:
                    continue
                if not v.IsNeighbor(neighbor):
                    same_neighbors = False
                    break
            if same_neighbors:
                raw_input("ERROR: ComputeCost() same neighbors detected.")
                return 999999.9
        curvature = 0.001
        sides = list()
        for f in self.Faces:
            if v.IsFace(f):
                sides.append(f)
        if self.parent.Arguments.usecurvature:
            for f in self.Faces:
                mincurv = 1.0
                for s in sides:
                    dotproduct = vecDotProduct(f.normal, s.normal)
                    mincurv = min([mincurv, (1.002 - dotproduct)/2.0])
                curvature = max([curvature, mincurv])
        if self.IsBorder:
            WEIGHT_BORDER = 100
            curvature = curvature * WEIGHT_BORDER
        if self.parent.Arguments.protecttexture:
            if not self.IsSameUV(v):
                curvature = 1
        if self.parent.Arguments.lockborder and self.IsBorder():
            curvature = 999999.9
        return edgelength * curvature
    def ComputeNormal(self):
        if len(self.Faces) == 0:
            return
        Face_Normal = [0.0, 0.0, 0.0]
        for f in self.Faces:
            Face_Normal = vecAdd(Face_Normal, f.normal)
        self.Vert.Normal = vecNormalized(Face_Normal)
        return

##########################################################
#
# CollapseTriangle
#
##########################################################
class CollapseTriangle:
    vertex = None
    normal = [0.0, 0.0, 0.0]
    def __init__(self, v1, v2, v3):
#        del self.vertex[:]
        self.vertex = [v1, v2, v3]
#        self.vertex.append(v1)
#        self.vertex.append(v2)
#        self.vertex.append(v3)
        for v_self in self.vertex:
            v_self.AddFace(self)
        self.ComputeNormal()
        return
    def HasVertex(self, vert):
        if vert in self.vertex:
            return self.vertex.index(vert)
        else:
            return False
    def ReplaceVertex(self, u, v):
        u.RemoveFace(self)
        self.vertex[self.HasVertex(u)] = v
        v.AddFace(self)
        for v_self in self.vertex:
            if v_self == v:
                continue
            v_self.RemoveIfNotNeighbor(u)
            v_self.AddNeighbor(v)
        self.ComputeNormal()
        return
    def ComputeNormal(self):
#        v = [[], [], []]
        v0 = self.vertex[0].Vert.Position
        v1 = self.vertex[1].Vert.Position
        v2 = self.vertex[2].Vert.Position
#        v.append(self.vertex[0].Vert.Position)
#        v.append(self.vertex[1].Vert.Position)
#        v.append(self.vertex[2].Vert.Position)
#        a = vecSub(v[1], v[0])
#        b = vecSub(v[2], v[0])
        a = vecSub(v1, v0)
        b = vecSub(v2, v0)
        _normal = self.normal
        self.normal = vecCrossProduct(a,b)
        if vecNorm(self.normal) < 0.001:
            return
        self.normal = vecNormalized(self.normal)
        length = vecDotProduct(self.normal, _normal)
        if length < 0:
            self.normal = vecscalarMul(self.normal, -1)
        return


class PMarg:
    useedgelength = False
    usedcurvature = False
    protecttexture = False
    protectvc = False
    lockborder = False
    keepborder = False
    removeduplicate = True

##########################################################
#
# ProgMesh
#
##########################################################
class ProgMesh:
    Arguments = PMarg()
    vertices = list()
    triangles = list()
    CollapseOrder = list()
    CollapseMap = dict()
    VertexCount = 0
    TriangleCount = 0
    Faces = list()
    Verts = list()
    def __init__(self, vertCount, faceCount, verts, faces):
        t = time.time()
        self.VertexCount = vertCount
        self.TriangleCount = faceCount
        print "DEBUG: ProgMesh.init(): vertCount=%d, faceCount=%d, num verts=%d, num faces=%d" % (vertCount, faceCount, len(verts), len(faces))
        del self.Verts[:]
        for i in range(0, vertCount):
            v = verts[i]
            self.Verts.append(DXVertex(v))
#            print "DEBUG: Vert: (%f, %f, %f)" % (v[0], v[1], v[2])
        del self.Faces[:]
        for i in range(0, faceCount):
            f = faces[i]
            self.Faces.append(Triangle(f))
#            print "DEBUG: Face: [%d, %d, %d]" % (f[0], f[1], f[2])
        print "PROFILING: completed in %f sec" % (time.time() - t)
        return
    def HasVertex(self, v):
        if v in self.vertices:
            return True
        return False
    def RemoveVertex(self, v):
        if self.HasVertex(v):
#            print "DEBUG: RemoveVertex(): %s" % (str(v.Vert.Position))
            self.vertices.remove(v)
            del v
        return
    def HasTriangle(self, t):
        if t in self.triangles:
            return True
        return False
    def RemoveTriangle(self, t):
        if self.HasTriangle(t):
            print "DEBUG: RemoveTriangle() called"
            self.triangles.remove(t)
            del t
        return
    def GetFace(self, index):
        return self.Faces[index]
    def GetVert(self, index):
        return self.Verts[index]
    def GetVertexCount(self):
        return self.VertexCount
    def GetTriangleCount(self):
        return self.TriangleCount
    def CheckDuplicate(self, v):
        for u in self.vertices:
            if u.Vert.Position == v.Vert.Position:
                if u.Vert.Normal != v.Vert.Normal:
                    continue
                if self.Arguments.protecttexture and not u.IsSameUV(v):
                    continue
                if (self.Arguments.protectvc and u.Vert.Diffuse == v.Vert.Diffuse):
                    continue
                del v
                u.Duplicate = u.Duplicate+1
                return u
        return v
    def ComputeEdgeCostAtVertex(self, v):
        if len(v.Neighbors) == 0:
            v.Candidate = None
            v.Cost = -0.01
            return
        print "DEBUG: ComputeEdgeCostAtVertex: v.Neighbors #=%d, self.vertices #=%d" % (len(v.Neighbors), len(self.vertices))
        if len(v.Neighbors) >= (len(self.vertices)-1):
            print "ERROR: vertex at [%d] is connected to all vertices" % (self.vertices.index(v))
            raw_input("Press ENTER to continue")
            return
        for neighbor in v.Neighbors:
            cost = v.ComputeCost(neighbor)
            v.AddCost(cost, neighbor)
        return
    def ComputeAllEdgeCollapseCosts(self):
        t1 = time.time()
        print "DEBUG: ComputeAllEdgeCollapseCosts():"
        for vert in self.vertices:
            self.ComputeEdgeCostAtVertex(vert)
        self.vertices.sort(SortByCost)
        print "PROFILING: completed in %f sec" % (time.time()-t1)
        return
    def Collapse(self, u, v, recompute=True):
        if v is None:
            print "DEBUG: Collapse(): u.Faces #=%d, v is None" % (len(u.Faces))
            self.RemoveVertex(u)
            return
        print "DEBUG: Collapse(): u.Faces #=%d, v is not None" % (len(u.Faces))
        sides = list()
        for f in u.Faces:
            if f.HasVertex(v):
                print "DEBUG: Collapse(): adding f to sides"
                sides.append(f)
        for s in sides:
            print "DEBUG: Collapse(): removing s in sides"
            self.RemoveTriangle(s)
        for f in u.Faces:
            u.Faces[-1].ReplaceVertex(u, v)
        self.RemoveVertex(u)
        self.vertices.sort(SortByCost)
        return
    def ComputeProgressiveMesh(self):
        t1 = time.time()
        print "DEBUG: ComputeProgressiveMesh()"
        del self.vertices[:]
        t2 = time.time()
        print "DEBUG: Generating self.vertices (CollapseVertex data), VertexCount=%d" % (self.VertexCount)
        for i in range(0, self.VertexCount):
            v = CollapseVertex(self, i)
            if self.Arguments.removeduplicate:
                v = self.CheckDuplicate(v)
            self.vertices.append(v)
        print "PROFILING: Generated self.vertices, completed in %f sec" % (time.time()-t2)
        # integrity check
        print "INTEGRITY CHECK: self.vertices #=%d" % (len(self.vertices))
        for vert in self.vertices:
            if vert.ID > len(self.vertices):
                print "ERROR FOUND: vert.ID = %d at index=%d" % (vert.ID, self.vertices.index(vert))
        del self.triangles[:]
        t2 = time.time()
        print "DEBUG: Generating self.triangles (CollapseTriangle data), TriangleCount=%d" % (self.TriangleCount)
        for i in range(0, self.TriangleCount):
            t = CollapseTriangle(self.vertices[self.Faces[i].v1], self.vertices[self.Faces[i].v2], self.vertices[self.Faces[i].v3])
            self.triangles.append(t)
        print "PROFILING: Generated self.triangles, completed in %f sec" % (time.time()-t2)
        t2 = time.time()
        print "DEBUG: Re-index self.vertices... #=%d" % (len(self.vertices))
        i = 0
        j = 0
        while i < len(self.vertices):
            vert = self.vertices[i]
#            print "DEBUG: ComputeProgressiveMesh(): vert.ID = %d, i = %d " % (i, j)
            vert.ID = i
            vert.LockBorder()
            vert.use_cost = True
            if vert.Duplicate:
                vert.Duplicate = vert.Duplicate-1
                del self.vertices[i]
                i = i-1
            i = i+1
            j = j+1
        print "PROFILING: Re-index self.vertices, completed in %f sec" % (time.time()-t2)
        # integrity check
        print "INTEGRITY CHECK: self.vertices #=%d" % (len(self.vertices))
        for vert in self.vertices:
            if vert.ID > len(self.vertices):
                print "ERROR FOUND: vert.ID = %d at index=%d" % (vert.ID, self.vertices.index(vert))
        print "DEBUG: vert.ID (max) = %d" % (i-1)
        self.ComputeAllEdgeCollapseCosts()
#        self.CollapseOrder.clear()
        del self.CollapseOrder[:]
        t2 = time.time()
        print "DEBUG: Generating self.CollapseOrder"
        for i in range(0, len(self.vertices)):
            self.CollapseOrder.append(0)
        self.CollapseMap.clear()
        while len(self.vertices) is not 0:
            mn = self.vertices[len(self.vertices)-1]
            cv = mn.Candidate
            # integrity check
            if mn.ID > len(self.vertices):
                print "ERROR FOUND: mn.ID = %d at index=%d, self.vertices #=%d" % (mn.ID, self.vertices.index(mn), len(self.vertices))
#            print "DEBUG: ComputeProgressiveMesh(): mn.ID = %d, i = %d" % (mn.ID, len(self.vertices)-1)
            self.CollapseOrder[len(self.vertices)-1] = mn.ID
            if cv is not None:
                self.CollapseMap[mn.ID] = cv.ID
            else:
                self.CollapseMap[mn.ID] = -1
            self.Collapse(mn, cv)
        print "PROFIING: Generated self.CollapseOrder, completed in %f sec" % (time.time()-t2)
        t2 = time.time()
        print "PROFILING: ComputeProgressiveMesh(): completed in %f sec" % (t2-t1)
        return
    def DoProgressiveMesh(self, ratio):
        t1 = time.time()
        print "DEBUG: DoProgressiveMesh(): ratio=%f" % (ratio)
        target = self.VertexCount * ratio
        CollapseList = list()
        new_Faces = list()
        new_Verts = list()
        del self.vertices[:]
        for i in range(0, self.VertexCount):
            v = CollapseVertex(self, i)
            if self.Arguments.removeduplicate:
                v = self.CheckDuplicate(v)
            self.vertices.append(v)
        del self.triangles[:]
        for i in range(0, self.TriangleCount):
            t_ = self.Faces[i]
            t = CollapseTriangle(self.vertices[t_.v1], self.vertices[t_.v2], self.vertices[t_.v3])
            self.triangles.append(t)
        i = 0
        j = 0
        while i < len(self.vertices):
            vert = self.vertices[i]
#            print "DEBUG: DoProgressiveMesh(): vert.ID = %d, i = %d " % (i, j)
            vert.ID = i
            vert.LockBorder()
            if vert.Duplicate:
                vert.Duplicate = vert.Duplicate-1
                del self.vertices[i]
                i = i-1
            i = i+1
            j = j+1
        print "DEBUG: DoProgressiveMesh() vert.ID (max) i = %d" % (i-1)
        for i in range(0, len(self.vertices)):
            mn = self.vertices[i]
#            print "DEBUG: mn.ID = %d, from self.vertices[%d]" % (mn.ID, i)
            if self.CollapseMap[mn.ID] == -1:
                cv = None
            else:
                cv = self.vertices[self.CollapseMap[mn.ID]]
            mn.Candidate = cv
#            print "DEBUG: DoProgressiveMesh(): self.vertices #=%d, self.CollapseOrder #=%d, i=%d" % (len(self.vertices), len(self.CollapseOrder), i)
#            print "DEBUG: DoProgressiveMesh(): self.CollapseOrder[%d] #=%d" % (i, self.CollapseOrder[i])
            CollapseList.append(self.vertices[ self.CollapseOrder[i] ])
        while len(CollapseList) > target:
            mn = CollapseList[-1]
            if mn.IsBorder:
                break
            if mn.Cost > 999999.0:
                break
            Collapse(mn, mn.Candidate, false)
            CollapseList.pop()
        i = 0
        for v in self.vertices:
            v.ID = i
            v.ComputeNormal()
            new_Verts.append(v.Vert)
            i = i+1
        for t in self.triangles:
            face = list()
            face.append(t.vertex[0].ID)
            face.append(t.vertex[1].ID)
            face.append(t.vertex[2].ID)
            new_Faces.append(face)
        result = len(new_Verts)

        t2 = time.time()
        print "PROFILING: DoProgressiveMesh(): completed in %f sec" % (t2-t1)
        if result == 0:
            print "No new_Verts"
            return 0

        if len(new_Faces) == 0:
            print "No new_Faces"
            return 0

        if len(new_Verts) == self.VertexCount:
            print "new_Verts is unchanged"
            return 0

        newFaceCount = len(new_Faces)
        newVertCount = len(new_Verts)

#        print "Results: new verts = %d, old verts = %d, new faces = %d" % (newVertCount, self.VertexCount, newFaceCount)
                        
        return (newVertCount, new_Verts, newFaceCount, new_Faces)
        

def main():
    # cube: 6 points, 6 quads, 12 triangles
    _verts = [ [0,0,0], [1,0,0], [1,1,0], [0,1,0], [0,0,1], [1,0,1], [1,1,1], [0,1,1] ]
    _faces = [ [0,1,2], [0,2,3], [0,1,5], [0,5,4], [4,5,6], [4,6,7], [1,2,6], [1,6,5], [0,3,7], [0,7,4], [2,3,7], [2,7,6] ]
    p = ProgMesh(vertCount=len(_verts), faceCount=len(_faces), verts=_verts, faces=_faces)
    p.ComputeProgressiveMesh()
    print p.DoProgressiveMesh(0.5)

if __name__ == '__main__':
    main()


