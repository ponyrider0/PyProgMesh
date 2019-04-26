
from pyffi.utils.mathutils import vecAdd
from pyffi.utils.mathutils import vecSub
from pyffi.utils.mathutils import vecscalarMul
from pyffi.utils.mathutils import vecDotProduct
from pyffi.utils.mathutils import vecCrossProduct
from pyffi.utils.mathutils import vecNormalized 
from pyffi.utils.mathutils import vecNorm 

from collections import defaultdict
import time
import math

class ProgMeshSettings:
    def __init__(self):
        self.UseEdgelength = True
        self.UseCurvature = True
        self.ProtectTexture = False
        self.ProtectColor = False
        self.KeepBorder = False
        self.RemoveDuplicate = True
        self.ReconstructVert = True

class RawTriangle:
##    v1 = None
##    v2 = None
##    v3 = None
    def __init__(self, _verts):
        self.v1 = _verts[0]
        self.v2 = _verts[1]
        self.v3 = _verts[2]

class RawVertex:
##    Position = None
##    Normal = None
##    RGBA = None
##    UV = None
    def __init__(self, Position=None, Normal=None, RGBA=None, UV=None):
        self.Position = [0.0, 0.0, 0.0]
        self.Normal = [0.0, 0.0, 0.0]
        self.RGBA = [0, 0, 0, 0]
        self.UV = [0.0, 0.0]
        if Position is not None:
            self.Position = Position
        if Normal is not None:
            self.Normal = Normal
        if RGBA is not None:
            self.RGBA = RGBA
        if UV is not None:
            self.UV = UV

def SortByBorderAndCost(u, v):
    if u.IsBorder() and not v.IsBorder():
        return -1
    if not u.IsBorder() and v.IsBorder():
        return 1
    if u.Cost < v.Cost:
        return -1
    elif u.Cost == v.Cost:
        return 0
    else:
        return 1

def SortByCost(u, v):
    print "DEBUG: SortByCost()"
    if u.Cost > v.Cost:
        return -1
    elif u.Cost == v.Cost:
        return 0
    else:
        return 1

##########################################################
#
# CollapseVertex
#
##########################################################
class CollapseVertex:
##    Neighbors = None
##    Faces = None
##    Vert = None
##    ID = None
##    Cost = None
##    Candidate = None
##    Duplicate = None
##    use_cost = False
##    parent = None
##    n_costs = None
##    border = False
    def __init__(self, _parent, _ID, _use_cost=False):
        self.deleted = False
        self.parent = _parent
        self.ID = _ID
        self.use_cost = _use_cost
        self.Vert = _parent.GetRawVert(self.ID)
        self.Cost = -1.0
        self.Candidate = None
        self.Duplicate = False
        self.border = False
        self.Neighbors = list()
        self.Faces = list()
        self.n_costs = defaultdict(list)
        return
    def RemoveSelf(self):
        self.deleted = True
#        print "DEBUG: deleting CollapseVertex v.ID[%d]" % (self.ID)
        if len(self.Faces) != 0:
            s = ""
            for f in self.Faces:
                s = s + ("f[%d %d %d]" % (f.vertex[0].ID, f.vertex[1].ID, f.vertex[2].ID)) + " "
            print "ASSERTION FAILURE: vertex[ID=%d] deleted without removal of all faces (#%d): %s" % (self.ID, len(self.Faces), s)
#            raw_input("PRESS ENTER TO CONTINUE.\n")
##        for n in self.Neighbors:
##            n.RemoveNeighbor(self)
##            self.Neighbors.remove(n)
        while len(self.Neighbors) > 0:
            n = self.Neighbors[-1]
            n.RemoveNeighbor(self)
            self.Neighbors.pop()
    def IsNeighbor(self, v):
        if v in self.Neighbors:
            return True
        return False
    def AddNeighbor(self, v):
#        print "  DEBUG: AddNeighbor() called on v.ID = [%d]:" % (v.ID)
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
#        print "  DEBUG: CollapseVertex.AddFace(f) called by v.ID[%d]:" % (self.ID)
        if not self.IsFace(f):
