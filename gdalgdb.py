#!python3

# Using python3 anconda
# conda install -c conda-forge gdal

from pathlib import Path
from contextlib import contextmanager
from osgeo import ogr

@contextmanager
def _get_dataset(gdb_path):
    try:
        driver = ogr.GetDriverByName("OpenFileGDB")
        dataset = driver.Open(gdb_path, False)    # False = no edition, OpenFileGDB driver is read only
        yield dataset
    finally:
        del dataset

def _execute_attach_query(dataset, layer_attach, rel_attr, primary_id):
    q = "SELECT ATT_NAME, DATA FROM {layer_attach} WHERE {layer_attach}.{rel_attr}='{primary_id}'"
    q = q.format(layer_attach=layer_attach, rel_attr=rel_attr, primary_id=primary_id)
    return dataset.ExecuteSQL(q)

def _create_primary_dir(attach_rootpath, primary_name, len_attachs):
    primary_dir = Path(attach_rootpath, primary_name) if len_attachs \
                  else Path(attach_rootpath, "_"+primary_name)
    Path.mkdir(primary_dir, exist_ok=True)
    return primary_dir

def _save_attach(attach, primary_dir):
    attach_name = attach.GetField('ATT_NAME')
    if attach_name[0] == "{" and len(attach_name) > 39:    # if start with uuid
        attach_name = attach_name[38:]
    print(attach_name, end=' ')
    attach_path = Path(primary_dir, attach_name)
    with open(attach_path.as_posix(), 'wb') as filename:
        filename.write(attach.GetFieldAsBinary('DATA'))


def get_layers(gdb_path):
    with _get_dataset(gdb_path) as dataset:
        for layer in dataset:
            print(layer.GetName())

def get_attrs(gdb_path, layer_name):
    with _get_dataset(gdb_path) as dataset:
        layer = dataset.GetLayerByName(layer_name)
        for field in layer.schema:
            print("{:20}{:12}".format(field.GetName(), field.GetTypeName()))

def get_attach(gdb_path, layer_name,
               name_attr="OBJECTID", rel_attr="REL_GLOBALID", ):
    # Get blob attachment from related layer
    root_path = Path(gdb_path).parent
    attach_rootpath = Path(root_path, layer_name+"_attach")
    Path.mkdir(attach_rootpath, exist_ok=True)

    layer_attach = layer_name + "__ATTACH"
    with _get_dataset(gdb_path) as dataset:
        primary = dataset.GetLayerByName(layer_name)
        for p in primary:
            primary_oid = "{:04}".format(p.GetFID())
            primary_gid = p.GetField("GlobalID")
            primary_id = primary_oid if rel_attr == "REL_OBJECTID" \
                         else primary_gid

            primary_name = primary_oid if name_attr == "OBJECTID" \
                           else p.GetField(name_attr)
            print("\n", primary_name, end=' ')

            attachs = _execute_attach_query(dataset, layer_attach, rel_attr, primary_id)
            primary_dir = _create_primary_dir(attach_rootpath, primary_name, len(attachs))
            for a in attachs:
                _save_attach(a, primary_dir)