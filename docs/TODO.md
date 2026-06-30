# Agregaciones
- Identificacion de sistema para recurso. UNICO para toda la estructura

> Permite busquedas globales basadas en una identificacion textual
> P. Ej: ResourceTree.get_absolute("SYSTEM_UNIQUE_NAME")

- Identificacion simbolica para recurso: UNICO en su contexto (carpeta). Notacion por puntos agregada

> Permite busquedas relativas basadas en una identificacion textual
> P. Ej: ResourceTree.get_relative("root.dir1.dir2.dir3.file1")

- Nombre simbolico para recurso (opcional)

> Util para almacenamiento, visualizacion, o documentacion

- Descripcion para recurso (opcional)

> Util para almacenamiento, visualizacion, o documentacion

- Integracion de arboles de recursos (ResourceTree)

> Util para componer estructuras de recursos, y fusionarlas en un punto de convergencia