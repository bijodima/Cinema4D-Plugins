"""Pole Wire 1.0 - local command plugin."""
from pathlib import Path
import c4d
PLUGIN_ID=10612348
ROOT=Path(__file__).parent
namespace={'__name__':'polewire_manager','__file__':str(ROOT/'Pole Wire Manager.py')}
exec(compile((ROOT/'Pole Wire Manager.py').read_text(encoding='utf-8'),str(ROOT/'Pole Wire Manager.py'),'exec'),namespace)
class PoleWireCommand(c4d.plugins.CommandData):
    def Execute(self,doc):
        namespace['main'](PLUGIN_ID)
        return True
    def RestoreLayout(self,secret):
        import sys,types
        session=sys.modules.setdefault('_pole_wire_manager',types.ModuleType('_pole_wire_manager'))
        session.dialog=namespace['Manager']()
        return session.dialog.Restore(pluginid=PLUGIN_ID,secret=secret)
if __name__=='__main__':
    icon=c4d.bitmaps.BaseBitmap()
    result=icon.InitWith(str(ROOT/'res/icon.png'))[0]
    if result!=c4d.IMAGERESULT_OK:icon=None
    if not c4d.plugins.RegisterCommandPlugin(id=PLUGIN_ID,str='Pole Wire',info=0,icon=icon,help='Build pole and wire routes',dat=PoleWireCommand()):
        print('Pole Wire: command registration failed (ID collision or resources).')
