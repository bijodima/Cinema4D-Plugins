from pathlib import Path
import math
import c4d

FOLDER=Path(__file__).parent
GENERATOR_CODE=(FOLDER/'generator_code.py').read_text(encoding='utf-8')
GENERATOR_HELPERS={};exec(GENERATOR_CODE,GENERATOR_HELPERS)
library={'__name__':'pw_library'}
exec(compile((FOLDER/'preset_library.py').read_text(encoding='utf-8'),str(FOLDER/'preset_library.py'),'exec'),library)
core={'__name__':'pw_core','__file__':str(FOLDER/'setup_core.py')}
exec(compile((FOLDER/'setup_core.py').read_text(encoding='utf-8'),str(FOLDER/'setup_core.py'),'exec'),core)

def is_generator(node):
    return node is not None and node.GetType()==c4d.Opython and 'source_transform' in (node[c4d.OPYTHON_CODE] or '')

def validate_route(route,model,gen=None):
    if route is None or route.GetRealSpline() is None:raise ValueError('Assign a route spline or click Create Straight Route.')
    if route.GetDocument()!=model.GetDocument():raise ValueError('Route and model must be in the same document.')
    if route in list(core['walk'](model)):raise ValueError('The route must be outside the pole model.')
    if gen is not None and (route in list(core['walk'](gen)) or gen in list(core['walk'](route))):
        raise ValueError('The generator and route must not contain each other.')