#            print "  DEBUG: f is not in v.ID[%d]'s Faces list (#%d), adding..." % (self.ID, len(self.Faces))
            self.Faces.append(f)
#            print "  DEBUG: adding f's vertices as neighbors (#%d)..." % (len(f.vertex))
            for v in f.vertex:
                if v == self:
#                    print "  DEBUG: f.vertex[%d] is this vertex, skipping" % (f.vertex.index(v))
                    continue
#                print "  DEBUG: f.vertex[%d] -- adding as neighbor..." % (f.vertex.index(v))
                self.AddNeighbor(v)
#        else:
#            print "  DEBUG: f is already in v.ID[%d]'s Faces list (#%d), skipping." % (self.ID, len(self.Faces))
        return
    def RemoveFace(self, f):
        if f.HasVertex(self) == False:
            print "ASSERTION FAILURE: v[%d].RemoveFace() face [%d %d %d] does not contain this vertex" % (self.ID, f.vertex[0], f.vertex[1], f.vertex[2])
#            raw_input("PRESS ENTER TO CONTINUE.\n")
        if self.IsFace(f):
            self.Faces.remove(f)
            for v in f.vertex:
                if v == self:
                    continue
                self.RemoveIfNotNeighbor(v)
        return
    def IsBorder(self):
        return self.border
    def LockBorder(self):
        # for each neighbor vertex, see if neighbor shares exactly one face with self
        self.border = False
        for n in self.Neighbors:
            num_shared_faces = 0
            for f in n.Faces:
                if f in self.Faces:
                    num_shared_faces = num_shared_faces + 1
                    if num_shared_faces > 1:
                        break
            if num_shared_faces == 1:
                self.border = True
                break
#        # original algorithm
#        self.border = (len(self.Faces) < len(self.Neighbors))
##        if self.border:
##            print "  DEBUG: Border Locked(), v.ID[%d]" % (self.ID)
##        else:
##            print "  DEBUG: Border UNLocked, v.ID[%d]" % (self.ID)            
        return
    def AddCost(self, c, v):
        self.n_costs[c].append(v)
        if (c < self.Cost) or (self.Candidate is None):
            self.Cost = c
#            print "DEBUG: assigning self.Candidate"
            self.Candidate = self.n_costs[c][-1]
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
                # select new Candidate with lowest cost
                if len(verts) > 0:
                    self.Cost = c
                    self.Candidate = verts[-1]
                else:
                    lowest_cost = None
                    for c in self.n_costs.keys():
                        if lowest_cost is None:
                            lowest_cost = c
                        if c < lowest_cost:
                            lowest_cost = c
                    self.Cost = lowest_cost
                    self.Candidate = self.n_costs[lowest_cost][-1]
        return
    def GetCost(self, v):
        if not self.use_cost:
            return -1.0
        for c, verts in self.n_costs.items():
            if v in verts:
                return c
        return -1.0
    def IsSameUV(self, v):
        return (self.Vert.UV == v.Vert.UV)
    def __eq__(self, v):
        return (self.ID == v.ID and self.parent == v.parent)
    def __lt__(self, v):
        return (self.Cost > v.Cost)
    def ComputeCost(self, v):
        edgelength = 1.0
        if self.parent.Settings.UseEdgelength:
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
#                raw_input("ERROR: ComputeCost() same neighbors detected.")
                return 999999.9
        curvature = 0.001
        sides = list()
        for f in self.Faces:
            if v.IsFace(f):
                sides.append(f)
        if self.parent.Settings.UseCurvature:
            for f in self.Faces:
                mincurv = 1.0
                for s in sides:
                    dotproduct = vecDotProduct(f.normal, s.normal)
                    mincurv = min([mincurv, (1.002 - dotproduct)/2.0])
                curvature = max([curvature, mincurv])
        if self.IsBorder():
            WEIGHT_BORDER = 100
            curvature = curvature * WEIGHT_BORDER
        if self.parent.Settings.ProtectTexture:
            if not self.IsSameUV(v):
                WEIGHT_UV = 1.5
                curvature = curvature * WEIGHT_UV
        if self.parent.Settings.KeepBorder and self.IsBorder():
