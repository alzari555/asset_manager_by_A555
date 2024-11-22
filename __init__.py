import bpy
import os
import glob
import shutil
from mathutils import Vector
from bpy.props import (
    StringProperty,
    CollectionProperty,
    BoolProperty,
    IntProperty,
    EnumProperty,
    FloatProperty
)
from bpy.types import (
    Operator,
    Panel,
    PropertyGroup,
    UIList
)

# Constantes
SUPPORTED_ASSET_TYPES = {
    'MESH': "Mesh",
    'MATERIAL': "Material",
    'COLLECTION': "Collection",
    'GEOMETRY_NODES': "Geometry Nodes"
}
FILE_EXTENSION = '.blend'

class AssetItem(PropertyGroup):
    """Clase para almacenar información de un asset individual"""
    name: StringProperty(
        name="Nombre",
        description="Nombre del asset"
    )
    filepath: StringProperty(
        name="Ruta del archivo",
        description="Ruta al archivo .blend del asset"
    )
    asset_type: StringProperty(
        name="Tipo de Asset",
        description="Tipo del asset (mesh, material, etc.)",
        default="UNKNOWN"
    )
    is_editing: BoolProperty(
        name="Editando",
        description="Indica si el asset está siendo editado",
        default=False
    )
    edit_name: StringProperty(
        name="Nombre en edición",
        description="Nombre temporal durante la edición"
    )
    is_selected: BoolProperty(
        name="Seleccionado",
        description="Indica si el asset está seleccionado para operaciones en masa",
        default=False
    )

class ASSET_LIBRARY_Properties(PropertyGroup):
    """Clase principal para gestionar la biblioteca de assets"""
    library_path: StringProperty(
        name="Directorio",
        description="Directorio donde se guardan los assets",
        default="",
        subtype='DIR_PATH',
        update=lambda self, context: self.load_assets(context)
    )
    
    assets: CollectionProperty(type=AssetItem)
    active_asset_index: IntProperty()
    search_term: StringProperty(
        name="Buscar",
        description="Buscar assets por nombre",
        default=""
    )
    select_all: BoolProperty(
        name="Seleccionar Todo",
        description="Seleccionar/Deseleccionar todos los assets",
        default=False,
        update=lambda self, context: self.update_all_selections(context)
    )
    
    load_mode: EnumProperty(
        name="Load Mode",
        description="Modo de carga del asset",
        items=[
            ('COLLECTION', 'Collection', 'Cargar como colección', 'OUTLINER_COLLECTION', 0),
            ('MATERIAL', 'Material', 'Aplicar material', 'MATERIAL', 1),
            ('NODES', 'Geometry Nodes', 'Aplicar geometry nodes', 'NODETREE', 2),
            ('MESH', 'Mesh Only', 'Cargar solo la malla', 'OUTLINER_OB_MESH', 3),
        ],
        default='COLLECTION'
    )
    
    arrange_mode: EnumProperty(
        name="Arrange Mode",
        description="Modo de organización al cargar múltiples assets",
        items=[
            ('RELATIVE', 'Posición Relativa', 'Mantener posiciones relativas', 'ORIENTATION_LOCAL', 0),
            ('ROW', 'En Fila', 'Organizar en fila horizontal', 'ANCHOR_LEFT', 1),
        ],
        default='RELATIVE'
    )
    
    spacing: FloatProperty(
        name="Spacing",
        description="Espacio entre assets cuando se organizan en fila",
        default=3.0,
        min=0.0,
        soft_max=10.0
    )
    
    force_mode: BoolProperty(
        name="Force Mode",
        description="Sobrescribir materiales/modificadores existentes",
        default=False
    )
    
    def update_all_selections(self, context):
        for asset in self.assets:
            asset.is_selected = self.select_all
    
    def load_assets(self, context):
        """Carga los assets desde el directorio"""
        self.assets.clear()
        
        if not self.library_path or not os.path.exists(self.library_path):
            return

        try:
            for file in os.listdir(self.library_path):
                if file.endswith(FILE_EXTENSION):
                    # Filtrar por término de búsqueda
                    if self.search_term and self.search_term.lower() not in file.lower():
                        continue
                        
                    item = self.assets.add()
                    item.name = os.path.splitext(file)[0]
                    item.filepath = os.path.join(self.library_path, file)
                    
                    # Detectar tipo de asset
                    try:
                        with bpy.data.libraries.load(item.filepath) as (data_from, data_to):
                            if data_from.materials:
                                item.asset_type = "MATERIAL"
                            elif any(mod.type == 'NODES' for obj in data_from.objects 
                                   for mod in obj.modifiers):
                                item.asset_type = "NODES"
                            elif data_from.objects:
                                item.asset_type = "MESH"
                            else:
                                item.asset_type = "UNKNOWN"
                    except:
                        item.asset_type = "UNKNOWN"
                        
        except Exception as e:
            self.report({'ERROR'}, f"Error al cargar los assets: {str(e)}")

