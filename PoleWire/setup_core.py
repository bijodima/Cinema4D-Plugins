"""Run in Cinema 4D Script Manager. Compatible with Pole Wire Generator 0.3."""
import c4d
from pathlib import Path

def walk(node):
    yield node
    for child in node.GetChildren():
        yield from walk(child)

def bounds(model):
    matrix=model.GetMg()
    if min(matrix.v1.GetLength(),matrix.v2.GetLength(),matrix.v3.GetLength())<1e-9:
        raise ValueError('The model has a zero scale.')
    inverse=~matrix;points=[]
    for node in walk(model):
        if isinstance(node,c4d.PolygonObject):
            transform=inverse*node.GetMg()
            points.extend(transform*p for p in node.GetAllPoints())
    if not points:
        raise ValueError('Select an editable polygon model or a group containing polygon meshes.')
    low=min(p.y for p in points);high=max(p.y for p in points)
    bottom=[p for p in points if p.y<=low+max((high-low)*.005,1e-6)]
    base=c4d.Vector((min(p.x for p in bottom)+max(p.x for p in bottom))*.5,low,
                    (min(p.z for p in bottom)+max(p.z for p in bottom))*.5)
    return base,high,min(p.x for p in points),max(p.x for p in points)

def create_rig(doc,model,count,own_undo=True):
    if model is None or model.GetDocument()!=doc:
        raise ValueError('Select a model in the current document.')
    if not 1<=count<=8:
        raise ValueError('Connector count must be between 1 and 8.')
    if any(n.GetName() in ('PW Base','PW Connectors') for n in model.GetChildren()):
        raise ValueError('This model already has a PW rig. Edit its Nulls instead of creating duplicates.')
    origin,top,left,right=bounds(model)
    base=c4d.BaseObject(c4d.Onull);base.SetName('PW Base');base.SetRelPos(origin)
    group=c4d.BaseObject(c4d.Onull);group.SetName('PW Connectors')
    for i in range(count):
        connector=c4d.BaseObject(c4d.Onull);connector.SetName('Connector %02d'%(i+1))
        x=origin.x if count==1 else left+(right-left)*(i+.5)/count
        connector.SetRelPos(c4d.Vector(x,origin.y+(top-origin.y)*.9,origin.z))
        connector.InsertUnderLast(group)
    if own_undo:doc.StartUndo()
    try:
        base.InsertUnderLast(model);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,base)
        group.InsertUnderLast(model);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,group)
    finally:
        if own_undo:doc.EndUndo()
    c4d.EventAdd()
    return base,group

def create_setup(doc,model,count,route=None):
    if model is None or model.GetDocument()!=doc:
        raise ValueError('Select the full pole model first.')
    for root in doc.GetObjects():
        for node in walk(root):
            if node.GetType()==c4d.Opython and 'source_transform' in (node[c4d.OPYTHON_CODE] or '') and node[c4d.ID_USERDATA,2]==model:
                return node,False
    origin,top,left,right=bounds(model)
    bases=[n for n in model.GetChildren() if n.GetName()=='PW Base']
    groups=[n for n in model.GetChildren() if n.GetName()=='PW Connectors']
    reuse=bool(bases or groups)
    if reuse and (len(bases)!=1 or len(groups)!=1):
        raise ValueError('Expected one PW Base and one PW Connectors group. Resolve duplicate or incomplete rigs first.')
    if reuse and not 1<=len([n for n in groups[0].GetChildren() if n.GetType()==c4d.Onull])<=8:
        raise ValueError('The existing connector group must contain 1-8 direct Null children.')
    if route is not None and (route.GetDocument()!=doc or route.GetRealSpline() is None):
        raise ValueError('The route must be a spline in the current document.')
    folder=Path(__file__).parent;ns={'__name__':'pw_builder'}
    exec(compile((folder/'generator_builder.py').read_text(encoding='utf-8'),str(folder/'generator_builder.py'),'exec'),ns)
    gen=ns['build']((folder/'generator_code.py').read_text(encoding='utf-8'),route,model)
    height=max(1.,(top-origin.y)*model.GetMg().v2.GetLength())
    gen[c4d.ID_USERDATA,3]=height*1.5;gen[c4d.ID_USERDATA,7]=height*.07
    gen[c4d.ID_USERDATA,8]=max(.01,height*.003)
    newroute=route is None
    if newroute:
        start=model.GetMg()*origin+c4d.Vector(height,0,0)
        route=c4d.SplineObject(2,c4d.SPLINETYPE_LINEAR);route.SetName('PW Route')
        route.SetAllPoints([start,start+c4d.Vector(0,0,height*3)])
        route.Message(c4d.MSG_UPDATE);gen[c4d.ID_USERDATA,1]=route
    doc.StartUndo()
    try:
        base,group=(bases[0],groups[0]) if reuse else create_rig(doc,model,count,False)
        gen[c4d.ID_USERDATA,12]=base;gen[c4d.ID_USERDATA,13]=group
        if newroute:doc.InsertObject(route);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,route)
        doc.InsertObject(gen);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,gen)
    finally:doc.EndUndo()
    c4d.EventAdd()
    return gen,True