#            raw_input("KEEP BORDER activated, Press ENTER to Continue.")
            curvature = 999999.9
        cost = edgelength * curvature
#        print "DEBUG: ComputeCost() v[%d] to v[%d], c=%f" % (self.ID, v.ID, cost)
        return cost
    def ComputeNormal(self):
        if len(self.Faces) == 0:
            return
        Face_Normal = [0.0, 0.0, 0.0]
        for f in self.Faces:
            Face_Normal = vecAdd(Face_Normal, f.normal)
        # Integrity Check
        self.Vert.Normal = Face_Normal
        if vecNorm(self.Vert.Normal) < 0.001:
            return
        self.Vert.Normal = vecNormalized(self.Vert.Normal)
        return

##########################################################
#
# CollapseTriangle
#
##########################################################
class CollapseTriangle:
##    vertex = None
##    normal = None
##    deleted = None
    def __init__(self, v1, v2, v3):
        self.deleted = False
        self.normal = [0.0, 0.0, 0.0]
        self.vertex = [v1, v2, v3]
        for v_self in self.vertex:
#            print "v[%d], v.ID=[%d]: AddFace()..." % (self.vertex.index(v_self), v_self.ID)
            v_self.AddFace(self)
        self.ComputeNormal()
        self.UV_list = [v1.Vert.UV, v2.Vert.UV, v3.Vert.UV]
        self.Normal_list = [v1.Vert.Normal, v2.Vert.Normal, v3.Vert.Normal]
        self.RGBA_list = [v1.Vert.RGBA, v2.Vert.RGBA, v3.Vert.RGBA]
        return
    def RemoveSelf(self):
        self.deleted = True
#        print "DEBUG: deleting CollapseTriangle [%d %d %d]" % (self.vertex[0].ID, self.vertex[1].ID, self.vertex[2].ID)
        for v in self.vertex:
            if v is None:
                continue
            v.RemoveFace(self)
    def HasVertex(self, vert):
        if vert in self.vertex:
            return self.vertex.index(vert)+1
        else:
            return False
    def ReplaceVertex(self, u, v):
#        print "  DEBUG: ReplaceVertex(%d with %d) for Triangle [%d %d %d]" % (u.ID, v.ID, self.vertex[0].ID, self.vertex[1].ID, self.vertex[2].ID)
        u.RemoveFace(self)
#        print "    INSPECTION: Triangle currently [%d %d %d]" % (self.vertex[0].ID, self.vertex[1].ID, self.vertex[2].ID)
        self.vertex[self.HasVertex(u)-1] = v
#        print "    INSPECTION: Triangle now [%d %d %d]" % (self.vertex[0].ID, self.vertex[1].ID, self.vertex[2].ID)
        v.AddFace(self)
        for v_self in self.vertex:
            if v_self == v:
                continue
            if v_self.IsNeighbor(u) == False:
                print "ASSERTION FAILURE: ReplaceVertex(%d to %d): v_self.ID[%d] is not Neighbor to u.ID[%d]" % (u.ID, v.ID, v_self.ID, u.ID)
#                raw_input("PRESS ENTER TO CONTINUE.\n")
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


##########################################################
#
# ProgMesh
#
##########################################################
class ProgMesh:
##    Settings = ProgMeshSettings()
##    vertices = list()
##    triangles = list()
##    CollapseOrder = list()
##    CollapseMap = dict()
##    RawVertexCount = 0
##    RawTriangleCount = 0
##    RawTriangles = list()
##    RawVerts = list()
    def __init__(self, vertCount, faceCount, verts, faces, settings=None):
        if isinstance(settings, ProgMeshSettings):
            self.Settings = settings
        else:
            self.Settings = ProgMeshSettings()
        self.StartTime = time.time()
        self.vertices = list()
        self.triangles = list()
        self.CollapseOrder = list()
        self.CollapseMap = dict()
        self.RawTriangles = list()
        self.RawVerts = list()
