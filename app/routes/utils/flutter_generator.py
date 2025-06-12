import os, shutil, pathlib, tempfile, subprocess, json, zipfile
from jinja2 import Environment, FileSystemLoader


BASE_DIR = pathlib.Path(__file__).parent           # …/app/routes/utils
TEMPLATE_DIR = BASE_DIR / "templates"
TEMPLATE_ZIP = BASE_DIR.parent.parent / "templates" / "flutter_template.zip"
#                       ↑ sube 2 niveles hasta app/ luego templates/

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False, extensions=['jinja2.ext.do'],)
print("Plantillas Jinja en :", TEMPLATE_DIR.resolve())
print("Flutter template zip:", TEMPLATE_ZIP.resolve())
def scaffold_flutter_from_zip(project_name: str) -> str:
    """Descomprime flutter_template.zip en un tmp y renombra el dir."""
    tmpdir   = tempfile.mkdtemp()
    unzip_at = os.path.join(tmpdir, project_name)
    shutil.unpack_archive(TEMPLATE_ZIP, unzip_at)
    return unzip_at                                    # ruta al proyecto

def camel(name: str) -> str:
    return "".join(w.capitalize() for w in name.split("_"))

# ---------- renderizado de una página ----------
def render_page(page: dict) -> str:
    parts = [render_component(c) for c in page["components"]]
    parts.sort(key=lambda p: p.get('z', 0))
    print("Pages:", page)
    print("Componentes:", parts)
    class_defs = "\n\n".join(p["class_def"] for p in parts if p["class_def"])
    calls      = ",\n          ".join(p["call"]      for p in parts if p["call"])

    bottom_call = next((p["bottom"] for p in parts if "bottom" in p), None)

    tpl = env.get_template("page.dart.j2")
    return f"// {page['name']}\n" + tpl.render(
        class_name = f"Page{page['id']}",
        bg_color   = page["background_color"][1:],   # sin #
        class_defs = class_defs,
        calls      = calls,
        bottom_call = bottom_call,
    )