class ASSET_LIBRARY_OT_save_asset(Operator):
    """Guarda el objeto seleccionado como un asset en la biblioteca"""
    bl_idname = "asset.save_to_library"
    bl_label = "Guardar Asset"
    bl_description = "Guarda los objetos seleccionados como un asset en la biblioteca"
    bl_options = {'REGISTER', 'UNDO'}

    def execute(self, context):
        scene = context.scene
        library_props = scene.asset_library

        if not library_props.library_path:
            self.report({'ERROR'}, "Por favor seleccione una carpeta para la biblioteca")
            return {'CANCELLED'}

        if not os.path.exists(library_props.library_path):
            try:
                os.makedirs(library_props.library_path)
            except Exception as e:
                self.report({'ERROR'}, f"Error al crear la carpeta de la biblioteca: {str(e)}")
                return {'CANCELLED'}

        if not context.selected_objects:
            self.report({'ERROR'}, "Por favor seleccione al menos un objeto para guardar")
            return {'CANCELLED'}

        if not context.active_object:
            self.report({'ERROR'}, "Por favor seleccione un objeto activo")
            return {'CANCELLED'}

        asset_name = context.active_object.name
        asset_filepath = os.path.join(library_props.library_path, asset_name + FILE_EXTENSION)

        try:
            # Recolectar datos a guardar
            data_blocks = set()
            
            # Calcular el centro del grupo
            selected_objects = context.selected_objects
            if not selected_objects:
                self.report({'ERROR'}, "Por favor seleccione al menos un objeto")
                return {'CANCELLED'}
                
            # Calcular centro usando bounds
            min_co = Vector((float('inf'),) * 3)
            max_co = Vector((float('-inf'),) * 3)
            for obj in selected_objects:
                if hasattr(obj, "bound_box"):
                    for v in obj.bound_box:
                        world_co = obj.matrix_world @ Vector(v)
                        min_co.x = min(min_co.x, world_co.x)
                        min_co.y = min(min_co.y, world_co.y)
                        min_co.z = min(min_co.z, world_co.z)
                        max_co.x = max(max_co.x, world_co.x)
                        max_co.y = max(max_co.y, world_co.y)
                        max_co.z = max(max_co.z, world_co.z)
                else:
                    # Para objetos sin bound_box, usar la ubicación del objeto
                    world_co = obj.matrix_world.translation
                    min_co.x = min(min_co.x, world_co.x)
                    min_co.y = min(min_co.y, world_co.y)
                    min_co.z = min(min_co.z, world_co.z)
                    max_co.x = max(max_co.x, world_co.x)
                    max_co.y = max(max_co.y, world_co.y)
                    max_co.z = max(max_co.z, world_co.z)
            
            center = (min_co + max_co) / 2
            
            # Guardar las posiciones relativas al centro
            positions = {}
            for obj in selected_objects:
                positions[obj.name] = obj.matrix_world.translation - center
            
            def process_node_tree(node_tree):
                if not node_tree:
                    return
                for node in node_tree.nodes:
                    if node.type == 'TEX_IMAGE' and node.image:
                        data_blocks.add(node.image)
                        if node.image.packed_file is None and node.image.filepath:
                            node.image.pack()
                    
                    if hasattr(node, "node_tree") and node.node_tree:
                        data_blocks.add(node.node_tree)
                        process_node_tree(node.node_tree)

            # Agregar objetos seleccionados y sus datos
            for obj in selected_objects:
                data_blocks.add(obj)
                
                # Agregar datos del objeto (mesh, curve, gpencil data, etc)
                if obj.data:
                    data_blocks.add(obj.data)
                
                # Agregar materiales
                if hasattr(obj.data, "materials"):
                    for mat_slot in obj.material_slots:
                        mat = mat_slot.material
                        if mat:
                            data_blocks.add(mat)
                            if mat.use_nodes and mat.node_tree:
                                data_blocks.add(mat.node_tree)
                                process_node_tree(mat.node_tree)
                
                # Agregar modificadores
                for mod in obj.modifiers:
                    # Geometry Nodes
                    if mod.type == 'NODES' and mod.node_group:
                        data_blocks.add(mod.node_group)
                        process_node_tree(mod.node_group)
                        
                        for node in mod.node_group.nodes:
                            if node.type == 'GROUP_INPUT':
                                for socket in node.outputs:
                                    if hasattr(socket, "default_value"):
                                        if isinstance(socket.default_value, bpy.types.Material):
                                            data_blocks.add(socket.default_value)
                                            if socket.default_value.use_nodes and socket.default_value.node_tree:
                                                data_blocks.add(socket.default_value.node_tree)
                                                process_node_tree(socket.default_value.node_tree)
                    
                    # Otros tipos de modificadores que puedan tener datos
                    elif hasattr(mod, "object") and mod.object:
                        data_blocks.add(mod.object)
                        if mod.object.data:
                            data_blocks.add(mod.object.data)
                
                # Guardar datos específicos según el tipo de objeto
                if obj.type == 'GPENCIL':
                    # Guardar materiales de Grease Pencil
                    for material in obj.data.materials:
                        if material:
                            data_blocks.add(material)
                
                elif obj.type == 'CURVE':
                    # Guardar objetos de taper y bevel si existen
                    if obj.data.bevel_object:
                        data_blocks.add(obj.data.bevel_object)
                        if obj.data.bevel_object.data:
                            data_blocks.add(obj.data.bevel_object.data)
                    if obj.data.taper_object:
                        data_blocks.add(obj.data.taper_object)
                        if obj.data.taper_object.data:
                            data_blocks.add(obj.data.taper_object.data)
            
            # Guardar las posiciones relativas como una propiedad personalizada
            for obj in selected_objects:
                obj["relative_positions"] = str(positions)
            
            bpy.data.libraries.write(
                asset_filepath,
                data_blocks,
                fake_user=True,
                compress=True
            )

            library_props.load_assets(context)
            self.report({'INFO'}, f"Asset '{asset_name}' guardado correctamente")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error al guardar el asset: {str(e)}")
            return {'CANCELLED'}