def apply_settings(doc,gen,model,route,spacing,sag,radius,samples,rotation,end,align,corners,material,own_undo=True,ground=None,ground_offset=0.,corner_model=None,end_model=None,corner_angle=35.,pitch=0.,bank=0.,random_yaw=0.,random_tilt=0.,seed=1,preview=False):
    if not is_generator(gen) or gen.GetDocument()!=doc:raise ValueError('Load or create a generator first.')
    if model!=gen[c4d.ID_USERDATA,2]:raise ValueError('Model differs from the loaded generator. Load the intended generator first.')
    validate_route(route,model,gen)
    if material is not None and (not isinstance(material,c4d.BaseMaterial) or material.GetDocument()!=doc):raise ValueError('Assign a material from this document.')
    if ground is not None:
        if not isinstance(ground,c4d.BaseObject) or ground.GetDocument()!=doc:raise ValueError('Assign a ground object from this document.')
        if gen in list(core['walk'](ground)) or ground in list(core['walk'](gen)):raise ValueError('Ground must be outside the generator hierarchy.')
        if not any(isinstance(n,c4d.PolygonObject) and n.GetPolygonCount()>0 for n in core['walk'](ground)):
            raise ValueError('Ground must be editable polygons or a group of polygon meshes. Make primitives editable first.')
    if spacing<=0 or sag<0 or radius<=0 or not 4<=samples<=64:raise ValueError('Check spacing, sag, radius and span segments.')
    expected=len([n for n in gen[c4d.ID_USERDATA,13].GetChildren() if n.GetType()==c4d.Onull]) if gen[c4d.ID_USERDATA,13] else int(gen[c4d.ID_USERDATA,5])
    checker=GENERATOR_HELPERS
    for variant in (corner_model,end_model):
        if variant is None:continue
        if not isinstance(variant,c4d.BaseObject) or variant.GetDocument()!=doc:raise ValueError('Assign a pole model from this document.')
        if gen in list(core['walk'](variant)) or variant in list(core['walk'](gen)):raise ValueError('Variant must be outside generator hierarchy.')
        checker['variant_data'](variant,expected)
    code=GENERATOR_CODE
    ids={d[1].id for d,bc in gen.GetUserDataContainer()}
    if ids not in (set(range(1,17)),set(range(1,18)),set(range(1,20)),set(range(1,23)),set(range(1,28)),set(range(1,31))):raise ValueError('Unsupported generator parameters; keep this generator unchanged.')
    if own_undo:doc.StartUndo()
    try:
        if own_undo:doc.AddUndo(c4d.UNDOTYPE_CHANGE,gen)
        if 17 not in ids:
            bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK);bc[c4d.DESC_NAME]='Wire Material';gen.AddUserData(bc)
        if 18 not in ids:
            bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_BASELISTLINK);bc[c4d.DESC_NAME]='Ground Surface';gen.AddUserData(bc)
            bc=c4d.GetCustomDataTypeDefault(c4d.DTYPE_REAL);bc[c4d.DESC_NAME]='Ground Offset (cm)';gen.AddUserData(bc)
        if 20 not in ids:
            for name,dtype in (('Corner Pole Model',c4d.DTYPE_BASELISTLINK),('End Pole Model',c4d.DTYPE_BASELISTLINK),('Corner Angle (degrees)',c4d.DTYPE_REAL)):
                bc=c4d.GetCustomDataTypeDefault(dtype);bc[c4d.DESC_NAME]=name;gen.AddUserData(bc)
        if 23 not in ids:
            for name,dtype in (('Pole Pitch (degrees)',c4d.DTYPE_REAL),('Pole Bank (degrees)',c4d.DTYPE_REAL),('Random Yaw (degrees)',c4d.DTYPE_REAL),('Random Tilt (degrees)',c4d.DTYPE_REAL),('Random Seed',c4d.DTYPE_LONG)):
                bc=c4d.GetCustomDataTypeDefault(dtype);bc[c4d.DESC_NAME]=name;gen.AddUserData(bc)
        if 28 not in ids:
            for name,dtype in (('Spline Preview (disable before render)',c4d.DTYPE_BOOL),('Wire Settings',c4d.DTYPE_BASELISTLINK),('Pole Overrides',c4d.DTYPE_BASELISTLINK)):
                bc=c4d.GetCustomDataTypeDefault(dtype);bc[c4d.DESC_NAME]=name;gen.AddUserData(bc)
        gen[c4d.ID_USERDATA,28]=preview
        for ident,value in enumerate((pitch,bank,random_yaw,random_tilt,seed),23):gen[c4d.ID_USERDATA,ident]=value
        gen[c4d.ID_USERDATA,20]=corner_model;gen[c4d.ID_USERDATA,21]=end_model;gen[c4d.ID_USERDATA,22]=corner_angle
        for ident,value in {1:route,3:spacing,7:sag,8:radius,9:samples,10:end,11:math.radians(rotation),15:align,16:corners,17:material}.items():
            gen[c4d.ID_USERDATA,ident]=value
        gen[c4d.ID_USERDATA,18]=ground;gen[c4d.ID_USERDATA,19]=ground_offset
        if gen[c4d.OPYTHON_CODE]!=code:gen[c4d.OPYTHON_CODE]=code
        gen.Message(c4d.MSG_UPDATE)
    finally:
        if own_undo:doc.EndUndo()
    c4d.EventAdd()

