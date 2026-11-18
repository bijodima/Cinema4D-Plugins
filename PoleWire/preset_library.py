from pathlib import Path
import c4d

def save_preset(doc,model,directory):
    if model is None or model.GetDocument()!=doc:raise ValueError('Assign a model first.')
    directory=Path(directory)
    if directory.exists():raise ValueError('Choose a new preset folder; existing folders are not overwritten.')
    copy=c4d.documents.IsolateObjects(doc,[model])
    if copy is None:raise RuntimeError('Cannot isolate the model.')
    try:
        copy.SetDocumentPath(doc.GetDocumentPath());copy.SetDocumentName('Pole.c4d')
        assets=[];missing=[]
        flags=c4d.SAVEPROJECT_ASSETS|c4d.SAVEPROJECT_SCENEFILE|c4d.SAVEPROJECT_USEDOCUMENTNAMEASFILENAME|c4d.SAVEPROJECT_ASSETLINKS_COPY_FILEASSETS
        if not c4d.documents.SaveProject(copy,flags,str(directory),assets,missing):
            raise RuntimeError('Preset save failed. Missing assets: %d. Check the new folder before retrying.'%len(missing))
        return directory/'Pole.c4d'
    finally:c4d.documents.KillDocument(copy)

def load_preset(doc,path):
    path=Path(path)
    if path.suffix.lower()!='.c4d':raise ValueError('Choose a .c4d pole preset.')
    # Validate before changing the active document.
    check=c4d.documents.LoadDocument(str(path),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
    if check is None:raise ValueError('Cannot open this preset.')
    try:
        if len(check.GetObjects())!=1:raise ValueError('A pole preset must contain one model root.')
    finally:c4d.documents.KillDocument(check)
    objects=list(doc.GetObjects());materials=list(doc.GetMaterials())
    doc.StartUndo()
    try:
        ok=c4d.documents.MergeDocument(doc,str(path),c4d.SCENEFILTER_OBJECTS|c4d.SCENEFILTER_MATERIALS,None)
        added=[n for n in doc.GetObjects() if n not in objects]
        for n in added:doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,n)
        for n in doc.GetMaterials():
            if n not in materials:doc.AddUndo(c4d.UNDOTYPE_NEWOBJ,n)
    finally:doc.EndUndo()
    c4d.EventAdd()
    if not ok or len(added)!=1:raise RuntimeError('Import failed; Undo can remove any imported items.')
    return added[0]