class ASSET_LIBRARY_OT_load_asset(Operator):
    """Carga los assets seleccionados en la escena actual"""
    bl_idname = "asset.load_from_library"
    bl_label = "Cargar Asset"
    bl_description = "Carga los assets seleccionados en la escena actual"
    
    def execute(self, context):
        scene = context.scene
        library_props = scene.asset_library
        cursor_location = context.scene.cursor.location
        
        selected_assets = [asset for asset in library_props.assets if asset.is_selected]
        
        if not selected_assets:
            if library_props.active_asset_index >= len(library_props.assets):
                self.report({'ERROR'}, "No hay assets seleccionados para cargar")
                return {'CANCELLED'}
            selected_assets = [library_props.assets[library_props.active_asset_index]]

        try:
            for i, asset in enumerate(selected_assets):
                with bpy.data.libraries.load(asset.filepath) as (data_from, data_to):
                    data_to.objects = data_from.objects
                    
                    if library_props.load_mode == 'MATERIAL':
                        data_to.materials = data_from.materials
                        data_to.node_groups = [ng for ng in data_from.node_groups 
                                             if any(hasattr(mat, 'node_tree') and mat.node_tree == ng 
                                                  for mat in data_from.materials)]
                    
                    elif library_props.load_mode == 'NODES':
                        data_to.node_groups = data_from.node_groups

                loaded_objects = []
                relative_positions = {}
                
                # Cargar posiciones relativas si existen
                for obj in data_to.objects:
                    if obj is not None and "relative_positions" in obj:
                        try:
                            relative_positions = eval(obj["relative_positions"])
                            break
                        except:
                            pass

                for obj in data_to.objects:
                    if obj is not None:
                        if library_props.load_mode in {'COLLECTION', 'MESH'}:
                            scene.collection.objects.link(obj)
                            loaded_objects.append(obj)
                            
                            # Aplicar posición según el modo de organización
                            if library_props.arrange_mode == 'RELATIVE' and relative_positions:
                                if obj.name in relative_positions:
                                    rel_pos = relative_positions[obj.name]
                                    if isinstance(rel_pos, Vector):
                                        obj.location = cursor_location + rel_pos
                            else:  # ROW mode
                                obj.location = cursor_location + Vector((i * library_props.spacing, 0, 0))
                            
                            if library_props.load_mode == 'MESH':
                                if hasattr(obj.data, "materials"):
                                    obj.data.materials.clear()
                                while obj.modifiers:
                                    obj.modifiers.remove(obj.modifiers[0])
                        
                        if library_props.load_mode == 'MATERIAL':
                            for target_obj in context.selected_objects:
                                if hasattr(target_obj.data, "materials"):
                                    # Limpiar materiales existentes si está en modo forzado
                                    if library_props.force_mode:
                                        while len(target_obj.data.materials):
                                            target_obj.data.materials.pop()
                                    
                                    # Agregar nuevos materiales
                                    for mat in data_to.materials:
                                        if mat is not None and isinstance(mat, bpy.types.Material):
                                            # Si el material ya existe en el objeto y no estamos en modo forzado, saltarlo
                                            if not library_props.force_mode and mat.name in target_obj.data.materials:
                                                continue
                                            
                                            # Asegurarse de que el material use nodos
                                            if not mat.use_nodes:
                                                mat.use_nodes = True
                                            
                                            # Agregar el material al objeto
                                            target_obj.data.materials.append(mat)

                        if library_props.load_mode == 'NODES':
                            for target_obj in context.selected_objects:
                                for mod in obj.modifiers:
                                    if mod.type == 'NODES':
                                        if library_props.force_mode:
                                            for existing_mod in target_obj.modifiers:
                                                if existing_mod.type == 'NODES':
                                                    target_obj.modifiers.remove(existing_mod)
                                        
                                        new_mod = target_obj.modifiers.new(name=mod.name, type='NODES')
                                        new_mod.node_group = mod.node_group

                if library_props.load_mode not in {'COLLECTION', 'MESH'}:
                    for obj in loaded_objects:
                        bpy.data.objects.remove(obj, do_unlink=True)

            self.report({'INFO'}, f"Assets cargados correctamente")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Error al cargar los assets: {str(e)}")
            return {'CANCELLED'}

