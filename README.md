# Asset Manager for Blender

## Descripción
Asset Manager es un addon para Blender que proporciona un sistema avanzado y flexible para gestionar assets 3D. Permite guardar y cargar cualquier tipo de objeto (meshes, curvas, grease pencil, etc.) junto con sus materiales, texturas y modificadores, manteniendo sus relaciones y posiciones relativas.

## Características Principales

### Guardado Flexible
- Guarda cualquier tipo de objeto de Blender (meshes, curvas, grease pencil, etc.)
- Preserva materiales, texturas y modificadores
- Mantiene las relaciones entre objetos
- Guarda las posiciones relativas entre objetos
- Empaqueta automáticamente las texturas

### Múltiples Modos de Carga
1. **Modo Colección**: 
   - Carga el asset completo con todos sus datos
   - Mantiene las posiciones relativas entre objetos

2. **Modo Material**: 
   - Aplica los materiales del asset a los objetos seleccionados
   - Opción para forzar la sobreescritura de materiales existentes

3. **Modo Geometry Nodes**: 
   - Aplica los modificadores de geometry nodes del asset
   - Preserva las configuraciones y conexiones de nodos

4. **Modo Mesh**: 
   - Carga solo la geometría sin materiales ni modificadores
   - Útil para reutilizar solo la forma del objeto

### Opciones de Organización
- **Modo Relativo**: Mantiene las posiciones relativas entre objetos
- **Modo Fila**: Organiza los assets en una fila con espaciado personalizable
- Control de espaciado entre objetos

### Interfaz Intuitiva
- Lista de assets con vista previa
- Búsqueda de assets por nombre
- Selección múltiple con checkbox global
- Botón de refresco para actualizar la lista
- Eliminación masiva de assets
- Interfaz organizada y fácil de usar

## Requisitos
- Blender 4.3.0 o superior
- Windows/Mac/Linux

## Instalación
1. Descargar el archivo ZIP del addon
2. En Blender, ir a Edit > Preferences > Add-ons
3. Clic en "Install" y seleccionar el archivo ZIP
4. Activar el addon marcando la casilla

## Uso
1. El addon aparece en el panel lateral del 3D Viewport (tecla N)
2. Seleccionar una carpeta para la biblioteca de assets
3. Para guardar:
   - Seleccionar los objetos a guardar
   - Clic en "Guardar Seleccionado"
4. Para cargar:
   - Seleccionar el modo de carga deseado
   - Seleccionar los assets a cargar
   - Clic en "Cargar Seleccionados"

## Características Avanzadas
- Preservación automática de texturas y materiales
- Soporte para geometry nodes y sus configuraciones
- Manejo de objetos vinculados (como objetos de bevel en curvas)
- Sistema de posicionamiento relativo inteligente

## Notas
- Los assets se guardan con todas sus dependencias
- Las posiciones relativas se calculan automáticamente
- Se pueden seleccionar y cargar múltiples assets a la vez
- La opción de forzado permite sobrescribir configuraciones existentes

## Versión
0.1.3-alpha

## Autor
Zield555

## Licencia
[Especificar la licencia]