#        t = time.time()
        self.RawVertexCount = vertCount
        self.RawTriangleCount = faceCount
        self.ReconstructionEstimate = 0
#        print "DEBUG: ProgMesh.init(): vertCount=%d, faceCount=%d, num verts=%d, num faces=%d" % (vertCount, faceCount, len(verts), len(faces))
        del self.RawVerts[:]
        if isinstance(verts[0], RawVertex):
            for i in range(0, vertCount):
                self.RawVerts.append(verts[i])
        else:
            for i in range(0, vertCount):
                v = verts[i]
                self.RawVerts.append(RawVertex(v))
#            print "DEBUG: Vert: (%f, %f, %f)" % (v[0], v[1], v[2])
        del self.RawTriangles[:]
        for i in range(0, faceCount):
            f = faces[i]
            self.RawTriangles.append(RawTriangle(f))
#            print "DEBUG: Face: [%d, %d, %d]" % (f[0], f[1], f[2])
#        print "PROFILING: completed in %f sec" % (time.time() - t)
        return
    def UVCloseEnough(self, a, b, ratio=0.5):
        threshold = 0.75 - (0.5 * ratio)
        # 1. vecSub(a,b), 2. vecNorm < threshold
        difference = vecSub(a, b)
        distance = vecNorm(difference)
        if distance < (1.412135*threshold):
            return True
        return False
    def HasVertex(self, v):
        if v.deleted:
            return False
        if v in self.vertices:
            return True
        return False
############################################
# RemoveVertex() optimized to avoid calling self.vertices.remove()
#   Only use in final stages aka Collapse(), after vertex/triangle generation
#   self.vertices can not be accessed by index after calling this, must
#   iterate through and skip elements with .deleted == True
############################################
    def RemoveVertex(self, v):
        if self.HasVertex(v):
#            print "  DEBUG: RemoveVertex(): ID=%d" % (v.ID)
#            self.vertices.remove(v)
            v.RemoveSelf()
            del v
        return
    def HasTriangle(self, t):
        if t.deleted:
            return False
        if t in self.triangles:
            return True
        return False
############################################
# RemoveTriangle() optimized to avoid calling self.triangles.remove()
#   Only use in final stages aka Collapse(), after vertex/triangle generation
#   self.triangles can not be accessed by index after calling this, must
#   iterate through and skip elements with .deleted == True
############################################
    def RemoveTriangle(self, t):
        if self.HasTriangle(t):
#            print "  DEBUG: RemoveTriangle(): [%d %d %d]" % (t.vertex[0].ID, t.vertex[1].ID, t.vertex[2].ID)
#            self.triangles.remove(t)
            t.RemoveSelf()
            del t
        return
    def GetRawTriangle(self, index):
        return self.RawTriangles[index]
    def GetRawVert(self, index):
        return self.RawVerts[index]
    def GetRawVertexCount(self):
        return self.VertexCount
    def GetRawTriangleCount(self):
        return self.TriangleCount
    def CheckDuplicate(self, v):
        for u in self.vertices:
            if u.Vert.Position == v.Vert.Position:
##                if u.Vert.Normal != v.Vert.Normal:
##                    self.ReconstructionEstimate = self.ReconstructionEstimate +1
##                    continue
                if self.Settings.ProtectTexture and not u.IsSameUV(v):
                    self.ReconstructionEstimate = self.ReconstructionEstimate +1
##                    continue
                if self.Settings.ProtectColor and u.Vert.RGBA != v.Vert.RGBA:
                    self.ReconstructionEstimate = self.ReconstructionEstimate +1
##                    continue
                del v
                u.Duplicate = u.Duplicate+1
                return u
        return v
    def ComputeEdgeCostAtVertex(self, v):
        if len(v.Neighbors) == 0:
            v.Candidate = None
            v.Cost = -0.01
            return
