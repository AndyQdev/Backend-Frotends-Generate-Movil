import os, shutil, pathlib, tempfile, subprocess, json
from jinja2 import Environment, FileSystemLoader


BASE_DIR = pathlib.Path(__file__).parent           # …/app/routes/utils
TEMPLATE_DIR = BASE_DIR / "templates"
TEMPLATE_ZIP = BASE_DIR.parent.parent / "templates" / "flutter_template.zip"
#                       ↑ sube 2 niveles hasta app/ luego templates/

env = Environment(loader=FileSystemLoader(TEMPLATE_DIR), autoescape=False)
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
    print("Pages:", page)
    print("Componentes:", parts)
    class_defs = "\n\n".join(p["class_def"] for p in parts if p["class_def"])
    calls      = ",\n          ".join(p["call"]      for p in parts if p["call"])

    bottom_call = next((p["bottom"] for p in parts if "bottom" in p), None)

    tpl = env.get_template("page.dart.j2")
    return tpl.render(
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
        return {'class_def': class_def, 'call': f'{class_name}()'}

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
    
    if t == 'checklist':
        call = env.get_template('checklist.dart.j2').render(comp=comp)
        return {'class_def': '', 'call': call}

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

    if t == 'search':
        class_name = f"Search{comp['id']}"
        class_def = env.get_template('search.dart.j2').render(comp=comp, class_name=class_name)
        return {'class_def': class_def, 'call': f'{class_name}()'}
    
    return {'class_def': '', 'call': ''}

# ---------- genera todos los files ----------
def build_flutter_project(proj: dict) -> str:
    app_dir = scaffold_flutter_from_zip(f"project_{proj['id']}")

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
