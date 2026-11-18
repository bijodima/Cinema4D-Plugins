"""Run in Cinema 4D Script Manager; creates a generator without changing input objects."""
from pathlib import Path
import c4d


def build(code,route=None,pole=None):
    gen=c4d.BaseObject(c4d.Opython)
    gen.SetName('PW Pole and Wire Generator')
    fields=[
        ('Route Spline',c4d.DTYPE_BASELISTLINK,route,None,None),
        ('Pole Model',c4d.DTYPE_BASELISTLINK,pole,None,None),
        ('Pole Spacing (cm)',c4d.DTYPE_REAL,600.,1.,100000.),
        ('Wire Height (cm)',c4d.DTYPE_REAL,400.,0.,100000.),
        ('Wire Count',c4d.DTYPE_LONG,3,1,8),
        ('Wire Spacing (cm)',c4d.DTYPE_REAL,60.,0.,10000.),
        ('Sag (cm)',c4d.DTYPE_REAL,35.,0.,10000.),
        ('Wire Radius (cm)',c4d.DTYPE_REAL,1.5,.01,100.),
        ('Segments per Span',c4d.DTYPE_LONG,16,4,64),
        ('Include End Pole',c4d.DTYPE_BOOL,True,None,None),
        ('Pole Rotation',c4d.DTYPE_REAL,0.,None,None),
        ('Base Null',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Connector Group',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Auto Base Center',c4d.DTYPE_BOOL,True,None,None),
        ('Align to Adjacent Spans',c4d.DTYPE_BOOL,True,None,None),
        ('Poles at Linear Spline Corners',c4d.DTYPE_BOOL,True,None,None),
        ('Wire Material',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Ground Surface',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Ground Offset (cm)',c4d.DTYPE_REAL,0.,-100000.,100000.),
        ('Corner Pole Model',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('End Pole Model',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Corner Angle (degrees)',c4d.DTYPE_REAL,35.,1.,179.),
        ('Pole Pitch (degrees)',c4d.DTYPE_REAL,0.0,None,None),
        ('Pole Bank (degrees)',c4d.DTYPE_REAL,0.0,None,None),
        ('Random Yaw (degrees)',c4d.DTYPE_REAL,0.0,None,None),
        ('Random Tilt (degrees)',c4d.DTYPE_REAL,0.0,None,None),
        ('Random Seed',c4d.DTYPE_LONG,1,None,None),
        ('Spline Preview (disable before render)',c4d.DTYPE_BOOL,False,None,None),
        ('Wire Settings',c4d.DTYPE_BASELISTLINK,None,None,None),
        ('Pole Overrides',c4d.DTYPE_BASELISTLINK,None,None,None),

    ]
    for name,dtype,value,minimum,maximum in fields:
        bc=c4d.GetCustomDataTypeDefault(dtype);bc[c4d.DESC_NAME]=name
        if minimum is not None:bc[c4d.DESC_MIN]=minimum;bc[c4d.DESC_MAX]=maximum
        if name=='Pole Rotation':bc[c4d.DESC_UNIT]=c4d.DESC_UNIT_DEGREE
        ident=gen.AddUserData(bc)
        if value is not None:gen[ident]=value
    gen[c4d.OPYTHON_OPTIMIZE]=False
    gen[c4d.OPYTHON_CODE]=code
    return gen


def main():
    code=(Path(__file__).parent/'generator_code.py').read_text(encoding='utf-8-sig')
    selected=doc.GetActiveObjects(c4d.GETACTIVEOBJECTFLAGS_0)
    route=next((o for o in selected if o.GetRealSpline() is not None),None)
    pole=next((o for o in selected if o!=route),None)
    gen=build(code,route,pole)
    doc.StartUndo()
    try:
        doc.InsertObject(gen);doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,gen)
        doc.SetActiveObject(gen,c4d.SELECTION_NEW)
    finally:doc.EndUndo();c4d.EventAdd()

if __name__=='__main__':main()