#        print "DEBUG: ComputeEdgeCostAtVertex: v.Neighbors #=%d, self.vertices #=%d" % (len(v.Neighbors), len(self.vertices))
##        if len(v.Neighbors) >= (len(self.vertices)-1):
##            print "ERROR: vertex at [%d] is connected to all vertices" % (self.vertices.index(v))
##            raw_input("Press ENTER to continue")
##            return
        for neighbor in v.Neighbors:
            cost = v.ComputeCost(neighbor)
            v.AddCost(cost, neighbor)
        return
    def ComputeAllEdgeCollapseCosts(self):
#        t1 = time.time()
#        print "DEBUG: ComputeAllEdgeCollapseCosts(): ..."
        for vert in self.vertices:
            if vert.deleted:
                continue
            self.ComputeEdgeCostAtVertex(vert)
#            print "DEBUG: v[%d], Candidate=[%d], Cost=%f" % (vert.ID, vert.Candidate.ID, vert.Cost)
        self.vertices.sort(key=lambda vert: vert.Cost, reverse=True)
#        self.vertices.sort(cmp=SortByCost)        
#        print "PROFILING: completed in %f sec" % (time.time()-t1)
        return
    def Collapse(self, u, v, recompute=True):
        if v is None:
#            print "DEBUG: Collapse(): u.Faces #=%d, v is None" % (len(u.Faces))
            self.RemoveVertex(u)
            return

        delete_list = list()
        replace_list = list()
        for f in u.Faces:
            if f.HasVertex(v):
                delete_list.append(f)
            else:
                replace_list.append(f)

        for f in delete_list:
#            print "  DEBUG: Collapse(%d to %d): removing triangle [%d %d %d]" % (u.ID, v.ID, f.vertex[0].ID, f.vertex[1].ID, f.vertex[2].ID)
            self.RemoveTriangle(f)

        for f in replace_list:
#            print "  DEBUG: f[%d][%d %d %d] replacing vertex u[%d] with v[%d]" % (u.Faces.index(f), f.vertex[0].ID, f.vertex[1].ID, f.vertex[2].ID, u.ID, v.ID)
            f.ReplaceVertex(u, v)

        self.RemoveVertex(u)

        if recompute:
            self.vertices.sort(key=lambda vert: vert.Cost, reverse=True)
#        self.vertices.sort(cmp=SortByCost)
        return
    def ComputeProgressiveMesh(self):
        t1 = time.time()
        del self.vertices[:]
#        t2 = time.time()
#        print "DEBUG: ComputeProgressiveMesh(): RawVertexCount=%d" % (self.RawVertexCount)
        for i in range(0, self.RawVertexCount):
            v = CollapseVertex(self, i)
            if self.Settings.RemoveDuplicate:
                v = self.CheckDuplicate(v)
            self.vertices.append(v)
#        print "PROFILING: Generated self.vertices, completed in %f sec" % (time.time()-t2)
        del self.triangles[:]
#        t2 = time.time()
#        print "DEBUG: Generating self.triangles (CollapseTriangle data), TriangleCount=%d" % (self.TriangleCount)
        for i in range(0, self.RawTriangleCount):
            t = CollapseTriangle(self.vertices[self.RawTriangles[i].v1], self.vertices[self.RawTriangles[i].v2], self.vertices[self.RawTriangles[i].v3])
            self.triangles.append(t)
#        print "PROFILING: Generated self.triangles, completed in %f sec" % (time.time()-t2)
#        t2 = time.time()
#        print "DEBUG: Re-index self.vertices... #=%d" % (len(self.vertices))
        i = 0
        j = 0
        while i < len(self.vertices):
            vert = self.vertices[i]
#            print "DEBUG: ComputeProgressiveMesh(): vert.ID = %d, i = %d " % (i, j)
            vert.ID = i
            vert.LockBorder()
            vert.use_cost = True
            if vert.Duplicate > 0:
                vert.Duplicate = vert.Duplicate-1
                del self.vertices[i]
                i = i-1
            i = i+1
            j = j+1
#        print "PROFILING: Re-index self.vertices, completed in %f sec" % (time.time()-t2)
#        print "DEBUG: vert.ID (max) = %d" % (i-1)
        self.ComputeAllEdgeCollapseCosts()
