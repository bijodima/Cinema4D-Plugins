"""Pole Wire 0.3. Source geometry is never edited during evaluation."""
import math
import random
import c4d

def ud(i): return op[c4d.ID_USERDATA,i]
def vk(v): return (v.x,v.y,v.z)
def mk(m): return tuple(vk(v) for v in (m.off,m.v1,m.v2,m.v3))
def walk(n):
    yield n
    for child in n.GetChildren(): yield from walk(child)
def empty(message):
    n=c4d.BaseObject(c4d.Onull);n.SetName(message);return n
def horizontal(v):
    v=c4d.Vector(v.x,0,v.z)
    return v.GetNormalized() if v.GetLength()>1e-8 else c4d.Vector()

def bottom_center(pole):
    inv=~pole.GetMg();lo=[float('inf')]*3;hi=[-float('inf')]*3
    for n in walk(pole):
        if not isinstance(n,c4d.PointObject): continue
        matrix=inv*n.GetMg()
        for p in n.GetAllPoints():
            for i,x in enumerate(vk(matrix*p)):
                lo[i]=min(lo[i],x);hi[i]=max(hi[i],x)
    if not math.isfinite(lo[0]): return c4d.Vector()
    return c4d.Vector((lo[0]+hi[0])*.5,lo[1],(lo[2]+hi[2])*.5)

def prepare_ground(meshes):
    colliders=[];low=float('inf');high=-float('inf')
    for mesh in meshes:
        mg=mesh.GetMg()
        if min(mg.v1.GetLength(),mg.v2.GetLength(),mg.v3.GetLength())<1e-9:continue
        collider=c4d.utils.GeRayCollider()
        if not collider.Init(mesh):continue
        for p in mesh.GetAllPoints():
            y=(mg*p).y;low=min(low,y);high=max(high,y)
        colliders.append((collider,mg,~mg))
    return colliders,low,high

def ground_position(point,ground_data,offset):
    colliders,low,high=ground_data
    if not colliders or not math.isfinite(low):return point,False
    margin=max(1.,(high-low)*.01)
    start=c4d.Vector(point.x,high+margin,point.z);end=c4d.Vector(point.x,low-margin,point.z)
    best=None
    for collider,mg,inverse in colliders:
        a=inverse*start;b=inverse*end;ray=b-a;length=ray.GetLength()
        if length<1e-9:continue
        if collider.Intersect(a,ray/length,length):
            hit=collider.GetNearestIntersection()
            if hit:
                p=mg*hit['hitpos']
                if best is None or p.y>best.y:best=p
    return (c4d.Vector(point.x,best.y+offset,point.z),True) if best is not None else (point,False)

def variant_data(model,expected):
    bases=[n for n in model.GetChildren() if n.GetName()=='PW Base']
    groups=[n for n in model.GetChildren() if n.GetName()=='PW Connectors']
    if len(bases)!=1 or len(groups)!=1:raise ValueError('Prepare the variant rig first')
    source=model.GetMg();inverse=~source
    scale=c4d.Matrix()
    scale.v1=c4d.Vector(source.v1.GetLength(),0,0);scale.v2=c4d.Vector(0,source.v2.GetLength(),0);scale.v3=c4d.Vector(0,0,source.v3.GetLength())
    if min(scale.v1.x,scale.v2.y,scale.v3.z)<1e-9:raise ValueError('Variant scale is zero')
    offset=c4d.Matrix();offset.off=-(inverse*bases[0].GetMg().off)
    transform=scale*offset
    anchors=[transform*(inverse*n.GetMg().off) for n in groups[0].GetChildren() if n.GetType()==c4d.Onull]
    if len(anchors)!=expected:raise ValueError('All pole types must have the same connector count')
    return model,transform,anchors

def settings_key(group):
    if group is None:return None
    return tuple((n,n.GetDirty(c4d.DIRTYFLAGS_ALL),mk(n.GetMl()),tuple(n[d] for d,bc in n.GetUserDataContainer())) for n in walk(group))