class Manager(c4d.gui.GeDialog):
    def __init__(self):self.gen=None;self.owner=None;self.drag_doc=None;self.drag_control=None;self.last_state=None;self.gen_guid=None
    def button(self,i,label):self.AddButton(i,c4d.BFH_SCALEFIT,initw=0,inith=0,name=label)
    def link(self,i,label):
        self.AddStaticText(i+1000,c4d.BFH_LEFT,name=label)
        return self.AddCustomGui(i,c4d.CUSTOMGUI_LINKBOX,'',c4d.BFH_SCALEFIT,320,0,c4d.BaseContainer())
    def CreateLayout(self):
        self.SetTitle('Pole Wire 1.0')
        self.ScrollGroupBegin(50,c4d.BFH_SCALEFIT|c4d.BFV_SCALEFIT,c4d.SCROLLGROUP_VERT|c4d.SCROLLGROUP_AUTOVERT,initw=500,inith=550)
        self.GroupBegin(1,c4d.BFH_SCALEFIT,1,0);self.GroupBorderSpace(10,10,10,10)
        self.button(10,'Load Selected Generator / Model')
        self.modelbox=self.link(11,'Pole Model')
        self.routebox=self.link(12,'Route Spline')
        self.GroupBegin(2,c4d.BFH_SCALEFIT,3,1)
        self.button(13,'Use Selected Spline');self.button(14,'Create Straight Route');self.button(15,'Edit Route Points');self.GroupEnd()
        self.AddStaticText(16,c4d.BFH_LEFT,name='New rig connectors (existing rig is preserved)')
        self.AddEditNumberArrows(17,c4d.BFH_SCALEFIT,initw=80,inith=0)
        self.button(18,'Create Rig + Generator')
        self.cornerbox=self.link(38,'Corner Pole Model (optional)')
        self.endbox=self.link(39,'End Pole Model (optional)')
        self.button(40,'Prepare Corner Rig');self.button(41,'Prepare End Rig')
        self.AddStaticText(1042,c4d.BFH_LEFT,name='Corner Angle (degrees)')
        self.AddEditNumberArrows(42,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.groundbox=self.link(36,'Ground Surface (editable mesh / group, optional)')
        self.AddStaticText(1037,c4d.BFH_LEFT,name='Ground Offset (cm)')
        self.AddEditNumberArrows(37,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.GroupBegin(3,c4d.BFH_SCALEFIT,2,0)
        for i,label in ((20,'Pole Spacing (cm)'),(21,'Sag (cm)'),(22,'Wire Radius (cm)'),(23,'Segments per Span'),(24,'Pole Rotation (degrees)')):
            self.AddStaticText(i+1000,c4d.BFH_LEFT,name=label);self.AddEditNumberArrows(i,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.GroupEnd()
        for i,label in ((25,'Include End Pole'),(26,'Align to Adjacent Spans'),(27,'Poles at Linear Spline Corners')):
            self.AddCheckbox(i,c4d.BFH_LEFT,initw=0,inith=0,name=label)
        for ident,label in ((43,'Pole Pitch (degrees)'),(44,'Pole Bank (degrees)'),(45,'Random Yaw +/- (degrees)'),(46,'Random Tilt +/- (degrees)'),(47,'Random Seed')):
            self.AddStaticText(ident+1000,c4d.BFH_LEFT,name=label);self.AddEditNumberArrows(ident,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.AddCheckbox(60,c4d.BFH_LEFT,initw=0,inith=0,name='Spline Preview - disable before rendering')
        self.button(61,'Create / Select Individual Wire Settings')
        self.AddStaticText(1062,c4d.BFH_LEFT,name='Pole number for override (along route, starts at 1)')
        self.AddEditNumberArrows(62,c4d.BFH_SCALEFIT,initw=100,inith=0)
        self.button(63,'Create / Select Pole Override')
        self.AddStaticText(1063,c4d.BFH_LEFT,name='Edit selected settings in Attributes. Override transforms are local offsets.')
        self.materialbox=self.link(28,'Wire Material (optional)')
        self.AddCheckbox(33,c4d.BFH_LEFT,initw=0,inith=0,name='Live Update')
        self.button(29,'Apply Settings / Route')
        self.GroupBegin(4,c4d.BFH_SCALEFIT,2,1)
        self.button(30,'Select Base');self.button(31,'Select Connectors');self.GroupEnd()
        self.GroupBegin(5,c4d.BFH_SCALEFIT,2,1)
        self.button(34,'Save Pole Preset');self.button(35,'Load Pole Preset');self.GroupEnd()
        self.AddStaticText(32,c4d.BFH_SCALEFIT,name='Select a generator or model to begin.')
        self.GroupEnd();self.GroupEnd();return True
    def InitValues(self):
        self.owner=c4d.documents.GetActiveDocument()
        for ident in (43,44,45,46):self.SetFloat(ident,0.)
        self.SetInt32(62,1,min=1,max=500);self.SetBool(60,False)
        self.SetInt32(47,1)
        self.SetBool(33,True);self.SetTimer(150)
        self.SetFloat(37,0.,min=-100000.,max=100000.,step=.1)
        self.SetFloat(42,35.,min=1.,max=179.,step=1.)
        self.SetInt32(17,3,min=1,max=8)
        for i,val in ((20,600.),(21,35.),(22,1.5),(24,0.)):self.SetFloat(i,val)
        self.SetInt32(23,16,min=4,max=64)
        for i in (25,26,27):self.SetBool(i,True)
        try:self.load_selected()
        except (ValueError,RuntimeError,ReferenceError) as e:self.SetString(32,str(e))
        return True
    def load_gen(self,g):
        self.end_drag()
        self.gen=g;self.gen_guid=g.GetGUID();self.owner=g.GetDocument()
        self.modelbox.SetLink(g[c4d.ID_USERDATA,2]);self.routebox.SetLink(g[c4d.ID_USERDATA,1])
        for control,param in ((20,3),(21,7),(22,8)):self.SetFloat(control,float(g[c4d.ID_USERDATA,param]))
        self.SetFloat(24,math.degrees(float(g[c4d.ID_USERDATA,11])))
        self.SetInt32(23,int(g[c4d.ID_USERDATA,9]),min=4,max=64)
        for control,param in ((25,10),(26,15),(27,16)):self.SetBool(control,bool(g[c4d.ID_USERDATA,param]))
        ids={d[1].id for d,bc in g.GetUserDataContainer()}
        self.materialbox.SetLink(g[c4d.ID_USERDATA,17] if 17 in ids else None)
        self.groundbox.SetLink(g[c4d.ID_USERDATA,18] if 18 in ids else None)
        self.SetFloat(37,float(g[c4d.ID_USERDATA,19]) if 19 in ids else 0.,min=-100000.,max=100000.,step=.1)
        self.cornerbox.SetLink(g[c4d.ID_USERDATA,20] if 20 in ids else None);self.endbox.SetLink(g[c4d.ID_USERDATA,21] if 21 in ids else None)
        self.SetFloat(42,float(g[c4d.ID_USERDATA,22]) if 22 in ids else 35.,min=1.,max=179.,step=1.)
        for ident,param in ((43,23),(44,24),(45,25),(46,26)):self.SetFloat(ident,float(g[c4d.ID_USERDATA,param]) if param in ids else 0.)
        self.SetInt32(47,int(g[c4d.ID_USERDATA,27]) if 27 in ids else 1)
        self.SetBool(60,bool(g[c4d.ID_USERDATA,28]) if 28 in ids else False)
        self.last_state=self.generator_state()
        self.SetString(32,'Loaded: '+g.GetName()+(' (disabled in Object Manager)' if not g[c4d.ID_BASEOBJECT_GENERATOR_FLAG] else ''))
    def load_selected(self):
        self.end_drag()
        doc=c4d.documents.GetActiveDocument();node=doc.GetActiveObject()
        if node is None:raise ValueError('Select a generator or full pole model.')
        if is_generator(node):self.load_gen(node);return
        while node.GetUp() and (node.GetName().startswith('Connector ') or node.GetName() in ('PW Base','PW Connectors')):node=node.GetUp()
        matches=[n for r in doc.GetObjects() for n in core['walk'](r) if is_generator(n) and n[c4d.ID_USERDATA,2]==node]
        if len(matches)==1:self.load_gen(matches[0]);return
        if len(matches)>1:raise ValueError('Select the specific generator to edit.')
        core['bounds'](node);self.owner=doc;self.gen=None;self.gen_guid=None;self.modelbox.SetLink(node);self.routebox.SetLink(None);self.materialbox.SetLink(None);self.groundbox.SetLink(None);self.SetFloat(37,0.);self.cornerbox.SetLink(None);self.endbox.SetLink(None);self.SetFloat(42,35.)
        self.SetString(32,'Model selected. Assign a route or create a straight route.')
    def selected(self,node,points=False):
        if node is None:raise ValueError('No object is assigned.')
        doc=c4d.documents.GetActiveDocument()
        doc.StartUndo()
        try:
            doc.AddUndo(c4d.UNDOTYPE_BITS,node);doc.SetActiveObject(node,c4d.SELECTION_NEW)
        finally:doc.EndUndo()
        if points:doc.SetMode(c4d.Mpoints)
        c4d.EventAdd()
    def end_drag(self):
        if self.drag_doc is not None:
            try:self.drag_doc.EndUndo()
            finally:self.drag_doc=None;self.drag_control=None
    def AskClose(self):self.end_drag();return False
    def DestroyWindow(self):self.end_drag()
    def generator_state(self):
        if self.gen is None:return None
        ids={d[1].id for d,bc in self.gen.GetUserDataContainer()}
        return tuple(self.gen[c4d.ID_USERDATA,i] for i in (1,2,3,7,8,9,10,11,15,16))+tuple(self.gen[c4d.ID_USERDATA,i] if i in ids else None for i in (17,18,19,20,21,22,23,24,25,26,27,28,29,30))
    def recover_generator(self):
        if self.gen_guid is None:return False
        try:
            if self.gen is not None and self.gen.GetDocument()==self.owner:return True
        except (ReferenceError,RuntimeError):pass
        self.gen=None
        for root in self.owner.GetObjects():
            for node in core['walk'](root):
                if is_generator(node) and node.GetGUID()==self.gen_guid:
                    self.load_gen(node);return True
        self.SetString(32,'Generator is absent. Undo/Redo can restore it; no new generator is needed.')
        return False
    def Timer(self,msg):
        if self.drag_doc is None:
            if c4d.documents.GetActiveDocument()!=self.owner:return
            try:
                if not self.recover_generator():return
                if self.generator_state()!=self.last_state:self.load_gen(self.gen)
            except (ReferenceError,RuntimeError,AttributeError):
                self.gen=None
            return
        state=c4d.BaseContainer()
        if c4d.documents.GetActiveDocument()!=self.drag_doc or not c4d.gui.GetInputState(c4d.BFM_INPUT_MOUSE,c4d.BFM_INPUT_MOUSELEFT,state) or not state[c4d.BFM_INPUT_VALUE]:
            self.end_drag()
    def apply_panel(self,control=None,dragging=False):
        doc=c4d.documents.GetActiveDocument()
        if doc!=self.owner:raise ValueError('Document changed. Load a generator again.')
        if not self.recover_generator():raise ValueError('Generator is absent. Restore it with Undo/Redo or load another generator.')
        if self.drag_doc is not None and self.drag_control!=control:self.end_drag()
        if dragging and self.drag_doc is None:
            doc.StartUndo();doc.AddUndo(c4d.UNDOTYPE_CHANGE,self.gen)
            self.drag_doc=doc;self.drag_control=control
        try:
            apply_settings(doc,self.gen,self.modelbox.GetLink(doc),self.routebox.GetLink(doc),self.GetFloat(20),self.GetFloat(21),self.GetFloat(22),self.GetInt32(23),self.GetFloat(24),self.GetBool(25),self.GetBool(26),self.GetBool(27),self.materialbox.GetLink(doc),own_undo=self.drag_doc is None,ground=self.groundbox.GetLink(doc),ground_offset=self.GetFloat(37),corner_model=self.cornerbox.GetLink(doc),end_model=self.endbox.GetLink(doc),corner_angle=self.GetFloat(42),pitch=self.GetFloat(43),bank=self.GetFloat(44),random_yaw=self.GetFloat(45),random_tilt=self.GetFloat(46),seed=self.GetInt32(47),preview=self.GetBool(60))
        except Exception:
            self.end_drag();raise
        if not dragging:self.end_drag()
        self.last_state=self.generator_state()
        # EventAdd is deferred while a numeric gadget owns the drag loop.
        # Evaluate and present the active viewport before returning the callback.
        if self.GetBool(33):
            flags=c4d.DRAWFLAGS_ONLY_ACTIVE_VIEW|c4d.DRAWFLAGS_NO_THREAD|c4d.DRAWFLAGS_FORCEFULLREDRAW
            if dragging:flags|=c4d.DRAWFLAGS_INDRAG
            c4d.DrawViews(flags)
        self.SetString(32,'Updated live.' if self.GetBool(33) else 'Settings applied.')
    def Command(self,i,msg):
        try:
            live_fields=(12,20,21,22,23,24,25,26,27,28,36,37,38,39,42,43,44,45,46,47,60)
            if i not in live_fields:self.end_drag()
            doc=c4d.documents.GetActiveDocument()
            if i==10:self.load_selected();return True
            if doc!=self.owner:raise ValueError('Document changed. Load a model or generator again.')
            model=self.modelbox.GetLink(doc);route=self.routebox.GetLink(doc)
            if i==13:
                node=doc.GetActiveObject()
                if node is None or node.GetRealSpline() is None:raise ValueError('Select a spline in Object Manager.')
                self.routebox.SetLink(node);self.SetString(32,'Route selected. Click Apply to connect it.')
                if self.GetBool(33):self.apply_panel()
            elif i==14:
                if model is None:raise ValueError('Assign a pole model first.')
                origin,top,_,_=core['bounds'](model);height=max(1.,(top-origin.y)*model.GetMg().v2.GetLength())
                start=model.GetMg()*origin+c4d.Vector(height,0,0)
                route=c4d.SplineObject(2,c4d.SPLINETYPE_LINEAR);route.SetName('PW Route')
                route.SetAllPoints([start,start+c4d.Vector(0,0,max(1.,self.GetFloat(20))*2)]);route.Message(c4d.MSG_UPDATE)
                doc.StartUndo()
                try:doc.InsertObject(route);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,route)
                finally:doc.EndUndo()
                self.routebox.SetLink(route);c4d.EventAdd();self.SetString(32,'Route created. Click Create or Apply to connect it.')
                if self.GetBool(33):self.apply_panel()
            elif i==15:
                if not isinstance(route,c4d.SplineObject):raise ValueError('Point editing requires an editable spline.')
                self.selected(route,True);self.SetString(32,'Move or add spline points in the viewport. Connected generators follow automatically.')
            elif i==18:
                if model is None:raise ValueError('Assign a pole model first.')
                validate_route(route,model)
                requested_ground=self.groundbox.GetLink(doc);requested_offset=self.GetFloat(37)
                requested_corner=self.cornerbox.GetLink(doc);requested_end=self.endbox.GetLink(doc);requested_angle=self.GetFloat(42)
                gen,created=core['create_setup'](doc,model,self.GetInt32(17),route);self.load_gen(gen)
                if created and any(n is not None for n in (requested_ground,requested_corner,requested_end)):
                    self.groundbox.SetLink(requested_ground);self.SetFloat(37,requested_offset);self.cornerbox.SetLink(requested_corner);self.endbox.SetLink(requested_end);self.SetFloat(42,requested_angle);self.apply_panel()
                self.SetString(32,'Rig and generator created.' if created else 'Existing generator loaded. Select a route and click Apply to change it.')
            elif i in (40,41):
                variant=(self.cornerbox if i==40 else self.endbox).GetLink(doc)
                if variant is None:raise ValueError('Assign the variant model first.')
                if variant.GetDocument()!=doc:raise ValueError('Assign a model from this document.')
                if self.gen is not None and (variant in list(core['walk'](self.gen)) or self.gen in list(core['walk'](variant))):raise ValueError('Variant must be outside generator hierarchy.')
                existing=[n for n in variant.GetChildren() if n.GetName() in ('PW Base','PW Connectors')]
                if not existing:
                    group=self.gen[c4d.ID_USERDATA,13] if self.gen else None
                    count=len([n for n in group.GetChildren() if n.GetType()==c4d.Onull]) if group else self.GetInt32(17)
                    core['create_rig'](doc,variant,count)
                group=next((n for n in variant.GetChildren() if n.GetName()=='PW Connectors'),None)
                if group is None:raise ValueError('Incomplete rig: check PW Base and PW Connectors.')
                self.selected(group)
                if self.GetBool(33):self.apply_panel()
                self.SetString(32,'Rig ready. Position PW Base and Connector Nulls on this model.')
            elif i in (61,63):
                self.apply_panel()
                if self.gen is None:raise ValueError('Load a generator first.')
                g=self.gen;param=29 if i==61 else 30;group=g[c4d.ID_USERDATA,param]
                def field(node,name,dtype,value):
                    bc=c4d.GetCustomDataTypeDefault(dtype);bc[c4d.DESC_NAME]=name;ident=node.AddUserData(bc)
                    if value is not None:node[ident]=value
                doc.StartUndo()
                try:
                    if group is None:
                        doc.AddUndo(c4d.UNDOTYPE_CHANGE,g)
                        group=c4d.BaseObject(c4d.Onull);group.SetName(g.GetName()+(' - Wire Settings' if i==61 else ' - Overrides'))
                        doc.InsertObject(group);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,group);g[c4d.ID_USERDATA,param]=group
                    if i==61:
                        mounts=g[c4d.ID_USERDATA,13]
                        count=len([n for n in mounts.GetChildren() if n.GetType()==c4d.Onull]) if mounts else int(g[c4d.ID_USERDATA,5])
                        for index in range(len(group.GetChildren()),count):
                            row=c4d.BaseObject(c4d.Onull);row.SetName('Wire %02d'%(index+1))
                            for name,dtype,value in (('Enabled',c4d.DTYPE_BOOL,True),('Custom Sag and Radius',c4d.DTYPE_BOOL,False),('Sag (cm)',c4d.DTYPE_REAL,g[c4d.ID_USERDATA,7]),('Radius (cm)',c4d.DTYPE_REAL,g[c4d.ID_USERDATA,8]),('Material',c4d.DTYPE_BASELISTLINK,None)):field(row,name,dtype,value)
                            row.InsertUnderLast(group);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,row)
                        target=group.GetDown() or group
                    else:
                        index=self.GetInt32(62);target=next((n for n in group.GetChildren() if n[c4d.ID_USERDATA,1]==index),None)
                        if target is None:
                            target=c4d.BaseObject(c4d.Onull);target.SetName('Pole %03d Override'%index)
                            for name,dtype,value in (('Pole Number',c4d.DTYPE_LONG,index),('Hide Pole (keep wires)',c4d.DTYPE_BOOL,False),('Model (prepared rig)',c4d.DTYPE_BASELISTLINK,None)):field(target,name,dtype,value)
                            target.InsertUnderLast(group);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,target)
                finally:doc.EndUndo()
                self.selected(target);self.last_state=self.generator_state();c4d.EventAdd()
            elif i==29:
                self.apply_panel()
            elif i in (30,31):
                if self.gen is None:raise ValueError('Load or create a generator first.')
                self.selected(self.gen[c4d.ID_USERDATA,12 if i==30 else 13])
            elif i==34:
                path=c4d.storage.SaveDialog(title='New preset folder name',force_suffix='')
                if path:
                    saved=library['save_preset'](doc,model,path)
                    self.SetString(32,'Preset saved with assets: '+str(saved))
            elif i==35:
                path=c4d.storage.LoadDialog(title='Load pole preset (.c4d)')
                if path:
                    imported=library['load_preset'](doc,path)
                    self.gen=None;self.gen_guid=None;self.modelbox.SetLink(imported);self.routebox.SetLink(None);self.materialbox.SetLink(None);self.groundbox.SetLink(None);self.SetFloat(37,0.);self.cornerbox.SetLink(None);self.endbox.SetLink(None);self.SetFloat(42,35.)
                    self.SetString(32,'Preset loaded. Assign a route and click Create Rig + Generator.')
            elif i in live_fields and self.GetBool(33):self.apply_panel(i,bool(msg[c4d.BFM_ACTION_INDRAG]))
        except (ValueError,RuntimeError,ReferenceError,AttributeError) as e:
            self.end_drag();self.SetString(32,str(e))
        return True

def main(plugin_id=0):
    import sys,types
    session=sys.modules.setdefault('_pole_wire_manager',types.ModuleType('_pole_wire_manager'))
    old=getattr(session,'dialog',None)
    if old is not None:old.Close()
    session.dialog=Manager();session.dialog.Open(c4d.DLG_TYPE_ASYNC,pluginid=plugin_id,defaultw=540,defaulth=660)

if __name__=='__main__':main()