#        self.CollapseOrder.clear()
        del self.CollapseOrder[:]
        t2 = time.time()
        print "DEBUG: Generating self.CollapseOrder ..."
        for i in range(0, len(self.vertices)):
            self.CollapseOrder.append([0,0])
        costMap = list()
        for i in range(0, len(self.vertices)):
            v = self.vertices[i]
            costMap.append(v.Cost)
        self.CollapseMap.clear()
        while len(self.vertices) is not 0:
            mn = self.vertices[-1]
            if mn.deleted:
                self.vertices.pop()
                continue
            cv = mn.Candidate
#            print "DEBUG: ComputeProgressiveMesh(): mn.ID = %d, i = %d" % (mn.ID, len(self.vertices)-1)
            self.CollapseOrder[len(self.vertices)-1] = [mn.ID, costMap[len(self.vertices)-1] ]
            if cv is not None:
                self.CollapseMap[mn.ID] = cv.ID
            else:
                self.CollapseMap[mn.ID] = -1
            self.Collapse(mn, cv)
#        s = ''
##        for co in self.CollapseOrder:
##            s = s + ("v[%d](c=%f) " % (co[0], co[1]))
##        print "CollapseOrder (#%d): %s" % (len(self.CollapseOrder), s)
        print "PROFIING: Generated self.CollapseOrder, completed in %f sec" % (time.time()-t2)
#        t2 = time.time()
        print "PROFILING: ComputeProgressiveMesh(): completed in %f sec" % (time.time()-t1)
        return
    def DoProgressiveMesh(self, ratio):
#        t1 = time.time()
        Goal_CollapseCount = self.RawVertexCount * (1.0 - ratio)
#        print "DEBUG: DoProgressiveMesh(): ratio=%f, target=%f" % (ratio, target)
        CollapseList = list()
        new_Faces = list()
        new_Verts = list()
        del self.vertices[:]
        self.ReconstructionEstimate = 0
        for i in range(0, self.RawVertexCount):
            v = CollapseVertex(self, i)
            if self.Settings.RemoveDuplicate:
                v = self.CheckDuplicate(v)
            self.vertices.append(v)
        del self.triangles[:]
        for i in range(0, self.RawTriangleCount):
            t_ = self.RawTriangles[i]
            t = CollapseTriangle(self.vertices[t_.v1], self.vertices[t_.v2], self.vertices[t_.v3])
            # store original UV/Normal/RGBA
            RawCornerID = [self.RawTriangles[i].v1, self.RawTriangles[i].v2, self.RawTriangles[i].v3]
            for j in range(0, 3):
                t.UV_list[j] = self.RawVerts[RawCornerID[j]].UV
                t.Normal_list[j] = self.RawVerts[RawCornerID[j]].Normal
                t.RGBA_list[j] = self.RawVerts[RawCornerID[j]].RGBA
            self.triangles.append(t)
        i = 0
        j = 0
        DuplicatesRemoved = 0
        while i < len(self.vertices):
            vert = self.vertices[i]
#            print "DEBUG: DoProgressiveMesh(): vert.ID = %d, i = %d " % (i, j)
            vert.ID = i
#            vert.LockBorder()
            if vert.Duplicate:
                vert.Duplicate = vert.Duplicate-1
                DuplicatesRemoved = DuplicatesRemoved+1
                del self.vertices[i]
                i = i-1
            i = i+1
            j = j+1
#        print "DEBUG: DoProgressiveMesh() vert.ID (max) i = %d" % (i-1)
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
            CollapseList.append(self.vertices[ self.CollapseOrder[i][0] ])
            self.vertices[ self.CollapseOrder[i][0] ].Cost = self.CollapseOrder[i][1]
##        s = ""
##        for co in CollapseList:
##            s = s + " " + str( co.ID )              
##        print "DEBUG: CollapseList (#%d): %s" % (len(CollapseList), s)
        t2 = time.time()
        percent_removed = (DuplicatesRemoved*1.0)/(self.RawVertexCount*1.0)
        if (percent_removed) > 0.10 :