def render_component(comp: dict) -> dict:
    """Devuelve {'class_def': str, 'call': str}"""
    t = comp['type']

    if t == 'button':
        call = env.get_template('button.dart.j2').render(comp=comp)
        return {'class_def': '', 'call': call}

    if t == 'input':
        class_name = f"Input{comp['id']}"
        class_def  = env.get_template('input.dart.j2').render(
            comp=comp, class_name=class_name
        )
        return {'class_def': class_def, 'call': f'{class_name}()'}

    if t == 'header':
        class_name = f"Header{comp['id']}"
        class_def  = env.get_template('header.dart.j2').render(
            comp=comp, class_name=class_name
        )
        return {'class_def': class_def, 'call': f'{class_name}()', 'z': 100}

    if t == 'bottomNavigationBar':
        class_name = f"BottomNav{comp['id']}"
        class_def  = env.get_template('bottom_navigation_bar.dart.j2').render(
            comp=comp, class_name=class_name
        )
        return {'class_def': class_def,
            'call'     : '',               # no va en el body/Stack
            'bottom'   : f'{class_name}()' # se usará en bottomNavigationBar
    }
    if t == 'select':
        class_name = f"Select{comp['id']}"
        class_def  = env.get_template('select.dart.j2').render(
            comp=comp, class_name=class_name
        )
        return {'class_def': class_def, 'call': f'{class_name}()'}
    
    # if t == 'checklist':
    #     call = env.get_template('checklist.dart.j2').render(comp=comp)
    #     return {'class_def': '', 'call': call}
    if t == 'checklist':
        class_name = f"Checklist{comp['id']}"
        class_def  = env.get_template('checklist.dart.j2').render(
            comp=comp, class_name=class_name
        )
        return {'class_def': class_def, 'call': f'{class_name}()'}

    
    if t == 'radiobutton':
        call = env.get_template('radiobutton.dart.j2').render(comp=comp)
        return {'class_def': '', 'call': call}

    if t == 'card':
        call = env.get_template('card.dart.j2').render(comp=comp)
        return {'class_def': '', 'call': call}

    if t == 'label':
        call = env.get_template('label.dart.j2').render(comp=comp)
        return {'class_def': '', 'call': call}
    if t == 'textArea':
        class_name = f"TextArea{comp['id']}"
        class_def = env.get_template('text_area.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}

    if t == 'imagen':
        class_name = f"Imagen{comp['id']}"
        class_def = env.get_template('imagen.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}

    if t == 'calendar':
        class_name = f"Calendar{comp['id']}"
        class_def = env.get_template('calendar.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}
    if t == 'icon':
        class_name = f"Icon{comp['id']}"
        class_def = env.get_template('icon.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}

    if t == 'datatable':
        class_name = f"DataTable{comp['id']}"
        class_def = env.get_template('datatable.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}
    
    if t == 'search':
        class_name = f"Search{comp['id']}"
        class_def = env.get_template('search.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}
    
    return {'class_def': '', 'call': ''}

# ---------- genera todos los files ----------
def build_flutter_project(proj: dict) -> str:
    app_dir = scaffold_flutter_from_zip(f"project_{proj['id']}")
    pubspec_path = os.path.join(app_dir, "flutter_template", "pubspec.yaml")
    with open(pubspec_path, "r", encoding="utf8") as f:
        lines = f.readlines()

    # Buscar el índice donde empiezan las dependencias
    for i, line in enumerate(lines):
        if line.strip() == "dependencies:":
            deps_index = i
            break
    else:
        raise ValueError("No se encontró el bloque de dependencias en pubspec.yaml")

    # Revisar si ya está agregada
    if not any("lucide_icons:" in l for l in lines):
        # Buscar el índice donde termina el bloque flutter: sdk: flutter
        for j in range(deps_index + 1, len(lines)):
            if lines[j].strip().startswith("sdk: flutter"):
                # Insertar después de esa línea
                lines.insert(j + 1, "  lucide_icons: ^0.257.0\n")
                break

    # Guardar el archivo modificado
    with open(pubspec_path, "w", encoding="utf8") as f:
        f.writelines(lines)
        
    pages_dir = os.path.join(app_dir, "flutter_template", "lib", "pages")
    os.makedirs(pages_dir, exist_ok=True)

    routes   = []
    for page in proj["pages"]:
        page_file = os.path.join(pages_dir, f"page_{page['id']}.dart")
        with open(page_file, "w", encoding="utf8") as f:
            f.write(render_page(page))
        routes.append(
            f"'/page-{page['id']}': (context) => const Page{page['id']}(),"
        )
    imports = [f"import 'pages/page_{page['id']}.dart';" for page in proj["pages"]]
    # Renderizar main.dart con las rutas
    main_tpl = env.get_template("main.dart.j2")
    with open(os.path.join(app_dir, "flutter_template", "lib", "main.dart"), "w", encoding="utf8") as f:
        f.write(main_tpl.render(
            imports=imports,
            routes=routes
        ))

    # Instalar deps locales (rápido, sin gradle) ---------------
    # subprocess.run(["flutter", "pub", "get"], cwd=app_dir, check=True)

    # Empaquetar
    zip_path = shutil.make_archive(app_dir, "zip", app_dir)
    return zip_path



# desde aqui
def build_specific_files(proj: dict, file_types: list) -> str:
    """
    Genera un archivo zip con los archivos específicos solicitados.
    
    Args:
        proj: Diccionario con la información del proyecto
        file_types: Lista de tipos de archivos a generar. Puede contener:
            - 'main': Para generar el main.dart
            - 'page_X': Para generar la página X (ej: 'page_1', 'page_2', etc)
    
    Returns:
        str: Ruta al archivo zip generado
    """
    app_dir = scaffold_flutter_from_zip(f"project_{proj['id']}_specific")
    pages_dir = os.path.join(app_dir, "flutter_template", "lib", "pages")
    os.makedirs(pages_dir, exist_ok=True)

    # Preparar rutas e imports solo para las páginas solicitadas
    routes = []
    imports = []
    pages_to_generate = []

    for file_type in file_types:
        if file_type == 'main':
            continue
        elif file_type.startswith('page_'):
            page_id = int(file_type.split('_')[1])
            pages_to_generate.append(page_id)
            routes.append(f"'/page-{page_id}': (context) => const Page{page_id}(),")
            imports.append(f"import 'pages/page_{page_id}.dart';")

    # Generar solo las páginas solicitadas
    for page in proj["pages"]:
        if page['id'] in pages_to_generate:
            page_file = os.path.join(pages_dir, f"page_{page['id']}.dart")
            with open(page_file, "w", encoding="utf8") as f:
                f.write(render_page(page))

    # Generar main.dart si fue solicitado
    if 'main' in file_types:
        main_tpl = env.get_template("main.dart.j2")
        main_content = f"// main.dart - {proj['name']}\n" + main_tpl.render(
            imports=imports,
            routes=routes
        )
        with open(os.path.join(app_dir, "flutter_template", "lib", "main.dart"), "w", encoding="utf8") as f:
            f.write(main_content)

    # Empaquetar
    output_zip = os.path.join(tempfile.gettempdir(), f"specific_flutter_{proj['id']}.zip")
    with zipfile.ZipFile(output_zip, "w", zipfile.ZIP_DEFLATED) as zipf:
        if 'main' in file_types:
            main_path = os.path.join(app_dir, "flutter_template", "lib", "main.dart")
            zipf.write(main_path, arcname="main.dart")

        for file_type in file_types:
            if file_type.startswith("page_"):
                page_id = int(file_type.split("_")[1])
                page_path = os.path.join(app_dir, "flutter_template", "lib", "pages", f"page_{page_id}.dart")
                if os.path.exists(page_path):
                    zipf.write(page_path, arcname=f"page_{page_id}.dart")
    return output_zip