def main():
    route,pole=ud(1),ud(2)
    if route is None or pole is None: return empty('Assign a route and pole model')
    if route==op or pole==op: return empty('Invalid link')
    for target in (route,pole):
        if any(n==op for n in walk(target)): return empty('Generator is inside an input object')
        parent=target.GetUp()
        while parent:
            if parent==op: return empty('Input object is inside the generator')
            parent=parent.GetUp()
    preview=bool(ud(28));wire_settings=ud(29);overrides=ud(30)
    wire_rows=wire_settings.GetChildren() if wire_settings else []
    override_rows={int(n[c4d.ID_USERDATA,1]):n for n in overrides.GetChildren() if len(n.GetUserDataContainer())>=3} if overrides else {}
    spacing=max(1.,float(ud(3)));height=float(ud(4));count=max(1,min(8,int(ud(5))))
    spread=max(0.,float(ud(6)));sag=max(0.,float(ud(7)));radius=max(.01,float(ud(8)))
    samples=max(4,min(64,int(ud(9))));end=bool(ud(10));yaw=float(ud(11))
    base,group=ud(12),ud(13);auto=bool(ud(14));bisect=bool(ud(15));corners=bool(ud(16));material=ud(17)
    ground=ud(18);ground_offset=float(ud(19));meshes=[];ground_key=None
    if ground is not None:
        if ground==op or any(n==op for n in walk(ground)) or any(n==ground for n in walk(op)):
            return empty('Ground must be outside the generator hierarchy')
        meshes=[n for n in walk(ground) if isinstance(n,c4d.PolygonObject) and n.GetPolygonCount()>0]
        if not meshes:return empty('Ground requires editable polygon meshes')
        ground_key=tuple((n,n.GetDirty(c4d.DIRTYFLAGS_DATA),mk(n.GetMg())) for n in meshes)
    pitch,bank,random_yaw,random_tilt=[math.radians(float(ud(i))) for i in range(23,27)];seed=int(ud(27))
    corner_model,end_model=ud(20),ud(21);corner_angle=max(1.,min(179.,float(ud(22))))
    variant_key=[]
    for model in (corner_model,end_model):
        if model is not None:
            if any(n==op for n in walk(model)) or any(n==model for n in walk(op)):return empty('Variant must be outside generator hierarchy')
            variant_key.append((model,model.GetHDirty(c4d.HDIRTYFLAGS_ALL),mk(model.GetMg()),tuple((n.GetName(),mk(n.GetMg())) for n in walk(model))))
        else:variant_key.append(None)
    for row in override_rows.values():
        model=row[c4d.ID_USERDATA,3]
        if model is not None:variant_key.append((model,model.GetHDirty(c4d.HDIRTYFLAGS_ALL),mk(model.GetMg())))
    source=pole.GetMg();scale=c4d.Matrix()
    scale.v1=c4d.Vector(source.v1.GetLength(),0,0)
    scale.v2=c4d.Vector(0,source.v2.GetLength(),0)
    scale.v3=c4d.Vector(0,0,source.v3.GetLength())
    if min(scale.v1.x,scale.v2.y,scale.v3.z)<1e-9: return empty('Model scale is zero')
    invsource=~source
    mounts=[invsource*n.GetMg().off for n in group.GetChildren() if n.GetType()==c4d.Onull] if group else []
    if group and not mounts: return empty('Add connector Nulls to the group')
    if len(mounts)>8: return empty('Maximum 8 connectors')
    basepoint=invsource*base.GetMg().off if base else None
    state=(route,route.GetDirty(c4d.DIRTYFLAGS_ALL),mk(route.GetMg()),pole,pole.GetHDirty(c4d.HDIRTYFLAGS_ALL),
           mk(scale),vk(basepoint) if basepoint is not None else None,tuple(vk(v) for v in mounts),
           preview,settings_key(wire_settings),settings_key(overrides),tuple(variant_key),corner_angle,pitch,bank,random_yaw,random_tilt,seed,spacing,height,count,spread,sag,radius,samples,end,yaw,auto,bisect,corners,material,ground_key,ground_offset,mk(op.GetMg()))
    if state==globals().get('_state') and op.GetCache() is not None: return op.GetCache()
    ground_data=prepare_ground(meshes) if ground is not None else None
    misses=0
    if basepoint is None: basepoint=bottom_center(pole) if auto else c4d.Vector()
    offset=c4d.Matrix();offset.off=-basepoint
    source_transform=scale*offset
    anchors=[source_transform*v for v in mounts] if group else [c4d.Vector((i-(count-1)*.5)*spread,height,0) for i in range(count)]
    standard=(pole,source_transform,anchors)
    try:
        corner_type=variant_data(corner_model,len(anchors)) if corner_model is not None else standard
        end_type=variant_data(end_model,len(anchors)) if end_model is not None else standard
    except ValueError as error:return empty(str(error))
    spline=route.GetRealSpline()
    if spline is None: return empty('A spline is required')
    helper=c4d.utils.SplineHelp()
    if not helper.InitSplineWith(route,c4d.SPLINEHELPFLAGS_GLOBALSPACE): return empty('Cannot read spline')
    root=empty('Poles and Wires');inverse=~op.GetMg();up=c4d.Vector(0,1,0);total=0;point_offset=0
    for segment in range(helper.GetSegmentCount()):
        length=helper.GetSegmentLength(segment)
        info=spline.GetSegment(segment) if spline.GetSegmentCount() else {'closed':bool(spline[c4d.SPLINEOBJECT_CLOSED]),'cnt':spline.GetPointCount()}
        segment_points=spline.GetAllPoints()[point_offset:point_offset+info['cnt']];point_offset+=info['cnt']
        if length<1e-6: continue
        closed=bool(info['closed'])
        if length/spacing>500: return empty('More than 500 poles: increase spacing')
        distances=[i*spacing for i in range(int(length//spacing)+1) if i*spacing<length-1e-6]
        if not closed and end: distances.append(length)
        # Exact vertices for linear splines, without approximating Bezier arc length.
        if corners and spline[c4d.SPLINEOBJECT_TYPE]==c4d.SPLINETYPE_LINEAR:
            vertices=[route.GetMg()*v for v in segment_points];along=0.
            for i,p in enumerate(vertices):
                if i: along+=(p-vertices[i-1]).GetLength()
                if (i==0 or i==len(vertices)-1) and not closed: continue
                a=horizontal(p-vertices[i-1]);b=horizontal(vertices[(i+1)%len(vertices)]-p)
                if a.GetLength()>0 and b.GetLength()>0 and a.Dot(b)<math.cos(math.radians(35)):
                    distances=[d for d in distances if abs(d-along)>max(.01,spacing*.1) or d==0 or (not closed and d==length)]
                    distances.append(along)
        ordered=[]
        for d in sorted(distances):
            if not ordered or d-ordered[-1]>.001: ordered.append(d)
        if closed and len(ordered)<2: continue
        if total+len(ordered)>500: return empty('More than 500 poles: increase spacing')
        positions=[helper.GetPosition(d/length,segment,True,True) for d in ordered];frames=[];pole_anchors=[]
        if ground_data is not None:
            grounded=[]
            for position in positions:
                point,hit=ground_position(position,ground_data,ground_offset)
                grounded.append(point)
                if not hit:misses+=1
            positions=grounded
        for i,point in enumerate(positions):
            forward=horizontal(helper.GetTangent(ordered[i]/length,segment,True,True))
            if bisect and len(positions)>1:
                incoming=horizontal(point-positions[i-1]) if i>0 or closed else c4d.Vector()
                outgoing=horizontal(positions[(i+1)%len(positions)]-point) if i+1<len(positions) or closed else c4d.Vector()
                blend=incoming+outgoing
                forward=blend.GetNormalized() if blend.GetLength()>1e-6 else outgoing
            if forward.GetLength()<1e-8: forward=c4d.Vector(0,0,1)
            rng=random.Random((seed*1000003+segment*9176+i*6361)&0xFFFFFFFF)
            angles=c4d.Vector(yaw+rng.uniform(-abs(random_yaw),abs(random_yaw)),pitch+rng.uniform(-abs(random_tilt),abs(random_tilt)),bank+rng.uniform(-abs(random_tilt),abs(random_tilt)))
            frame=c4d.Matrix(point,up.Cross(forward).GetNormalized(),up,forward)*c4d.utils.HPBToMatrix(angles)
            override=override_rows.get(total+1)
            if override is not None:frame=frame*override.GetMl()
            frames.append(frame)
            incoming=horizontal(point-positions[i-1]) if i>0 or closed else c4d.Vector()
            outgoing=horizontal(positions[(i+1)%len(positions)]-point) if i+1<len(positions) or closed else c4d.Vector()
            terminal=not closed and (i==0 or (end and i==len(positions)-1))
            turn=incoming.GetLength()>0 and outgoing.GetLength()>0 and incoming.Dot(outgoing)<math.cos(math.radians(corner_angle))
            chosen=end_type if terminal else (corner_type if turn else standard)
            if override is not None and override[c4d.ID_USERDATA,3] is not None:
                custom=override[c4d.ID_USERDATA,3]
                if any(n==op for n in walk(custom)) or any(n==custom for n in walk(op)):return empty('Override model must be outside the generator')
                try:chosen=variant_data(custom,len(anchors))
                except ValueError as error:return empty(str(error))
            chosen_model,chosen_transform,chosen_anchors=chosen
            pole_anchors.append(chosen_anchors)
            if override is not None and bool(override[c4d.ID_USERDATA,2]):total+=1;continue
            clone=chosen_model.GetClone(c4d.COPYFLAGS_NONE)
            if clone is None: continue
            clone.SetName('Pole %03d'%(total+1));clone.SetMl(inverse*frame*chosen_transform)
            clone[c4d.ID_BASEOBJECT_VISIBILITY_EDITOR]=c4d.MODE_UNDEF;clone[c4d.ID_BASEOBJECT_VISIBILITY_RENDER]=c4d.MODE_UNDEF
            clone.InsertUnderLast(root);total+=1
        pairs=list(zip(frames,frames[1:]))
        if closed: pairs.append((frames[-1],frames[0]))
        for wire in range(len(anchors)):
            row=wire_rows[wire] if wire<len(wire_rows) and len(wire_rows[wire].GetUserDataContainer())>=5 else None
            wire_sag,wire_radius,wire_material=sag,radius,material
            if row is not None:
                if not row[c4d.ID_USERDATA,1]:continue
                if row[c4d.ID_USERDATA,2]:
                    wire_sag=max(0.,float(row[c4d.ID_USERDATA,3]));wire_radius=max(.01,float(row[c4d.ID_USERDATA,4]))
                wire_material=row[c4d.ID_USERDATA,5] or material
            for span,(a,b) in enumerate(pairs):
                start=a*pole_anchors[span][wire];finish=b*pole_anchors[(span+1)%len(frames)][wire]
                if (finish-start).GetLength()<1e-6: continue
                drop=min(wire_sag,(finish-start).GetLength()*.25)
                points=[]
                for j in range(samples+1):
                    t=j/float(samples);points.append(inverse*(start*(1-t)+finish*t-up*(4*drop*t*(1-t))))
                path=c4d.SplineObject(len(points),c4d.SPLINETYPE_LINEAR);path.SetAllPoints(points);path.Message(c4d.MSG_UPDATE)
                if preview:
                    path.SetName('Preview Wire %d.%d - Span %d'%(segment+1,wire+1,span+1));path.InsertUnderLast(root);continue
                sweep=c4d.BaseObject(c4d.Osweep);sweep.SetName('Wire %d.%d - Span %d'%(segment+1,wire+1,span+1))
                if wire_material is not None:
                    tag=c4d.TextureTag();tag.SetMaterial(wire_material);tag[c4d.TEXTURETAG_PROJECTION]=c4d.TEXTURETAG_PROJECTION_UVW;sweep.InsertTag(tag)
                profile=c4d.BaseObject(c4d.Osplinecircle);profile[c4d.PRIM_CIRCLE_RADIUS]=wire_radius
                profile.InsertUnderLast(sweep);path.InsertUnderLast(sweep);sweep.InsertUnderLast(root)
    if misses:root.SetName('Poles and Wires - %d poles outside ground; route height used'%misses)
    globals()['_state']=state
    return root