#            print "Recalculating goal"
            Goal_CollapseCount = len(self.vertices) * (1-ratio)
        CollapseCount = 0
        while len(CollapseList) > 5 and CollapseCount < Goal_CollapseCount:
            mn = CollapseList[-1]
##            if self.Settings.KeepBorder and mn.IsBorder():
##                print "  Stopping: v.ID[%d] is border." % (mn.ID)
##                break
            if mn.Cost > 999999.0:
                print "  Stopping: v.ID[%d] cost > 999999.0" % (mn.ID)
                break
#            print "  Collapsing vertices: ID: %d to %d, cost=%f..." % (mn.ID, mn.Candidate.ID, mn.Cost)
            CollapseCount = CollapseCount+1
            self.Collapse(mn, mn.Candidate, False)
            CollapseList.pop()
#        print "  Completed. [%d] vertices collapsed, [%d] duplicates removed, [%d] estimated to be reconstructed." % (CollapseCount, DuplicatesRemoved, self.ReconstructionEstimate)
        print "PROFILING: Collapsed CollapseList by (#%d), completed in %f sec" % (CollapseCount, time.time() - t2)

##        print "INSPECTION: self.vertices #=%d, self.triangles #=%d" % (len(self.vertices), len(self.triangles))
##        s = ""
##        for v in self.vertices:
##            s = s + str(v.ID) + " "
##        print "vertices: %s" % (s)
##        s = ""
##        for t in self.triangles:
##            s = s + "[" + str(t.vertex[0].ID) + " " + str(t.vertex[1].ID) + " " + str(t.vertex[2].ID) + "] "
##        print "triangles: %s" % (s)        

        if not self.Settings.ReconstructVert:
            i = 0
            for v in self.vertices:
                if v.deleted:
                    continue
                v.ID = i
    #            v.ComputeNormal()
                new_Verts.append(v.Vert)
                i = i+1
            print "DEBUG: current new_Verts (#%d)" % (len(new_Verts))

        reconstructed_verts = 0
        reuse_count = 0
        existing_used = 0
        print "DEBUG: triangles: #%d" % (len(self.triangles))
        for t in self.triangles:
            if t.deleted:
                continue
            face = list()
            if not self.Settings.ReconstructVert:
                face.append(t.vertex[0].ID)
                face.append(t.vertex[1].ID)
                face.append(t.vertex[2].ID)
            else:
                # Reconstruct merged vertices with different UV/Normal
                # 1. Check if Corner matchces Vertex
                for i in range(0,3):
                    # retrieve existing vert
                    working_v = t.vertex[i].Vert                
                    reconstruct_point = False
                    if self.Settings.ProtectTexture and not self.UVCloseEnough(t.vertex[i].Vert.UV, t.UV_list[i], ratio):
    #                    print "UV difference unacceptable... reconstructing"
                        reconstruct_point = True
                    if self.Settings.ProtectColor and t.vertex[i].Vert.RGBA != t.RGBA_list[i]:
    #                    print "RGB difference unacceptable... reconstructing"
                        reconstruct_point = True
                    if reconstruct_point:
                        # 2. make new vert
                        working_v = RawVertex(Position=t.vertex[i].Vert.Position, Normal=t.vertex[i].Vert.Normal, RGBA=t.RGBA_list[i], UV=t.UV_list[i])
                    # look up vert and add index
                    working_ID = -1
                    for existing_v in new_Verts:
                        if working_v.Position == existing_v.Position and self.UVCloseEnough(working_v.UV, existing_v.UV, ratio) and working_v.RGBA == existing_v.RGBA:
                            working_ID = new_Verts.index(existing_v)
                            if reconstruct_point:
                                reuse_count = reuse_count +1
                            else:
                                existing_used = existing_used + 1
    #                       print "Re-using reconstructed vert [%d]" % (new_ID)
                            break
                    if working_ID == -1:
                        working_ID = len(new_Verts)
                        if reconstruct_point:
                            reconstructed_verts = reconstructed_verts + 1
    #                   print "Adding reconstructed vert [%d]" % (new_ID)
                        new_Verts.append(working_v)
                    face.append(working_ID)
            new_Faces.append(face)