class SetupDialog(c4d.gui.GeDialog):
    def __init__(self):
        self.model=None
    def CreateLayout(self):
        self.SetTitle('Pole Wire Setup 0.3.2')
        self.GroupBegin(100,c4d.BFH_SCALEFIT,1,0)
        self.GroupBorderSpace(12,12,12,12)
        self.AddStaticText(101,c4d.BFH_SCALEFIT,name='Model: not selected')
        self.AddButton(102,c4d.BFH_SCALEFIT,initw=0,inith=0,name='Use Selected Model')
        self.AddStaticText(103,c4d.BFH_LEFT,name='Wire connectors (1-8)')
        self.AddEditNumberArrows(104,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.AddButton(105,c4d.BFH_SCALEFIT,initw=0,inith=0,name='Create Rig + Generator')
        self.AddStaticText(106,c4d.BFH_SCALEFIT,name='Move the connector Nulls onto the insulators after creation.')
        self.AddStaticText(107,c4d.BFH_SCALEFIT,name='')
        self.GroupEnd()
        return True
    def InitValues(self):
        self.SetInt32(104,3,min=1,max=8)
        self.use_selected()
        return True
    def use_selected(self):
        doc=c4d.documents.GetActiveDocument();model=doc.GetActiveObject()
        if model is not None and model.GetType()==c4d.Opython:
            if 'source_transform' in (model[c4d.OPYTHON_CODE] or ''):
                model=model[c4d.ID_USERDATA,2]
        if model is not None and (model.GetName().startswith('Connector ') or model.GetName() in ('PW Base','PW Connectors')):
            while model.GetUp() is not None and (model.GetName().startswith('Connector ') or model.GetName() in ('PW Base','PW Connectors')):
                model=model.GetUp()
        self.model=model
        self.SetString(101,'Model: '+(model.GetName() if model is not None else 'not selected'))
        self.SetString(107,'Select the full model root, not an individual insulator.')
    def Command(self,ident,msg):
        if ident==102:self.use_selected()
        elif ident==105:
            try:
                doc=c4d.documents.GetActiveDocument()
                routes=[n for n in doc.GetActiveObjects(0) if n.GetRealSpline() is not None]
                if not routes:routes=[n for root in doc.GetObjects() for n in walk(root) if n.GetRealSpline() is not None]
                if len(routes)>1:raise ValueError('Several splines found. Select one route, then click Create.')
                gen,created=create_setup(doc,self.model,self.GetInt32(104),routes[0] if routes else None)
                self.SetString(107,'Generator created and linked. Existing connector positions kept.' if created else 'This model already has a generator; no duplicate created.')
            except (ValueError,RuntimeError,ReferenceError) as exc:
                self.SetString(107,str(exc))
        return True

def main():
    # Keep an asynchronous dialog alive after Script Manager execution returns.
    import sys,types
    session=sys.modules.setdefault('_pole_wire_setup_session',types.ModuleType('_pole_wire_setup_session'))
    old=getattr(session,'dialog',None)
    if old is not None:old.Close()
    session.dialog=SetupDialog()
    session.dialog.Open(c4d.DLG_TYPE_ASYNC,defaultw=520,defaulth=220)

if __name__=='__main__':main()