class ASSET_LIBRARY_OT_delete_asset(Operator):
    """Elimina el asset seleccionado de la biblioteca"""
    bl_idname = "asset.delete_from_library"
    bl_label = "Eliminar Asset"
    bl_description = "Elimina el asset seleccionado de la biblioteca"
    
    asset_name: StringProperty()
    asset_index: IntProperty()
    
    def invoke(self, context, event):
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        library_props = context.scene.asset_library
        
        if not library_props.library_path:
            self.report({'ERROR'}, "No se ha seleccionado una carpeta de biblioteca")
            return {'CANCELLED'}
            
        asset_path = os.path.join(library_props.library_path, self.asset_name + FILE_EXTENSION)
        
        try:
            if os.path.exists(asset_path):
                os.remove(asset_path)
                library_props.load_assets(context)
                self.report({'INFO'}, f"Asset '{self.asset_name}' eliminado correctamente")
                return {'FINISHED'}
            else:
                self.report({'ERROR'}, f"No se encontró el archivo del asset")
                return {'CANCELLED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error al eliminar el asset: {str(e)}")
            return {'CANCELLED'}

class ASSET_LIBRARY_UL_items(UIList):
    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        if self.layout_type in {'DEFAULT', 'COMPACT'}:
            row = layout.row(align=True)
            
            # Checkbox de selección
            row.prop(item, "is_selected", text="")
            
            # Detectar tipo de asset y mostrar icono apropiado
            icon_name = 'OBJECT_DATA'
            try:
                with bpy.data.libraries.load(item.filepath) as (data_from, _):
                    if data_from.materials:
                        icon_name = 'MATERIAL'
                    elif data_from.node_groups:
                        icon_name = 'NODETREE'
            except:
                pass
            
            # Nombre del asset
            row.label(text=item.name, icon=icon_name)
            
            # Botón de eliminación
            op = row.operator("asset.delete_from_library", text="", icon='TRASH', emboss=False)
            if op:
                op.asset_name = item.name
                op.asset_index = index

        elif self.layout_type in {'GRID'}:
            layout.alignment = 'CENTER'
            layout.label(text=item.name)

class ASSET_LIBRARY_PT_main(Panel):
    bl_label = "Biblioteca de Assets"
    bl_idname = "ASSET_LIBRARY_PT_main"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = 'Asset Library'

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        library_props = scene.asset_library

        # Carpeta de la biblioteca
        row = layout.row()
        row.prop(library_props, "library_path", text="")
        
        # Búsqueda y controles
        row = layout.row(align=True)
        row.prop(library_props, "search_term", text="", icon='VIEWZOOM')
        row.operator("asset.refresh_library", text="", icon='FILE_REFRESH')
        
        # Checkbox global y botón de eliminar
        row = layout.row(align=True)
        row.prop(library_props, "select_all", text="Seleccionar Todo")
        row.operator("asset.delete_selected", text="", icon='TRASH')
        
        # Lista de assets
        row = layout.row()
        row.template_list("ASSET_LIBRARY_UL_items", "", library_props, "assets", library_props, "active_asset_index")

        # Controles de guardado
        box = layout.box()
        box.label(text="Guardar Asset")
        row = box.row()
        row.operator("asset.save_to_library", text="Guardar Seleccionado", icon='EXPORT')

        # Controles de carga
        box = layout.box()
        box.label(text="Cargar Asset")
        
        row = box.row()
        row.prop(library_props, "load_mode", text="Modo")
        
        row = box.row()
        row.prop(library_props, "force_mode", text="Forzar")
        
        row = box.row()
        row.prop(library_props, "arrange_mode", text="Organización")
        
        if library_props.arrange_mode == 'ROW':
            row = box.row()
            row.prop(library_props, "spacing", text="Espaciado")
        
        row = box.row()
        row.scale_y = 1.5
        row.operator("asset.load_from_library", text="Cargar Seleccionados", icon='IMPORT')

class ASSET_LIBRARY_OT_refresh_library(Operator):
    bl_idname = "asset.refresh_library"
    bl_label = "Refrescar Lista"
    bl_description = "Actualiza la lista de assets"
    
    def execute(self, context):
        try:
            context.scene.asset_library.load_assets(context)
            self.report({'INFO'}, "Lista de assets actualizada")
            return {'FINISHED'}
        except Exception as e:
            self.report({'ERROR'}, f"Error al actualizar la lista: {str(e)}")
            return {'CANCELLED'}

class ASSET_LIBRARY_OT_delete_selected(Operator):
    bl_idname = "asset.delete_selected"
    bl_label = "Eliminar Seleccionados"
    bl_description = "Elimina todos los assets seleccionados"
    
    def invoke(self, context, event):
        selected_count = len([a for a in context.scene.asset_library.assets if a.is_selected])
        if selected_count == 0:
            self.report({'WARNING'}, "No hay assets seleccionados para eliminar")
            return {'CANCELLED'}
        return context.window_manager.invoke_confirm(self, event)
    
    def execute(self, context):
        library_props = context.scene.asset_library
        deleted_count = 0
        
        try:
            # Crear una lista de assets a eliminar
            assets_to_delete = [asset for asset in library_props.assets if asset.is_selected]
            
            for asset in assets_to_delete:
                if os.path.exists(asset.filepath):
                    os.remove(asset.filepath)
                    deleted_count += 1
            
            # Actualizar la lista
            library_props.load_assets(context)
            
            if deleted_count > 0:
                self.report({'INFO'}, f"Se eliminaron {deleted_count} assets")
                return {'FINISHED'}
            else:
                self.report({'WARNING'}, "No se eliminó ningún asset")
                return {'CANCELLED'}
                
        except Exception as e:
            self.report({'ERROR'}, f"Error al eliminar assets: {str(e)}")
            return {'CANCELLED'}

class ASSET_LIBRARY_OT_select_all(Operator):
    bl_idname = "asset.select_all"
    bl_label = "Seleccionar Todo"
    bl_description = "Selecciona todos los assets en la lista"
    
    def execute(self, context):
        library_props = context.scene.asset_library
        for asset in library_props.assets:
            asset.is_selected = True
        return {'FINISHED'}

class ASSET_LIBRARY_OT_deselect_all(Operator):
    bl_idname = "asset.deselect_all"
    bl_label = "Deseleccionar Todo"
    bl_description = "Deselecciona todos los assets en la lista"
    
    def execute(self, context):
        library_props = context.scene.asset_library
        for asset in library_props.assets:
            asset.is_selected = False
        return {'FINISHED'}

classes = (
    AssetItem,
    ASSET_LIBRARY_Properties,
    ASSET_LIBRARY_OT_save_asset,
    ASSET_LIBRARY_OT_load_asset,
    ASSET_LIBRARY_OT_delete_asset,
    ASSET_LIBRARY_UL_items,
    ASSET_LIBRARY_PT_main,
    ASSET_LIBRARY_OT_select_all,
    ASSET_LIBRARY_OT_deselect_all,
    ASSET_LIBRARY_OT_refresh_library,
    ASSET_LIBRARY_OT_delete_selected,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.asset_library = bpy.props.PointerProperty(type=ASSET_LIBRARY_Properties)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.asset_library

if __name__ == "__main__":
    register()