#        print "DEBUG: %d Vertices reconstructed, %d reconstructed reused, %d existing reused" % (reconstructed_verts, reuse_count, existing_used)
        result = len(new_Verts)

#        t2 = time.time()
        print " Block decimation completed: [%d] original vertices: [%d] collapsed, [%d] duplicates removed, [%d] reconstructed. Processing time: %.2f sec" % \
              (self.RawVertexCount, CollapseCount, DuplicatesRemoved, reconstructed_verts, time.time() - self.StartTime)
        if result == 0:
            print "No new_Verts"
            return 0

        if len(new_Faces) == 0:
            print "No new_Faces"
            return 0

        if len(new_Verts) == self.RawVertexCount:
            print "new_Verts is unchanged"
            return 0

        newFaceCount = len(new_Faces)
        newVertCount = len(new_Verts)

#        print "Results: new verts = %d, old verts = %d, new faces = %d" % (newVertCount, self.VertexCount, newFaceCount)
                        
        return (newVertCount, new_Verts, newFaceCount, new_Faces)
        

def main():
    # cube: 6 points, 6 quads, 12 triangles
    _verts = [ [0.0,0.0,0.0], [1.0,0.0,0.0], [1.0,1.0,0.0], [0.0,1.0,0.0], [0.0,0.0,1.0], [1.0,0.0,1.0], [1.0,1.0,1.0], [0.0,1.0,1.0] ]
    _faces = [ [0,1,2], [0,2,3], [0,1,5], [0,5,4], [4,5,6], [4,6,7], [1,2,6], [1,6,5], [0,3,7], [0,7,4], [2,3,7], [2,7,6] ]

    
    
    p = ProgMesh(vertCount=len(_verts), faceCount=len(_faces), verts=_verts, faces=_faces)

    print "\n=========================================="
    print "ComputeProgressiveMesh()"
    print "=========================================="    
    p.ComputeProgressiveMesh()
    # Inspection, Integrity Checks
    print "INSPECTION:\n  ComputeProgressiveMesh() num verts = %d, num triangles = %d" % ( len(p.vertices), len(p.triangles) )
##    for f in p.triangles:
##        v1, v2, v3 = f.vertex
##        print "  Triangle [%d]: [ %d, %d, %d ] " % ( p.triangles.index(f), v1.ID, v2.ID, v3.ID )
##        for v in f.vertex:
##            s = ""
##            for n in v.Neighbors:
##                s = s + " " + str(n.ID)
##            print "    v[%d].Neighbors (#%d): %s " % (f.vertex.index(v), len(n.Neighbors), s)

    print "\n=========================================="
    print "DoProgressiveMesh()"
    print "=========================================="
    result = p.DoProgressiveMesh(0.7)
    if result == 0:
        print "no decimation"
    else:
        numVerts, verts, numFaces, faces = result
        # Inspection, Integrity Checks
        print "INSPECTION:\n  DoProgressiveMesh() p.vertices = %d, p.triangles = %d" % ( len(p.vertices), len(p.triangles) )
        for f in p.triangles:
            v1, v2, v3 = f.vertex
            print "  Triangle [%d]: [ %d, %d, %d ] " % ( p.triangles.index(f), v1.ID, v2.ID, v3.ID )
            for v in f.vertex:
                s = ""
                for n in v.Neighbors:
                    s = s + " " + str(n.ID)
                print "    v[%d], v.ID[%d].Neighbors (#%d): %s " % (f.vertex.index(v), v.ID, len(v.Neighbors), s)
        print "RESULTS: vertices = %d, faces = %d " % (numVerts, numFaces)
        s = ""
        for v1 in verts:
            v = v1.Position
            s = s + "[" + str(v[0]) + ", " + str(v[1]) + ", " + str(v[2]) + "] "
        print "verts: %s" % (s)
        s = ""
        for f in faces:
            s = s + "[" + str(f[0]) + " " + str(f[1]) + " " + str(f[2]) + "] "
        print "faces: %s" % (s)


if __name__ == '__main__':
    main()


